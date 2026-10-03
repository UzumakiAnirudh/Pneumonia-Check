import numpy as np
import pytest
import torch

from app.models.architectures import ARCHS, TASK_CLASSES, build_model, get_module, swin_reshape_transform
from app.services.gradcam import blend, colorize, compute_gradcam, describe_attention, normalize_cam
from app.services.lung_mask import estimate_lung_mask, template_mask
from app.services.preprocessing import load_image, prepare_uint8, preprocess


def _blob(cx: float, cy: float, size: int = 224, sigma: float = 0.07) -> np.ndarray:
    yy, xx = np.mgrid[0:size, 0:size] / size
    return np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma**2)).astype(np.float32)


def test_describe_uses_radiological_convention(sample_bytes):
    img = prepare_uint8(load_image(sample_bytes["normal_01"]).gray)
    # Image-left lower => patient's right lower lung.
    summary = describe_attention(_blob(0.3, 0.7), img, template_mask(224))
    assert summary.side == "right" and summary.vertical == "lower"
    assert "lower right lung" in summary.description
    assert summary.lung_attention_pct > 70
    assert 10 < summary.lung_area_pct < 50 and not summary.attention_outside_lungs
    assert sum(summary.region_scores.values()) == pytest.approx(1.0, abs=1e-3)


def test_describe_bilateral_and_outside(sample_bytes):
    img = prepare_uint8(load_image(sample_bytes["normal_01"]).gray)
    both = _blob(0.3, 0.45) + _blob(0.7, 0.45)
    assert describe_attention(both, img, template_mask(224)).side == "bilateral"
    corner = describe_attention(_blob(0.05, 0.05, sigma=0.04), img, template_mask(224))
    assert corner.lung_attention_pct < corner.lung_area_pct
    assert corner.attention_outside_lungs
    assert "not concentrated on the lung fields" in corner.description


def test_lung_mask_plausible(sample_bytes):
    img = prepare_uint8(load_image(sample_bytes["normal_01"]).gray)
    mask = estimate_lung_mask(img)
    assert mask.shape == (224, 224) and mask.dtype == bool
    assert 0.1 < mask.mean() < 0.5


def test_colorize_and_blend_shapes():
    cam = normalize_cam(np.random.default_rng(0).random((100, 80)))
    heat = colorize(cam)
    assert heat.shape == (100, 80, 3) and heat.dtype == np.uint8
    out = blend(np.zeros((100, 80), np.uint8), heat, 0.5)
    assert out.shape == (100, 80, 3)


def test_swin_reshape_transform_shapes():
    nhwc = torch.zeros(2, 7, 7, 768)
    assert swin_reshape_transform(nhwc).shape == (2, 768, 7, 7)
    tokens = torch.zeros(2, 49, 768)
    assert swin_reshape_transform(tokens).shape == (2, 768, 7, 7)


@pytest.mark.parametrize("arch", ["densenet", "swin"])
def test_gradcam_output_shape_real_models(arch, sample_bytes):
    pytest.importorskip("pytorch_grad_cam")
    torch.manual_seed(0)
    model = build_model(arch, len(TASK_CLASSES["stage1"])).eval()
    x = preprocess(load_image(sample_bytes["bacterial_01"]).gray)
    reshape = swin_reshape_transform if arch == "swin" else None
    logits, cam = compute_gradcam(model, get_module(model, ARCHS[arch].target_layer), x, reshape)
    assert logits.shape == (2,)
    assert cam.shape == (224, 224)
    assert 0.0 <= cam.min() and cam.max() <= 1.0
