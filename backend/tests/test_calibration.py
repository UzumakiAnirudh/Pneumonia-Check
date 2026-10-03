import numpy as np
import pytest

from app.services.calibration import TemperatureStore, expected_calibration_error, fit_temperature, softmax


def test_softmax_temperature_flattens():
    logits = np.array([2.0, 0.0])
    p1 = softmax(logits, 1.0)
    p2 = softmax(logits, 2.0)
    assert p1.sum() == pytest.approx(1.0)
    assert p2[0] < p1[0]
    assert np.argmax(p1) == np.argmax(p2)


def test_fit_temperature_recovers_overconfidence():
    rng = np.random.default_rng(0)
    n = 4000
    y = rng.integers(0, 2, n)
    true_logit = np.where(y == 1, 1, -1) * 1.0 + rng.normal(0, 1.0, n)
    # Well-calibrated logits are 2*sep*margin; make the model 2.5x overconfident.
    logits = np.c_[np.zeros(n), 2.0 * true_logit * 2.5]
    t = fit_temperature(logits, y)
    assert t == pytest.approx(2.5, rel=0.15)
    before = expected_calibration_error(softmax(logits), y)
    after = expected_calibration_error(softmax(logits, t), y)
    assert after < before


def test_temperature_store(tmp_path):
    path = tmp_path / "temperature.json"
    path.write_text('{"densenet_stage1": 1.5, "bad": -1}')
    store = TemperatureStore(path)
    assert store.loaded
    assert store.get("densenet", "stage1") == 1.5
    assert store.get("swin", "stage1") == 1.0
    assert "bad" not in store.values
    assert not TemperatureStore(tmp_path / "missing.json").loaded


def test_single_class_metrics_are_undefined_not_zero():
    from app.services.evaluation import binary_task_metrics, performance_drop

    y = np.zeros(10, int)
    probs = np.c_[np.full(10, 0.9), np.full(10, 0.1)]
    probs[0] = [0.2, 0.8]  # one false positive
    m = binary_task_metrics(y, probs, ["NORMAL", "PNEUMONIA"])["metrics"]
    assert m["specificity"] == 0.9 and m["accuracy"] == 0.9
    assert m["roc_auc"] is None and m["recall"] is None and m["precision"] is None
    assert performance_drop({"specificity": 0.95, "roc_auc": 0.99}, m) == {"specificity": -0.05}
