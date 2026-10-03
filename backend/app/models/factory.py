"""Builds the configured ModelProvider."""

from __future__ import annotations

import logging

import torch

from app.config import Settings
from app.models.mock_provider import MockModelProvider
from app.models.provider import ModelProvider
from app.models.real_provider import TorchModelProvider
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


def create_provider(settings: Settings, device: torch.device) -> ModelProvider:
    """``USE_MOCK_MODELS=true`` -> MockModelProvider, otherwise TorchModelProvider."""
    cfg = preprocess_from_settings(settings)
    if settings.use_mock_models:
        logger.info("Using MockModelProvider (USE_MOCK_MODELS=true)")
        return MockModelProvider(cfg, latency_ms=settings.mock_latency_ms)
    provider = TorchModelProvider(settings.weights_dir, tasks_for_mode(settings.classification_mode), device, cfg)
    if not provider.models:
        logger.warning(
            "USE_MOCK_MODELS=false but no weights were found in %s — predictions will return 503. "
            "See backend/weights/README.md.",
            settings.weights_dir,
        )
    return provider
