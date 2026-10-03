"""Application settings, loaded from environment variables / ``backend/.env``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """All runtime configuration. Every field can be overridden by an env var of the same name."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_name: str = "PneumoScan AI"
    version: str = "1.0.0"

    # --- Models -----------------------------------------------------------
    use_mock_models: bool = False
    """Development/testing only: MockModelProvider generates simulated outputs without weights."""
    classification_mode: Literal["two_stage", "three_class"] = "two_stage"
    weights_dir: Path = BACKEND_DIR / "weights"
    device: str = "auto"
    """'auto', 'cpu', 'cuda' or 'mps'."""
    mock_latency_ms: int = 150
    """Artificial per-model delay for the mock provider, so the demo feels realistic."""

    # --- Preprocessing defaults (overridden per model by weights/<model>.json) ----
    image_size: int = 224
    use_clahe: bool = True
    clahe_clip_limit: float = 2.0
    clahe_tile_grid: int = 8
    display_max_side: int = 512

    # --- Validation -------------------------------------------------------
    min_resolution: int = 128
    warn_resolution: int = 512
    validator_threshold: float = 0.5
    max_upload_mb: int = 25

    # --- Results ----------------------------------------------------------
    default_threshold: float = 0.75
    """Calibrated confidence below which a result is flagged for expert review."""

    # --- Storage ----------------------------------------------------------
    history_enabled: bool = True
    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'history.db'}"
    metrics_path: Path = BACKEND_DIR / "metrics" / "metrics.json"
    gallery_dir: Path = BACKEND_DIR / "metrics" / "gallery"
    samples_dir: Path = BACKEND_DIR / "samples"

    # --- Accounts ---------------------------------------------------------
    session_days: int = 7
    session_cookie_name: str = "pneumoscan_session"
    cookie_secure: bool = False
    """Set true when served over HTTPS so the session cookie is never sent in clear text."""

    # --- HTTP -------------------------------------------------------------
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://localhost:8080",
    ]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
