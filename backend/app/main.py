"""PneumoScan AI — FastAPI application.

Run:  uvicorn app.main:app --reload --port 8000   (from the backend/ directory)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.deps import Services
from app.api.auth_routes import router as auth_router
from app.api.routes import router
from app.config import Settings, get_settings
from app.models.factory import create_provider
from app.models.real_provider import resolve_device
from app.services.calibration import TemperatureStore
from app.db import make_engine
from app.services.auth import AuthService
from app.services.history import HistoryRepository
from app.services.predictor import PredictionService
from app.services.validator import ImageValidator

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("pneumoscan")


def build_services(settings: Settings) -> Services:
    device = resolve_device(settings.device)
    provider = create_provider(settings, device)
    validator = ImageValidator(
        settings.weights_dir / "validator.pth",
        device,
        threshold=settings.validator_threshold,
        min_resolution=settings.min_resolution,
        warn_resolution=settings.warn_resolution,
    )
    temperatures = TemperatureStore(settings.weights_dir / "temperature.json")
    predictor = PredictionService(settings, provider, validator, temperatures)
    engine = make_engine(settings.database_url)
    auth = AuthService(engine, session_days=settings.session_days)
    history = HistoryRepository(engine) if settings.history_enabled else None
    logger.info(
        "Ready: provider=%s mode=%s device=%s validator=%s history=%s",
        type(provider).__name__,
        settings.classification_mode,
        provider.device_name,
        validator.method,
        bool(history),
    )
    return Services(settings, provider, validator, temperatures, predictor, auth, history)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.services = build_services(settings)
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Explainable pneumonia detection from chest X-rays. Decision support only — not a diagnosis.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,  # session cookie
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(router)

    settings.gallery_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/api/metrics/gallery",
        StaticFiles(directory=settings.gallery_dir),
        name="gallery",
    )
    if settings.samples_dir.exists():
        app.mount(
            "/api/samples/files",
            StaticFiles(directory=settings.samples_dir),
            name="samples",
        )
    return app


app = create_app()
