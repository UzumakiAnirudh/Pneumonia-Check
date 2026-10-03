"""Model names, classes and file names — no PyTorch import, so ONNX deployments stay light."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Arch = Literal["densenet", "swin"]
Task = Literal["stage1", "stage2", "three_class"]

TASK_CLASSES: dict[str, list[str]] = {
    "stage1": ["NORMAL", "PNEUMONIA"],
    "stage2": ["BACTERIAL", "VIRAL"],
    "three_class": ["NORMAL", "BACTERIAL", "VIRAL"],
}


@dataclass(frozen=True)
class ArchSpec:
    key: str
    display_name: str
    timm_name: str
    target_layer: str
    """Dotted module path used as the Grad-CAM target."""


ARCHS: dict[str, ArchSpec] = {
    "densenet": ArchSpec(
        key="densenet",
        display_name="DenseNet121",
        timm_name="densenet121",
        target_layer="features.denseblock4",  # output of the last dense block (7x7x1024)
    ),
    "swin": ArchSpec(
        key="swin",
        display_name="Swin Transformer (Tiny)",
        timm_name="swin_tiny_patch4_window7_224",
        target_layer="norm",  # final-stage LayerNorm (7x7x768 tokens)
    ),
}


def weights_filename(arch: str, task: str) -> str:
    return f"{arch}_{task}.pth"


def metadata_filename(arch: str, task: str) -> str:
    return f"{arch}_{task}.json"


def onnx_filename(arch: str, task: str) -> str:
    return f"{arch}_{task}.onnx"


def read_metadata(weights_dir: Path, arch: str, task: str) -> dict:
    path = weights_dir / metadata_filename(arch, task)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except ValueError:
            return {}
    return {}
