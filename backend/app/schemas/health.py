from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ModelStatus(BaseModel):
    key: str
    name: str
    ready: bool
    weights: dict[str, bool] = {}


class ValidatorStatus(BaseModel):
    method: Literal["heuristic", "model"]
    loaded: bool


class CalibrationStatus(BaseModel):
    loaded: bool
    temperatures: dict[str, float]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    use_mock_models: bool
    classification_mode: Literal["two_stage", "three_class"]
    device: str
    models: list[ModelStatus]
    validator: ValidatorStatus
    calibration: CalibrationStatus
    history_enabled: bool
