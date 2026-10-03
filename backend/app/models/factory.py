"""Builds the configured ModelProvider."""

from __future__ import annotations

import logging

from app.config import Settings
from app.models.mock_provider import MockModelProvider
from app.models.provider import ModelProvider
from app.models.specs import onnx_filename, weights_filename
from app.services.preprocessing import PreprocessConfig

logger = logging.getLogger(__name__)


def tasks_for_mode(mode: str) -> list[str]:
    return ["three_class"] if mode == "three_class" else ["stage1", "stage2"]


def preprocess_from_settings(settings: Settings) -> PreprocessConfig:
    return PreprocessConfig(
        image_size=settings.image_size,
        use_clahe=settings.use_clahe,
        clahe_clip_limit=settings.clahe_clip_limit,
        clahe_tile_grid=settings.clahe_tile_grid,
    )


def resolve_backend(settings: Settings) -> str:
    """'torch' or 'onnx'. With MODEL_BACKEND=auto, prefer PyTorch when it is installed and .pth
    weights exist, otherwise use exported .onnx models."""
    if settings.model_backend != "auto":
        return settings.model_backend
    tasks = tasks_for_mode(settings.classification_mode)
    has = lambda name: (settings.weights_dir / name).exists()  # noqa: E731
    try:
        import torch  # noqa: F401

        torch_ok = True
    except ImportError:
        torch_ok = False
    if torch_ok and any(has(weights_filename(a, t)) for a in ("densenet", "swin") for t in tasks):
        return "torch"
    return "onnx"


def create_provider(settings: Settings) -> ModelProvider:
    """``USE_MOCK_MODELS=true`` -> MockModelProvider; otherwise PyTorch or ONNX models (see resolve_backend)."""
    cfg = preprocess_from_settings(settings)
    tasks = tasks_for_mode(settings.classification_mode)
    if settings.use_mock_models:
        logger.info("Using MockModelProvider (USE_MOCK_MODELS=true)")
        return MockModelProvider(cfg, latency_ms=settings.mock_latency_ms)
    backend = resolve_backend(settings)
    if backend == "onnx":
        from app.models.onnx_provider import OnnxModelProvider

        provider: ModelProvider = OnnxModelProvider(settings.weights_dir, tasks, cfg)
    else:
        from app.models.real_provider import TorchModelProvider, resolve_device

        provider = TorchModelProvider(settings.weights_dir, tasks, resolve_device(settings.device), cfg)
    if not provider.models:  # type: ignore[attr-defined]
        logger.warning(
            "No %s models found in %s — predictions will return 503. See backend/weights/README.md.",
            backend,
            settings.weights_dir,
        )
    logger.info("Model backend: %s", backend)
    return provider
