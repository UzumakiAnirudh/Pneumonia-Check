"""Shared helpers for the training scripts.

The backend package (``backend/app``) is put on ``sys.path`` so preprocessing, model
definitions, calibration and metric code are *identical* between training and inference.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import torch

TRAINING_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRAINING_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_SPLITS = TRAINING_DIR / "data" / "splits.csv"
DEFAULT_WEIGHTS = BACKEND_DIR / "weights"
DEFAULT_METRICS = BACKEND_DIR / "metrics" / "metrics.json"
DEFAULT_GALLERY = BACKEND_DIR / "metrics" / "gallery"
OUTPUTS = TRAINING_DIR / "outputs"


def to_device(t: torch.Tensor, device: torch.device) -> torch.Tensor:
    """Host->device copy. Asynchronous only on CUDA: on Apple MPS a non_blocking copy from
    non-pinned memory can complete after the DataLoader reuses the buffer, silently pairing
    images with the wrong labels (observed as training collapse)."""
    return t.to(device, non_blocking=device.type == "cuda")


def seed_everything(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def get_device(name: str = "auto") -> torch.device:
    from app.models.real_provider import resolve_device

    return resolve_device(name)


def load_trained_model(arch: str, task: str, weights_dir: Path, device: torch.device):
    """Build a model and load ``<arch>_<task>.pth``; returns (model, PreprocessConfig)."""
    from app.models.architectures import (
        TASK_CLASSES,
        build_model,
        load_state_dict,
        read_metadata,
        weights_filename,
    )
    from app.services.preprocessing import PreprocessConfig

    model = build_model(arch, len(TASK_CLASSES[task]), pretrained=False)
    model.load_state_dict(load_state_dict(weights_dir / weights_filename(arch, task)))
    meta = read_metadata(weights_dir, arch, task)
    return model.eval().to(device), PreprocessConfig.from_dict(meta.get("preprocess"))


@torch.no_grad()
def collect_logits(model: torch.nn.Module, loader, device: torch.device) -> tuple[np.ndarray, np.ndarray]:
    """Run a model over a loader; returns (logits (N, C), labels (N,))."""
    model.eval()
    all_logits, all_labels = [], []
    for x, y in loader:
        with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
            out = model(to_device(x, device))
        all_logits.append(out.float().cpu().numpy())
        all_labels.append(y.numpy())
    return np.concatenate(all_logits), np.concatenate(all_labels)


def read_temperatures(weights_dir: Path) -> dict[str, float]:
    path = weights_dir / "temperature.json"
    return json.loads(path.read_text()) if path.exists() else {}
