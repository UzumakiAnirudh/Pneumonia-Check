"""Prediction orchestration: validate -> per-model inference -> calibrate -> explain."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

import numpy as np

from app.config import Settings
from app.models.architectures import ARCHS, TASK_CLASSES
from app.models.provider import InferenceOutput, ModelProvider
from app.schemas.prediction import (
    Agreement,
    DominantRegion,
    Explanation,
    ImageInfo,
    ModelResult,
    PredictResponse,
    Reliability,
    StageResult,
    ValidationResult,
)
from app.services.calibration import TemperatureStore, softmax
from app.services.gradcam import blend, colorize, describe_attention
from app.services.preprocessing import (
    LoadedImage,
    encode_png_data_uri,
    load_image,
    make_display_image,
    resize_to,
)
from app.services.validator import ImageValidator


class NotChestXrayError(Exception):
    """The upload failed validation."""

    def __init__(self, validation: ValidationResult) -> None:
        super().__init__(validation.message)
        self.validation = validation


def reliability_for(confidences: list[float], threshold: float) -> Reliability:
    """High only if every stage that ran is at or above the threshold."""
    if min(confidences) >= threshold:
        return Reliability(level="high", threshold=threshold, message="High confidence")
    return Reliability(
        level="low",
        threshold=threshold,
        message="Low confidence — recommend expert review",
    )


def _stage(task: str, probs: np.ndarray, temperature: float) -> StageResult:
    classes = TASK_CLASSES[task]
    idx = int(np.argmax(probs))
    return StageResult(
        label=classes[idx],
        confidence=round(float(probs[idx]), 6),
        probabilities={c: round(float(p), 6) for c, p in zip(classes, probs)},
        temperature=round(temperature, 4),
    )


class PredictionService:
    def __init__(
        self,
        settings: Settings,
        provider: ModelProvider,
        validator: ImageValidator,
        temperatures: TemperatureStore,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.validator = validator
        self.temperatures = temperatures

    # ------------------------------------------------------------------ validation

    def _validation_result(self, img: LoadedImage) -> ValidationResult:
        outcome = self.validator.validate(img)
        return ValidationResult(
            is_valid=outcome.is_valid,
            is_chest_xray=outcome.is_chest_xray,
            score=outcome.score,
            method=outcome.method,  # type: ignore[arg-type]
            message=outcome.message,
            reasons=outcome.reasons,
            warnings=outcome.warnings,
            image=ImageInfo(
                width=img.width,
                height=img.height,
                format=img.format,
                file_size_bytes=img.file_size,
                is_dicom=img.is_dicom,
            ),
        )

    def validate(self, data: bytes, filename: str | None = None) -> ValidationResult:
        return self._validation_result(load_image(data, filename))

    # ------------------------------------------------------------------ prediction

    def _explanation(self, out: InferenceOutput, target_label: str, display: np.ndarray) -> Explanation | None:
        if out.cam is None:
            return None
        summary = describe_attention(out.cam, out.input_image)
        h, w = display.shape[:2]
        cam_display = np.clip(resize_to(out.cam.astype(np.float32), w, h), 0, 1)
        heat = colorize(cam_display)
        return Explanation(
            method=("Grad-CAM" if not self.provider.is_mock else "Simulated Grad-CAM (mock)"),
            target_label=target_label,  # type: ignore[arg-type]
            target_layer=out.target_layer,
            heatmap_png=encode_png_data_uri(heat),
            overlay_png=encode_png_data_uri(blend(display, heat, 0.45)),
            dominant_region=DominantRegion(vertical=summary.vertical, side=summary.side, label=summary.label),  # type: ignore[arg-type]
            description=summary.description,
            lung_attention_pct=summary.lung_attention_pct,
            lung_area_pct=summary.lung_area_pct,
            region_scores=summary.region_scores,
        )

    def _run_two_stage(self, arch: str, gray: np.ndarray, display: np.ndarray, threshold: float) -> ModelResult:
        out1 = self.provider.infer(arch, "stage1", gray, explain=True)
        t1 = self.temperatures.get(arch, "stage1")
        p1 = softmax(out1.logits, t1)
        stage1 = _stage("stage1", p1, t1)
        elapsed = out1.elapsed_ms

        stage2 = None
        if stage1.label == "PNEUMONIA":
            out2 = self.provider.infer(arch, "stage2", gray, explain=False)
            t2 = self.temperatures.get(arch, "stage2")
            p2 = softmax(out2.logits, t2)
            stage2 = _stage("stage2", p2, t2)
            elapsed += out2.elapsed_ms
            class_probs = {
                "NORMAL": float(p1[0]),
                "BACTERIAL": float(p1[1] * p2[0]),
                "VIRAL": float(p1[1] * p2[1]),
            }
            final = stage2.label
        else:
            class_probs = {"NORMAL": float(p1[0]), "PNEUMONIA": float(p1[1])}
            final = "NORMAL"

        confidences = [stage1.confidence] + ([stage2.confidence] if stage2 else [])
        return ModelResult(
            model=arch,  # type: ignore[arg-type]
            model_name=ARCHS[arch].display_name,
            mode="two_stage",
            stage1=stage1,
            stage2=stage2,
            final_label=final,  # type: ignore[arg-type]
            final_confidence=round(class_probs[final], 6),
            class_probabilities={k: round(v, 6) for k, v in class_probs.items()},
            reliability=reliability_for(confidences, threshold),
            explanation=self._explanation(out1, stage1.label, display),
            inference_ms=round(elapsed, 1),
        )

    def _run_three_class(self, arch: str, gray: np.ndarray, display: np.ndarray, threshold: float) -> ModelResult:
        out = self.provider.infer(arch, "three_class", gray, explain=True)
        t = self.temperatures.get(arch, "three_class")
        p = softmax(out.logits, t)  # NORMAL, BACTERIAL, VIRAL
        p1 = np.array([p[0], p[1] + p[2]])
        stage1 = _stage("stage1", p1, t)
        stage2 = None
        final = "NORMAL"
        if stage1.label == "PNEUMONIA":
            p2 = np.array([p[1], p[2]]) / max(p[1] + p[2], 1e-8)
            stage2 = _stage("stage2", p2, t)
            final = stage2.label
        class_probs = {
            "NORMAL": float(p[0]),
            "BACTERIAL": float(p[1]),
            "VIRAL": float(p[2]),
        }
        target = TASK_CLASSES["three_class"][int(np.argmax(p))]
        confidences = [stage1.confidence] + ([stage2.confidence] if stage2 else [])
        return ModelResult(
            model=arch,  # type: ignore[arg-type]
            model_name=ARCHS[arch].display_name,
            mode="three_class",
            stage1=stage1,
            stage2=stage2,
            final_label=final,  # type: ignore[arg-type]
            final_confidence=round(class_probs[final], 6),
            class_probabilities={k: round(v, 6) for k, v in class_probs.items()},
            reliability=reliability_for(confidences, threshold),
            explanation=self._explanation(out, target, display),
            inference_ms=round(out.elapsed_ms, 1),
        )

    def predict(
        self,
        data: bytes,
        filename: str | None,
        model: str,
        threshold: float | None = None,
        source_name: str | None = None,
    ) -> PredictResponse:
        """Validate and run the requested model(s). Raises :class:`NotChestXrayError` on rejection."""
        start = time.perf_counter()
        img = load_image(data, filename)
        validation = self._validation_result(img)
        if not validation.is_valid:
            raise NotChestXrayError(validation)

        threshold = self.settings.default_threshold if threshold is None else threshold
        display = make_display_image(img.gray, self.settings.display_max_side)
        archs = list(ARCHS) if model == "both" else [model]
        run = self._run_three_class if self.settings.classification_mode == "three_class" else self._run_two_stage
        results = [run(arch, img.gray, display, threshold) for arch in archs]

        agreement = None
        if len(results) > 1:
            agree = len({r.final_label for r in results}) == 1
            agreement = Agreement(
                agree=agree,
                message=("Both models agree" if agree else "Models disagree — expert review recommended"),
                labels={r.model: r.final_label for r in results},
            )

        return PredictResponse(
            id=uuid.uuid4().hex,
            created_at=datetime.now(timezone.utc),
            source_name=source_name,
            image=validation.image,
            image_png=encode_png_data_uri(display),
            validation=validation,
            results=results,
            agreement=agreement,
            is_mock=self.provider.is_mock,
            total_ms=round((time.perf_counter() - start) * 1000, 1),
        )
