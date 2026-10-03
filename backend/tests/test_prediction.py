"""Prediction schema and two-stage logic, using the mock provider and fake real-model weights."""

import numpy as np
import pytest
import torch

from app.models.architectures import TASK_CLASSES, build_model, weights_filename
from app.models.mock_provider import MockModelProvider
from app.models.provider import InferenceOutput, ModelProvider, ModelUnavailableError
from app.models.real_provider import TorchModelProvider
from app.schemas import PredictResponse
from app.services.calibration import TemperatureStore
from app.services.predictor import NotChestXrayError, PredictionService, reliability_for
from app.services.validator import ImageValidator
from tests.conftest import make_settings


def _service(tmp_path, provider: ModelProvider | None = None, **overrides) -> PredictionService:
    settings = make_settings(tmp_path, **overrides)
    return PredictionService(
        settings,
        provider or MockModelProvider(),
        ImageValidator(None, torch.device("cpu")),
        TemperatureStore(None),
    )


class FixedProvider(ModelProvider):
    """Returns fixed logits per task, to test the hierarchy deterministically."""

    def __init__(self, logits: dict[str, list[float]]):
        self.logits = logits
        self.calls: list[str] = []

    def available(self, arch, task):
        return task in self.logits

    def status(self, tasks):
        return []

    def infer(self, arch, task, gray, explain=False):
        self.calls.append(task)
        cam = np.ones((224, 224), np.float32) if explain else None
        return InferenceOutput(np.array(self.logits[task], np.float32), np.zeros((224, 224), np.uint8), cam, "x")


def test_mock_prediction_schema(tmp_path, sample_bytes):
    resp = _service(tmp_path).predict(sample_bytes["bacterial_01"], "b.png", "both", 0.75, "Bacterial A")
    PredictResponse.model_validate(resp.model_dump())
    assert resp.is_mock and len(resp.results) == 2 and resp.agreement is not None
    for r in resp.results:
        assert r.stage1.label == "PNEUMONIA" and r.stage2 is not None
        assert r.final_label == r.stage2.label
        assert set(r.class_probabilities) == {"NORMAL", "BACTERIAL", "VIRAL"}
        assert sum(r.class_probabilities.values()) == pytest.approx(1.0, abs=1e-4)
        assert r.explanation and r.explanation.heatmap_png.startswith("data:image/png;base64,")
        assert 0 <= r.explanation.lung_attention_pct <= 100
    assert resp.image_png.startswith("data:image/png;base64,")


def test_stage2_skipped_for_normal(tmp_path, sample_bytes):
    provider = FixedProvider({"stage1": [3.0, 0.0], "stage2": [0.0, 1.0]})
    resp = _service(tmp_path, provider).predict(sample_bytes["normal_01"], None, "densenet")
    r = resp.results[0]
    assert r.final_label == "NORMAL" and r.stage2 is None
    assert provider.calls == ["stage1"]
    assert set(r.class_probabilities) == {"NORMAL", "PNEUMONIA"}


def test_two_stage_joint_probabilities(tmp_path, sample_bytes):
    provider = FixedProvider({"stage1": [0.0, 2.0], "stage2": [0.0, 1.0]})
    r = _service(tmp_path, provider).predict(sample_bytes["viral_01"], None, "swin").results[0]
    p_pneu = 1 / (1 + np.exp(-2.0))
    p_viral = 1 / (1 + np.exp(-1.0))
    assert r.final_label == "VIRAL"
    assert r.class_probabilities["VIRAL"] == pytest.approx(p_pneu * p_viral, abs=1e-5)
    assert r.final_confidence == pytest.approx(p_pneu * p_viral, abs=1e-5)


def test_three_class_mode(tmp_path, sample_bytes):
    provider = FixedProvider({"three_class": [0.0, 2.0, 0.5]})
    r = (
        _service(tmp_path, provider, classification_mode="three_class")
        .predict(sample_bytes["bacterial_01"], None, "densenet")
        .results[0]
    )
    assert r.mode == "three_class" and r.final_label == "BACTERIAL"
    assert r.stage1.label == "PNEUMONIA" and r.stage2 is not None
    assert r.stage2.probabilities["BACTERIAL"] + r.stage2.probabilities["VIRAL"] == pytest.approx(1.0, abs=1e-5)


def test_reliability_threshold():
    assert reliability_for([0.9, 0.8], 0.75).level == "high"
    assert reliability_for([0.9, 0.7], 0.75).level == "low"


def test_rejects_non_cxr(tmp_path, colour_photo):
    with pytest.raises(NotChestXrayError) as exc:
        _service(tmp_path).predict(colour_photo, "p.jpg", "densenet")
    assert not exc.value.validation.is_chest_xray


def test_real_provider_with_random_weights(tmp_path, sample_bytes):
    pytest.importorskip("pytorch_grad_cam")
    weights = tmp_path / "weights"
    weights.mkdir()
    for task in ("stage1", "stage2"):
        torch.save(
            build_model("densenet", len(TASK_CLASSES[task])).state_dict(), weights / weights_filename("densenet", task)
        )
    provider = TorchModelProvider(weights, ["stage1", "stage2"], torch.device("cpu"))
    assert provider.available("densenet", "stage1") and not provider.available("swin", "stage1")
    resp = _service(tmp_path, provider).predict(sample_bytes["viral_01"], None, "densenet")
    assert not resp.is_mock
    assert resp.results[0].explanation is not None
    with pytest.raises(ModelUnavailableError):
        provider.infer("swin", "stage1", np.zeros((300, 300), np.uint8))
