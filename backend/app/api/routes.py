"""HTTP API."""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.deps import Services, current_user, get_services
from app.api.errors import api_error, read_upload
from app.models.factory import tasks_for_mode
from app.models.provider import ModelUnavailableError
from app.schemas import (
    HealthResponse,
    HistoryItem,
    ModelStatus,
    PredictResponse,
    SampleImage,
    ValidationResult,
)
from app.schemas.health import CalibrationStatus, ValidatorStatus
from app.services.predictor import NotChestXrayError
from app.services.preprocessing import ImageDecodeError
from app.services.resources import load_metrics, load_samples

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(s: Services = Depends(get_services)) -> HealthResponse:
    """Backend, model, validator and calibration status."""
    tasks = tasks_for_mode(s.settings.classification_mode)
    models = [ModelStatus(**vars(m)) for m in s.provider.status(tasks)]
    return HealthResponse(
        status="ok" if any(m.ready for m in models) else "degraded",
        version=s.settings.version,
        use_mock_models=s.provider.is_mock,
        classification_mode=s.settings.classification_mode,
        device=s.provider.device_name,
        models=models,
        validator=ValidatorStatus(method=s.validator.method, loaded=s.validator.learned is not None),  # type: ignore[arg-type]
        calibration=CalibrationStatus(loaded=s.temperatures.loaded, temperatures=s.temperatures.values),
        history_enabled=s.history is not None,
    )


@router.post("/validate", response_model=ValidationResult, tags=["analysis"])
async def validate(
    file: UploadFile = File(...),
    s: Services = Depends(get_services),
    _user: User = Depends(current_user),
) -> ValidationResult:
    """Check whether an image is a usable frontal chest X-ray."""
    data = await read_upload(file, s.settings.max_upload_bytes)
    try:
        return await run_in_threadpool(s.predictor.validate, data, file.filename)
    except ImageDecodeError as exc:
        raise api_error(400, "invalid_image", str(exc)) from exc


@router.post("/predict", response_model=PredictResponse, tags=["analysis"])
async def predict(
    file: UploadFile = File(...),
    model: Literal["densenet", "swin", "both"] = Form("densenet"),
    threshold: Optional[float] = Form(None, ge=0.5, le=0.99),
    save_history: bool = Form(False),
    source_name: Optional[str] = Form(None, max_length=200),
    s: Services = Depends(get_services),
    user: User = Depends(current_user),
) -> PredictResponse:
    """Run Stage 1 (and Stage 2 when pneumonia is found) with calibrated confidences and Grad-CAM."""
    data = await read_upload(file, s.settings.max_upload_bytes)
    try:
        result = await run_in_threadpool(s.predictor.predict, data, file.filename, model, threshold, source_name)
    except ImageDecodeError as exc:
        raise api_error(400, "invalid_image", str(exc)) from exc
    except NotChestXrayError as exc:
        raise api_error(
            422,
            "not_chest_xray",
            exc.validation.message,
            validation=exc.validation.model_dump(),
        ) from exc
    except ModelUnavailableError as exc:
        raise api_error(503, "model_unavailable", str(exc)) from exc

    if save_history and s.history is not None:
        await run_in_threadpool(s.history.add, result, user.id)
        result.saved_to_history = True
    return result


@router.get("/metrics", tags=["metrics"])
def metrics(s: Services = Depends(get_services)) -> dict:
    """Evaluation metrics exported by the training pipeline (see training/evaluate.py)."""
    data = load_metrics(s.settings.metrics_path)
    if data is None:
        raise api_error(
            404,
            "metrics_missing",
            "No metrics file found. Run training/evaluate.py to generate it.",
        )
    return data


@router.get("/samples", response_model=list[SampleImage], tags=["samples"])
def samples(s: Services = Depends(get_services)) -> list[SampleImage]:
    """Bundled sample X-rays for demos."""
    return load_samples(s.settings.samples_dir)


def _history(s: Services):
    if s.history is None:
        raise api_error(
            404,
            "history_disabled",
            "History is disabled on this server (HISTORY_ENABLED=false).",
        )
    return s.history


@router.get("/history", response_model=list[HistoryItem], tags=["history"])
def list_history(s: Services = Depends(get_services), user: User = Depends(current_user)) -> list[HistoryItem]:
    """The current account's analyses, newest first."""
    if s.history is None:
        return []
    return s.history.list(user.id)


@router.get("/history/{item_id}", response_model=PredictResponse, tags=["history"])
def get_history_item(
    item_id: str, s: Services = Depends(get_services), user: User = Depends(current_user)
) -> PredictResponse:
    item = _history(s).get(item_id, user.id)
    if item is None:
        raise api_error(404, "not_found", "Analysis not found in history.")
    return item


@router.delete("/history/{item_id}", status_code=204, tags=["history"])
def delete_history_item(
    item_id: str, s: Services = Depends(get_services), user: User = Depends(current_user)
) -> Response:
    if not _history(s).delete(item_id, user.id):
        raise api_error(404, "not_found", "Analysis not found in history.")
    return Response(status_code=204)


@router.delete("/history", status_code=204, tags=["history"])
def clear_history(s: Services = Depends(get_services), user: User = Depends(current_user)) -> Response:
    """Delete all of the current account's analyses."""
    if s.history is not None:
        s.history.clear(user.id)
    return Response(status_code=204)
