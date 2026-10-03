"""Input validation: is this a usable frontal chest X-ray?

Two strategies:
* :class:`LearnedValidator` — a MobileNetV3-Small binary classifier (CXR vs non-CXR) trained by
  ``training/train_validator.py`` and loaded from ``weights/validator.pth``.
* :class:`HeuristicValidator` — fallback used until that model is trained: grayscale check,
  aspect ratio, intensity distribution and a coarse anatomical-layout check.

Resolution / quality checks always run regardless of which strategy decides "is it a CXR".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.services.lung_mask import template_mask
from app.services.preprocessing import LoadedImage, validator_tensor

logger = logging.getLogger(__name__)

REJECT_MESSAGE = "This doesn't look like a chest X-ray. Please upload a frontal chest X-ray image."


@dataclass
class ValidationOutcome:
    """Result of validating one image."""

    is_chest_xray: bool
    score: float
    method: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    quality_ok: bool = True

    @property
    def is_valid(self) -> bool:
        return self.is_chest_xray and self.quality_ok

    @property
    def message(self) -> str:
        if not self.is_chest_xray:
            return REJECT_MESSAGE
        if not self.quality_ok:
            return "The image quality is too low to analyse reliably. Please upload a higher-resolution X-ray."
        if self.warnings:
            return "Image accepted with quality warnings."
        return "Image looks like a frontal chest X-ray."


def quality_checks(img: LoadedImage, min_resolution: int, warn_resolution: int) -> tuple[bool, list[str], list[str]]:
    """Resolution, contrast and blur checks. Returns (ok, reasons, warnings)."""
    reasons: list[str] = []
    warnings: list[str] = []
    short = min(img.width, img.height)
    if short < min_resolution:
        reasons.append(f"Image is too small to analyse ({img.width}×{img.height}; minimum {min_resolution} px).")
    elif short < warn_resolution:
        warnings.append(f"Low resolution ({img.width}×{img.height}) — results may be less reliable.")

    small = cv2.resize(img.gray, (256, 256), interpolation=cv2.INTER_AREA)
    if float(small.std()) < 22:
        warnings.append("Very low contrast image.")
    sharpness = float(cv2.Laplacian(small, cv2.CV_64F).var())
    if sharpness < 8:
        warnings.append("Image appears blurry.")
    return not reasons, reasons, warnings


class HeuristicValidator:
    """Rule-based CXR detector. Each failed check multiplies the score by a penalty."""

    method = "heuristic"

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold

    def score(self, img: LoadedImage) -> tuple[float, list[str]]:
        reasons: list[str] = []
        score = 1.0

        rgb = cv2.resize(img.rgb, (128, 128), interpolation=cv2.INTER_AREA).astype(np.int16)
        colourfulness = float((rgb.max(axis=2) - rgb.min(axis=2)).mean())
        if colourfulness > 18:
            score *= 0.1
            reasons.append("The image is in colour; chest X-rays are grayscale.")
        elif colourfulness > 8:
            score *= 0.7

        aspect = img.width / img.height
        if not 0.55 <= aspect <= 1.8:
            score *= 0.35
            reasons.append(f"Unusual aspect ratio ({aspect:.2f}) for a frontal chest X-ray.")

        g = cv2.resize(img.gray, (224, 224), interpolation=cv2.INTER_AREA)
        white = float((g > 235).mean())
        black = float((g < 15).mean())
        if white > 0.55:
            score *= 0.2
            reasons.append("Mostly white image — looks like a document or screenshot.")
        if black > 0.75:
            score *= 0.3
            reasons.append("Mostly black image.")
        if float(g.std()) < 12:
            score *= 0.2
            reasons.append("Nearly uniform image with no anatomical structure.")

        # Anatomical layout: the mediastinum (spine/heart) is brighter than both lung fields,
        # and the two lung fields have broadly similar density.
        lungs = template_mask(224)
        left_mask, right_mask = lungs.copy(), lungs.copy()
        left_mask[:, 112:] = False
        right_mask[:, :112] = False
        lung_l, lung_r = float(g[left_mask].mean()), float(g[right_mask].mean())
        mediastinum = float(g[56:168, 100:124].mean())
        contrast = mediastinum - max(lung_l, lung_r)
        if contrast < -5:
            score *= 0.45
            reasons.append("No bright central mediastinum between darker lung fields.")
        elif contrast < 6:
            score *= 0.8
        if abs(lung_l - lung_r) > 70:
            score *= 0.6
            reasons.append("Left and right halves differ strongly in density.")

        # Chest anatomy is roughly mirror-symmetric at coarse scale; random scenes are not.
        coarse = cv2.resize(g, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
        symmetry = float(np.corrcoef(coarse.ravel(), coarse[:, ::-1].ravel())[0, 1]) if coarse.std() > 0 else 0.0
        if symmetry < 0.3:
            score *= 0.35
            reasons.append("No left-right symmetric chest anatomy detected.")
        elif symmetry < 0.55:
            score *= 0.8

        # Radiographs are smooth at fine scale; pure noise / halftone screenshots are not.
        gf = g.astype(np.float32)
        high_freq = float(np.abs(gf - cv2.GaussianBlur(gf, (0, 0), 1.5)).mean())
        if high_freq > 20:
            score *= 0.2
            reasons.append("Image is dominated by fine-grained noise or texture.")

        return float(np.clip(score, 0.0, 1.0)), reasons

    def validate(self, img: LoadedImage) -> tuple[bool, float, list[str]]:
        score, reasons = self.score(img)
        return score >= self.threshold, score, reasons


class LearnedValidator:
    """MobileNetV3-Small classifier: class 0 = chest X-ray, class 1 = other."""

    method = "model"

    def __init__(self, weights_path: Path, device: Any, threshold: float = 0.5) -> None:
        import timm
        import torch

        self.device = device
        self.threshold = threshold
        self.model = timm.create_model("mobilenetv3_small_100", pretrained=False, num_classes=2)
        state = torch.load(weights_path, map_location="cpu", weights_only=True)
        state = state.get("state_dict", state) if isinstance(state, dict) else state
        self.model.load_state_dict({k.removeprefix("module."): v for k, v in state.items()})
        self.model.eval().to(device)

    def validate(self, img: LoadedImage) -> tuple[bool, float, list[str]]:
        import torch

        with torch.no_grad():
            logits = self.model(validator_tensor(img.rgb).to(self.device))
        p_cxr = float(torch.softmax(logits, dim=1)[0, 0])
        reasons = [] if p_cxr >= self.threshold else ["The input validator classified this image as not a chest X-ray."]
        return p_cxr >= self.threshold, p_cxr, reasons


class ImageValidator:
    """Facade: learned validator if weights exist, heuristic otherwise; plus quality checks."""

    def __init__(
        self,
        weights_path: Path | None,
        device: Any = None,
        threshold: float = 0.5,
        min_resolution: int = 128,
        warn_resolution: int = 512,
    ) -> None:
        self.min_resolution = min_resolution
        self.warn_resolution = warn_resolution
        self.heuristic = HeuristicValidator(threshold)
        self.learned: LearnedValidator | None = None
        if weights_path is not None and weights_path.exists():
            try:
                self.learned = LearnedValidator(weights_path, device, threshold)
                logger.info("Loaded learned input validator from %s", weights_path)
            except Exception:  # pragma: no cover - corrupt weights
                logger.exception("Could not load validator weights; using heuristic fallback")

    @property
    def method(self) -> str:
        return "model" if self.learned else "heuristic"

    def validate(self, img: LoadedImage) -> ValidationOutcome:
        engine = self.learned or self.heuristic
        is_cxr, score, reasons = engine.validate(img)
        quality_ok, q_reasons, warnings = quality_checks(img, self.min_resolution, self.warn_resolution)
        return ValidationOutcome(
            is_chest_xray=is_cxr,
            score=round(score, 4),
            method=engine.method,
            reasons=reasons + q_reasons,
            warnings=warnings,
            quality_ok=quality_ok,
        )
