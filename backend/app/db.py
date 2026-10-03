"""Database engine shared by accounts and history (SQLite via SQLModel)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, inspect, text
from sqlmodel import SQLModel, create_engine


def make_engine(database_url: str) -> Engine:
    """Create the engine, create tables, and apply small additive migrations."""
    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url.removeprefix("postgres://")  # Heroku/Neon style URLs
    if database_url.startswith("sqlite:///"):
        Path(database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(database_url, pool_pre_ping=True)  # e.g. a free hosted Postgres
    # Import table models so they are registered on SQLModel.metadata.
    from app.services import auth, history  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _migrate(engine)
    return engine


def _migrate(engine: Engine) -> None:
    """Additive migrations for databases created by earlier versions."""
    columns = {c["name"] for c in inspect(engine).get_columns("analyses")}
    if "user_id" not in columns:
        # Pre-account history rows keep user_id NULL and are therefore visible to nobody.
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE analyses ADD COLUMN user_id VARCHAR"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_analyses_user_id ON analyses (user_id)"))
