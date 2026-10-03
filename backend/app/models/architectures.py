"""Model definitions shared by the API and the training scripts.

Both architectures come from ``timm`` so they are created identically in training
(``pretrained=True``) and inference (``pretrained=False`` + saved weights).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

import torch
from torch import nn

from app.models.specs import (  # noqa: F401  (re-exported)
    ARCHS,
    TASK_CLASSES,
    Arch,
    ArchSpec,
    Task,
    metadata_filename,
    onnx_filename,
    read_metadata,
    weights_filename,
)


def build_model(arch: str, num_classes: int, pretrained: bool = False, **kwargs) -> nn.Module:
    """Create a timm model with a fresh ``num_classes`` head."""
    import timm

    spec = ARCHS[arch]
    return timm.create_model(spec.timm_name, pretrained=pretrained, num_classes=num_classes, **kwargs)


def get_module(model: nn.Module, dotted: str) -> nn.Module:
    module: nn.Module = model
    for part in dotted.split("."):
        module = getattr(module, part)
    return module


def swin_reshape_transform(tensor: torch.Tensor) -> torch.Tensor:
    """Convert Swin token outputs to an NCHW feature map for Grad-CAM.

    timm >= 0.9 emits NHWC tensors (B, H, W, C); older versions emit (B, L, C).
    """
    if tensor.ndim == 4:
        return tensor.permute(0, 3, 1, 2)
    b, length, c = tensor.shape
    side = int(round(length**0.5))
    return tensor.reshape(b, side, side, c).permute(0, 3, 1, 2)


def reshape_transform_for(arch: str) -> Callable[[torch.Tensor], torch.Tensor] | None:
    return swin_reshape_transform if arch == "swin" else None


def load_state_dict(path: Path) -> dict[str, torch.Tensor]:
    """Load a checkpoint saved as a raw state_dict or ``{"state_dict": ...}``; strips DDP prefixes."""
    obj = torch.load(path, map_location="cpu", weights_only=True)
    if isinstance(obj, dict) and "state_dict" in obj and isinstance(obj["state_dict"], dict):
        obj = obj["state_dict"]
    return {k.removeprefix("module."): v for k, v in obj.items()}
