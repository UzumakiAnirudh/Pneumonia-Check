from __future__ import annotations

from typing import Literal, Optional

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


class ModelVersion(BaseModel):
    id: str
    label: str


class TrainingStatus(BaseModel):
    state: str
    label: str = ""
    percent: float = 0
    epoch: Optional[int] = None
    epochs: Optional[int] = None
    active_version: Optional[str] = None
    new_version: Optional[str] = None
    description: str = ""
    message: str = ""
    started_at: Optional[str] = None
    updated_at: Optional[str] = None


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
    model_version: Optional[ModelVersion] = None
    training: Optional[TrainingStatus] = None
