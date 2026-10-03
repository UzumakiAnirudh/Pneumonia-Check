"""Grad-CAM computation and post-processing.

* :func:`compute_gradcam` runs pytorch-grad-cam on a real model (CNN or Swin).
* :func:`colorize`, :func:`blend` render heatmaps.
* :func:`describe_attention` turns a heatmap into a plain-language region description and the
  share of attention inside the lung fields.

Side naming follows the radiological convention: the patient's right lung appears on the
*left* of a frontal image.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    import torch

import cv2
import numpy as np

from app.services.lung_mask import estimate_lung_mask

VERTICAL_ZONES = ("upper", "middle", "lower")


@dataclass
class AttentionSummary:
    vertical: str
    side: str  # "left" | "right" | "bilateral" (patient side)
    label: str
    description: str
    lung_attention_pct: float
    lung_area_pct: float
    """Share of the image covered by the lung mask = in-lung attention expected by chance."""
    region_scores: dict[str, float]

    @property
    def attention_outside_lungs(self) -> bool:
        """True when attention is no more concentrated on the lungs than uniform attention would be."""
        return self.lung_attention_pct < self.lung_area_pct


def normalize_cam(cam: np.ndarray) -> np.ndarray:
    cam = np.nan_to_num(np.asarray(cam, dtype=np.float32))
    cam = np.maximum(cam, 0)
    lo, hi = float(cam.min()), float(cam.max())
    if hi - lo < 1e-8:
        return np.zeros_like(cam)
    return (cam - lo) / (hi - lo)


def compute_gradcam(
    model: torch.nn.Module,
    target_layer: torch.nn.Module,
    x: torch.Tensor,
    reshape_transform: Callable[[torch.Tensor], torch.Tensor] | None = None,
    target_index: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Run Grad-CAM. Returns (logits (C,), cam (H, W) in [0, 1] at input resolution).

    With ``target_index=None`` the predicted (arg-max) class is explained. Temperature scaling
    does not change the arg-max, so this matches the calibrated prediction.
    """
    from pytorch_grad_cam import GradCAM
    from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

    targets = None if target_index is None else [ClassifierOutputTarget(target_index)]
    with GradCAM(model=model, target_layers=[target_layer], reshape_transform=reshape_transform) as cam:
        grayscale = cam(input_tensor=x, targets=targets)
        logits = cam.outputs.detach().cpu().numpy()[0]
    return logits, normalize_cam(grayscale[0])


def colorize(cam: np.ndarray) -> np.ndarray:
    """[0, 1] heatmap -> RGB uint8 using the JET colormap (legend in the UI matches)."""
    heat = cv2.applyColorMap(np.uint8(np.clip(cam, 0, 1) * 255), cv2.COLORMAP_JET)
    return cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)


def blend(gray: np.ndarray, heat_rgb: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    """Alpha-blend a colour heatmap on a grayscale image (same size)."""
    base = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB) if gray.ndim == 2 else gray
    return cv2.addWeighted(base, 1 - alpha, heat_rgb, alpha, 0)


def _region_label(vertical: str, side: str) -> str:
    if side == "bilateral":
        return f"{vertical} zones of both lungs"
    return f"{vertical} {side} lung"


def describe_attention(cam: np.ndarray, image: np.ndarray, lung_mask: np.ndarray | None = None) -> AttentionSummary:
    """Summarise a square heatmap aligned with a square grayscale image (e.g. 224x224).

    Zones are the upper/middle/lower thirds of the lung fields' vertical extent, split by image
    half. Region scores are the share of total in-lung attention per zone.
    """
    size = cam.shape[0]
    mask = estimate_lung_mask(image) if lung_mask is None else lung_mask
    cam = normalize_cam(cam)
    total = float(cam.sum()) + 1e-8
    lung_pct = 100.0 * float((cam * mask).sum()) / total
    area_pct = 100.0 * float(mask.mean())

    rows = np.nonzero(mask.any(axis=1))[0]
    top, bottom = (int(rows.min()), int(rows.max()) + 1) if rows.size else (0, size)
    bounds = np.linspace(top, bottom, 4).round().astype(int)
    half = size // 2

    # Weight by the lung mask (dilated) so zone scores describe lung regions.
    weight = cv2.dilate(mask.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
    weighted = cam * np.maximum(weight, 0.15)
    scores: dict[str, float] = {}
    for zi, zone in enumerate(VERTICAL_ZONES):
        band = weighted[bounds[zi] : bounds[zi + 1]]
        scores[f"right_{zone}"] = float(band[:, :half].sum())  # image-left = patient's right
        scores[f"left_{zone}"] = float(band[:, half:].sum())
    s_total = sum(scores.values()) + 1e-8
    scores = {k: round(v / s_total, 4) for k, v in scores.items()}

    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    side, vertical = best.split("_")
    other = scores[f"{'left' if side == 'right' else 'right'}_{vertical}"]
    if other >= 0.75 * scores[best]:
        side = "bilateral"

    label = _region_label(vertical, side)
    if float(cam.max()) <= 0:
        description = "The model showed no localised attention for this prediction."
    elif side == "bilateral":
        description = f"The model's attention was distributed across the {label}."
    else:
        description = f"The model's attention was concentrated in the {label} region."
    if lung_pct < area_pct:
        description += " Attention is not concentrated on the lung fields (no more than chance)."

    return AttentionSummary(
        vertical=vertical,
        side=side,
        label=label,
        description=description,
        lung_attention_pct=round(lung_pct, 1),
        lung_area_pct=round(area_pct, 1),
        region_scores=scores,
    )
