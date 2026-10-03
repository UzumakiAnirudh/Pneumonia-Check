"""Shared service container and FastAPI dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Request

from app.config import Settings
from app.models.provider import ModelProvider
from app.services.calibration import TemperatureStore
from app.api.errors import api_error
from app.services.auth import AuthService, User
from app.services.history import HistoryRepository
from app.services.predictor import PredictionService
from app.services.validator import ImageValidator


@dataclass
class Services:
    settings: Settings
    provider: ModelProvider
    validator: ImageValidator
    temperatures: TemperatureStore
    predictor: PredictionService
    auth: AuthService
    history: Optional[HistoryRepository]
    """None when HISTORY_ENABLED=false (nothing is ever stored)."""


def get_services(request: Request) -> Services:
    return request.app.state.services


def session_token(request: Request, s: Services = Depends(get_services)) -> str | None:
    return request.cookies.get(s.settings.session_cookie_name)


def current_user(token: str | None = Depends(session_token), s: Services = Depends(get_services)) -> User:
    """Require a valid session; 401 otherwise."""
    user = s.auth.user_for_token(token)
    if user is None:
        raise api_error(401, "not_authenticated", "Please log in to continue.")
    return user
