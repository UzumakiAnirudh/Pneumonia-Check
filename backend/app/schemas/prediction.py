"""Prediction and validation schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ModelKey = Literal["densenet", "swin"]
ModelChoice = Literal["densenet", "swin", "both"]
Stage1Label = Literal["NORMAL", "PNEUMONIA"]
Stage2Label = Literal["BACTERIAL", "VIRAL"]
FinalLabel = Literal["NORMAL", "BACTERIAL", "VIRAL"]
AnyLabel = Literal["NORMAL", "PNEUMONIA", "BACTERIAL", "VIRAL"]


class ImageInfo(BaseModel):
    width: int
    height: int
    format: str
    file_size_bytes: int
    is_dicom: bool = False


class ValidationResult(BaseModel):
    is_valid: bool = Field(description="True when the image can be analysed.")
    is_chest_xray: bool
    score: float = Field(ge=0, le=1, description="Likelihood the image is a frontal chest X-ray.")
    method: Literal["heuristic", "model"]
    message: str
    reasons: list[str] = []
    warnings: list[str] = []
    image: ImageInfo


class StageResult(BaseModel):
    label: AnyLabel
    confidence: float = Field(ge=0, le=1, description="Calibrated probability of `label`.")
    probabilities: dict[str, float]
    temperature: float = 1.0


class Reliability(BaseModel):
    level: Literal["high", "low"]
    threshold: float
    message: str


class DominantRegion(BaseModel):
    vertical: Literal["upper", "middle", "lower"]
    side: Literal["left", "right", "bilateral"] = Field(description="Patient side (radiological convention).")
    label: str


class Explanation(BaseModel):
    method: str = "Grad-CAM"
    target_label: AnyLabel
    target_layer: str
    heatmap_png: str = Field(description="Data URI of the colour-mapped heatmap.")
    overlay_png: Optional[str] = Field(default=None, description="Data URI of the heatmap blended on the X-ray.")
    dominant_region: DominantRegion
    description: str
    lung_attention_pct: float = Field(ge=0, le=100)
    lung_area_pct: Optional[float] = Field(
        default=None, ge=0, le=100, description="Image share covered by the lung mask (chance level)."
    )
    region_scores: dict[str, float]


class ModelResult(BaseModel):
    model: ModelKey
    model_name: str
    mode: Literal["two_stage", "three_class"]
    stage1: StageResult
    stage2: Optional[StageResult] = None
    final_label: FinalLabel
    final_confidence: float = Field(ge=0, le=1)
    class_probabilities: dict[str, float] = Field(
        description="NORMAL/BACTERIAL/VIRAL joint probabilities, or NORMAL/PNEUMONIA when Stage 2 did not run."
    )
    reliability: Reliability
    explanation: Optional[Explanation] = None
    inference_ms: float


class Agreement(BaseModel):
    agree: bool
    message: str
    labels: dict[str, FinalLabel]


class PredictResponse(BaseModel):
    id: str
    created_at: datetime
    source_name: Optional[str] = None
    image: ImageInfo
    image_png: str = Field(description="Data URI of the metadata-free grayscale display image.")
    validation: ValidationResult
    results: list[ModelResult]
    agreement: Optional[Agreement] = None
    is_mock: bool
    total_ms: float
    saved_to_history: bool = False
