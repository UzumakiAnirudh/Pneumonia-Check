"""ModelProvider interface — the boundary between the API and the networks.

Implementations:
* :class:`app.models.real_provider.TorchModelProvider` — trained weights from ``backend/weights``.
* :class:`app.models.mock_provider.MockModelProvider` — simulated outputs so the app runs end to end.

The predictor service handles calibration, the two-stage hierarchy and explanation
post-processing identically for both.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

from app.models.specs import ARCHS


class ModelUnavailableError(RuntimeError):
    """Requested model/task has no weights loaded."""


@dataclass
class InferenceOutput:
    """Raw output of one network on one image."""

    logits: np.ndarray
    """Uncalibrated logits, shape (num_classes,)."""
    input_image: np.ndarray
    """The preprocessed uint8 (size, size) image the network saw (for lung masking)."""
    cam: np.ndarray | None = None
    """Grad-CAM heatmap at input resolution in [0, 1], for the predicted class."""
    target_layer: str = ""
    elapsed_ms: float = 0.0


@dataclass
class ModelInfo:
    key: str
    name: str
    ready: bool
    weights: dict[str, bool] = field(default_factory=dict)


class ModelProvider(ABC):
    """Runs networks on grayscale images."""

    is_mock: bool = False

    @abstractmethod
    def available(self, arch: str, task: str) -> bool:
        """True if ``arch``/``task`` can be run."""

    @abstractmethod
    def infer(self, arch: str, task: str, gray: np.ndarray, explain: bool = False) -> InferenceOutput:
        """Run ``arch`` for ``task`` on a full-resolution uint8 grayscale image."""

    @abstractmethod
    def status(self, tasks: list[str]) -> list[ModelInfo]:
        """Per-architecture readiness for the given tasks."""

    @property
    def device_name(self) -> str:
        return "cpu"

    @staticmethod
    def display_name(arch: str) -> str:
        return ARCHS[arch].display_name
