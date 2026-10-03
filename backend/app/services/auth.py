"""Accounts and sessions.

* Passwords: PBKDF2-HMAC-SHA256 (stdlib), per-user random salt, 310k iterations.
* Sessions: random 256-bit token sent to the browser in an httpOnly cookie; only its SHA-256
  hash is stored, so a leaked database cannot be used to log in. Logout deletes the session.
* Login throttling: 5 failures per email within 15 minutes -> temporary lockout.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Engine
from sqlmodel import Field, Session, SQLModel, delete, select

PBKDF2_ITERATIONS = 310_000
MAX_FAILURES = 5
LOCKOUT_SECONDS = 15 * 60


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str
    password_hash: str
    created_at: datetime


class AuthSession(SQLModel, table=True):
    __tablename__ = "sessions"

    token_hash: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    created_at: datetime
    expires_at: datetime


class EmailTakenError(Exception):
    pass


class TooManyAttemptsError(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Too many failed login attempts")
        self.retry_after = retry_after


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    # SQLite returns naive datetimes.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    return f"pbkdf2_sha256${iterations}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_b64, hash_b64 = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), int(iterations))
        return hmac.compare_digest(digest, base64.b64decode(hash_b64))
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# A real hash to compare against when the email is unknown, so response time doesn't reveal
# whether an account exists.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


class LoginThrottle:
    """In-memory failed-attempt counter per email (resets on restart)."""

    def __init__(self) -> None:
        self._fails: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        with self._lock:
            recent = [t for t in self._fails.get(key, []) if time.time() - t < LOCKOUT_SECONDS]
            self._fails[key] = recent
            if len(recent) >= MAX_FAILURES:
                raise TooManyAttemptsError(int(LOCKOUT_SECONDS - (time.time() - recent[0])) + 1)

    def fail(self, key: str) -> None:
        with self._lock:
            self._fails.setdefault(key, []).append(time.time())

    def reset(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)


class AuthService:
    def __init__(self, engine: Engine, session_days: int = 7) -> None:
        self.engine = engine
        self.session_ttl = timedelta(days=session_days)
        self.throttle = LoginThrottle()

    def register(self, name: str, email: str, password: str) -> User:
        email = normalize_email(email)
        with Session(self.engine) as db:
            if db.exec(select(User).where(User.email == email)).first():
                raise EmailTakenError(email)
            user = User(
                id=uuid.uuid4().hex,
                email=email,
                name=name.strip(),
                password_hash=hash_password(password),
                created_at=_now(),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    def authenticate(self, email: str, password: str) -> Optional[User]:
        email = normalize_email(email)
        self.throttle.check(email)
        with Session(self.engine) as db:
            user = db.exec(select(User).where(User.email == email)).first()
        ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
        if not (user and ok):
            self.throttle.fail(email)
            return None
        self.throttle.reset(email)
        return user

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        now = _now()
        with Session(self.engine) as db:
            db.add(
                AuthSession(
                    token_hash=_token_hash(token), user_id=user_id, created_at=now, expires_at=now + self.session_ttl
                )
            )
            db.commit()
        return token

    def user_for_token(self, token: str | None) -> Optional[User]:
        if not token:
            return None
        with Session(self.engine) as db:
            sess = db.get(AuthSession, _token_hash(token))
            if sess is None:
                return None
            if _as_utc(sess.expires_at) < _now():
                db.delete(sess)
                db.commit()
                return None
            return db.get(User, sess.user_id)

    def end_session(self, token: str | None) -> None:
        if not token:
            return
        with Session(self.engine) as db:
            db.exec(delete(AuthSession).where(AuthSession.token_hash == _token_hash(token)))  # type: ignore[call-overload]
            db.commit()
