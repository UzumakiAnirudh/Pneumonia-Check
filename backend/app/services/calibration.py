"""Temperature scaling (Guo et al., 2017).

A single scalar T > 0 per model/task divides the logits before softmax. T is fitted on the
validation set by ``training/calibrate.py`` (using :func:`fit_temperature`) and stored in
``weights/temperature.json`` as ``{"densenet_stage1": 1.42, ...}``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import torch

import numpy as np

logger = logging.getLogger(__name__)


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    z = np.asarray(logits, dtype=np.float64) / max(temperature, 1e-6)
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


T_MIN, T_MAX = 0.05, 20.0


def fit_temperature(
    logits: torch.Tensor | np.ndarray,
    labels: torch.Tensor | np.ndarray,
    max_iter: int = 200,
) -> float:
    """Learn T by minimising validation NLL with L-BFGS (optimises log T so T stays positive).

    The result is clamped to [0.05, 20]: values outside that range mean the validation set is
    too small or perfectly separated, and would make probabilities degenerate.
    """
    import torch

    logits_t = torch.as_tensor(np.asarray(logits), dtype=torch.float64)
    labels_t = torch.as_tensor(np.asarray(labels), dtype=torch.long)
    log_t = torch.zeros(1, dtype=torch.float64, requires_grad=True)
    optimizer = torch.optim.LBFGS([log_t], lr=0.1, max_iter=max_iter, line_search_fn="strong_wolfe")
    nll = torch.nn.CrossEntropyLoss()

    def closure() -> torch.Tensor:
        optimizer.zero_grad()
        loss = nll(logits_t / log_t.exp(), labels_t)
        loss.backward()
        return loss

    optimizer.step(closure)
    t = float(log_t.exp().item())
    if not np.isfinite(t) or not T_MIN <= t <= T_MAX:
        logger.warning("Fitted temperature %.4g is outside [%s, %s]; clamping", t, T_MIN, T_MAX)
        t = float(np.clip(np.nan_to_num(t, nan=1.0, posinf=T_MAX), T_MIN, T_MAX))
    return t


def expected_calibration_error(probs: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> float:
    """ECE using the max-probability (confidence) of each prediction."""
    probs = np.asarray(probs)
    labels = np.asarray(labels)
    conf = probs.max(axis=1)
    pred = probs.argmax(axis=1)
    correct = (pred == labels).astype(np.float64)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        in_bin = (conf > lo) & (conf <= hi)
        if in_bin.any():
            ece += in_bin.mean() * abs(correct[in_bin].mean() - conf[in_bin].mean())
    return float(ece)


def reliability_curve(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> dict[str, list[float]]:
    """Per-bin mean confidence / accuracy / count — for reliability diagrams."""
    conf = np.asarray(probs).max(axis=1)
    correct = (np.asarray(probs).argmax(axis=1) == np.asarray(labels)).astype(np.float64)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    out: dict[str, list[float]] = {
        "bin_confidence": [],
        "bin_accuracy": [],
        "bin_count": [],
    }
    for lo, hi in zip(edges[:-1], edges[1:]):
        in_bin = (conf > lo) & (conf <= hi)
        if in_bin.any():
            out["bin_confidence"].append(round(float(conf[in_bin].mean()), 4))
            out["bin_accuracy"].append(round(float(correct[in_bin].mean()), 4))
            out["bin_count"].append(int(in_bin.sum()))
    return out


class TemperatureStore:
    """Loads ``temperature.json``; missing keys fall back to T = 1 (uncalibrated)."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.values: dict[str, float] = {}
        if path is not None and path.exists():
            try:
                raw = json.loads(path.read_text())
                self.values = {k: float(v) for k, v in raw.items() if isinstance(v, (int, float)) and v > 0}
                logger.info("Loaded %d temperature(s) from %s", len(self.values), path)
            except (OSError, ValueError):
                logger.exception("Invalid temperature file %s; using T = 1", path)

    @property
    def loaded(self) -> bool:
        return bool(self.values)

    def get(self, arch: str, task: str) -> float:
        return self.values.get(f"{arch}_{task}", 1.0)
