"""Registration, login, logout and the current-user endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from fastapi.concurrency import run_in_threadpool

from app.api.deps import Services, current_user, get_services, session_token
from app.api.errors import api_error
from app.schemas.auth import LoginRequest, RegisterRequest, UserOut
from app.services.auth import EmailTakenError, TooManyAttemptsError, User

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, s: Services, token: str) -> None:
    response.set_cookie(
        key=s.settings.session_cookie_name,
        value=token,
        max_age=s.settings.session_days * 24 * 3600,
        httponly=True,  # not readable from JavaScript
        samesite="lax",  # not sent on cross-site POSTs (CSRF protection)
        secure=s.settings.cookie_secure,
        path="/",
    )


def _out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, created_at=user.created_at)


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: RegisterRequest, response: Response, s: Services = Depends(get_services)) -> UserOut:
    """Create an account and log in."""
    try:
        user = await run_in_threadpool(s.auth.register, body.name, body.email, body.password)
    except EmailTakenError as exc:
        raise api_error(409, "email_taken", "An account with this email already exists.") from exc
    _set_session_cookie(response, s, await run_in_threadpool(s.auth.create_session, user.id))
    return _out(user)


@router.post("/login", response_model=UserOut)
async def login(body: LoginRequest, response: Response, s: Services = Depends(get_services)) -> UserOut:
    try:
        user = await run_in_threadpool(s.auth.authenticate, body.email, body.password)
    except TooManyAttemptsError as exc:
        raise api_error(
            429,
            "too_many_attempts",
            f"Too many failed attempts. Try again in {max(1, exc.retry_after // 60)} minute(s).",
        ) from exc
    if user is None:
        raise api_error(401, "invalid_credentials", "Incorrect email or password.")
    _set_session_cookie(response, s, await run_in_threadpool(s.auth.create_session, user.id))
    return _out(user)


@router.post("/logout", status_code=204)
def logout(token: str | None = Depends(session_token), s: Services = Depends(get_services)) -> Response:
    s.auth.end_session(token)
    response = Response(status_code=204)
    response.delete_cookie(s.settings.session_cookie_name, path="/")
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return _out(user)
