import numpy as np
import torch

from app.services.preprocessing import load_image
from app.services.validator import REJECT_MESSAGE, HeuristicValidator, ImageValidator
from tests.conftest import encode

validator = ImageValidator(None, torch.device("cpu"), min_resolution=128, warn_resolution=512)


def test_phantom_cxrs_are_accepted(sample_bytes):
    assert sample_bytes, "samples missing — run scripts/generate_samples.py"
    for name, data in sample_bytes.items():
        outcome = validator.validate(load_image(data))
        assert outcome.is_valid, (name, outcome.reasons)
        assert outcome.method == "heuristic"


def test_colour_photo_rejected(colour_photo):
    outcome = validator.validate(load_image(colour_photo))
    assert not outcome.is_chest_xray
    assert outcome.message == REJECT_MESSAGE
    assert any("colour" in r for r in outcome.reasons)


def test_document_rejected(document):
    outcome = validator.validate(load_image(document))
    assert not outcome.is_chest_xray


def test_noise_rejected():
    noise = np.random.default_rng(1).integers(0, 255, (600, 600), dtype=np.uint8)
    assert not validator.validate(load_image(encode(noise))).is_chest_xray


def test_tiny_image_rejected_for_quality(sample_bytes):
    import cv2

    small = cv2.resize(load_image(sample_bytes["normal_01"]).gray, (90, 100))
    outcome = validator.validate(load_image(encode(small)))
    assert not outcome.is_valid
    assert not outcome.quality_ok
    assert any("too small" in r for r in outcome.reasons)


def test_low_resolution_warns(sample_bytes):
    import cv2

    small = cv2.resize(load_image(sample_bytes["normal_01"]).gray, (300, 333))
    outcome = validator.validate(load_image(encode(small)))
    assert outcome.is_valid
    assert any("Low resolution" in w for w in outcome.warnings)


def test_heuristic_score_bounds(sample_bytes):
    score, _ = HeuristicValidator().score(load_image(sample_bytes["viral_01"]))
    assert 0.0 <= score <= 1.0
