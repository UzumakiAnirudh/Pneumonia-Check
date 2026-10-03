"""Evaluation metrics in the JSON schema consumed by the Performance dashboard.

Used by ``training/evaluate.py``, ``training/external_validate.py`` and
``scripts/generate_demo_metrics.py`` so every producer writes the same format.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from app.services.calibration import expected_calibration_error, reliability_curve


def _r(x: float) -> float:
    return round(float(x), 4)


def roc_points(y_true: np.ndarray, score: np.ndarray, max_points: int = 80) -> dict[str, Any]:
    """ROC curve downsampled to at most ``max_points`` points."""
    fpr, tpr, _ = roc_curve(y_true, score)
    if len(fpr) > max_points:
        idx = np.unique(np.linspace(0, len(fpr) - 1, max_points).round().astype(int))
        fpr, tpr = fpr[idx], tpr[idx]
    return {
        "fpr": [_r(v) for v in fpr],
        "tpr": [_r(v) for v in tpr],
        "auc": _r(roc_auc_score(y_true, score)),
    }


def binary_task_metrics(
    y_true: np.ndarray,
    probs: np.ndarray,
    labels: list[str],
    probs_uncalibrated: np.ndarray | None = None,
) -> dict[str, Any]:
    """Metrics for a 2-class task. ``probs`` is (N, 2); the positive class is index 1."""
    y_true = np.asarray(y_true).astype(int)
    probs = np.asarray(probs)
    y_pred = probs.argmax(axis=1)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    has_pos, has_neg = bool((y_true == 1).any()), bool((y_true == 0).any())
    # Metrics that are undefined for single-class sets (e.g. a normals-only external set) are None, not 0.
    out: dict[str, Any] = {
        "labels": labels,
        "positive_label": labels[1],
        "n": int(len(y_true)),
        "metrics": {
            "accuracy": _r(accuracy_score(y_true, y_pred)),
            "precision": _r(precision_score(y_true, y_pred, zero_division=0)) if (tp + fp) and has_pos else None,
            "recall": _r(recall_score(y_true, y_pred, zero_division=0)) if has_pos else None,
            "specificity": _r(tn / (tn + fp)) if has_neg else None,
            "f1": _r(f1_score(y_true, y_pred, zero_division=0)) if has_pos else None,
            "roc_auc": _r(roc_auc_score(y_true, probs[:, 1])) if has_pos and has_neg else None,
        },
        "confusion_matrix": cm.tolist(),
        "roc": roc_points(y_true, probs[:, 1]) if has_pos and has_neg else None,
    }
    out["calibration"] = calibration_block(probs, y_true, probs_uncalibrated)
    return out


def multiclass_task_metrics(
    y_true: np.ndarray,
    probs: np.ndarray,
    labels: list[str],
    probs_uncalibrated: np.ndarray | None = None,
) -> dict[str, Any]:
    """Macro-averaged metrics for the 3-class task (or the combined two-stage pipeline)."""
    y_true = np.asarray(y_true).astype(int)
    probs = np.asarray(probs)
    y_pred = probs.argmax(axis=1)
    k = len(labels)
    cm = confusion_matrix(y_true, y_pred, labels=list(range(k)))
    specs = []
    for i in range(k):
        tn = cm.sum() - cm[i].sum() - cm[:, i].sum() + cm[i, i]
        fp = cm[:, i].sum() - cm[i, i]
        specs.append(tn / (tn + fp) if (tn + fp) else 0.0)
    try:
        auc = roc_auc_score(y_true, probs, multi_class="ovr", average="macro")
    except ValueError:
        auc = 0.0
    return {
        "labels": labels,
        "positive_label": "macro",
        "n": int(len(y_true)),
        "metrics": {
            "accuracy": _r(accuracy_score(y_true, y_pred)),
            "precision": _r(precision_score(y_true, y_pred, average="macro", zero_division=0)),
            "recall": _r(recall_score(y_true, y_pred, average="macro", zero_division=0)),
            "specificity": _r(np.mean(specs)),
            "f1": _r(f1_score(y_true, y_pred, average="macro", zero_division=0)),
            "roc_auc": _r(auc),
        },
        "confusion_matrix": cm.tolist(),
        "roc": None,
        "calibration": calibration_block(probs, y_true, probs_uncalibrated),
    }


def calibration_block(probs: np.ndarray, y_true: np.ndarray, probs_uncalibrated: np.ndarray | None) -> dict[str, Any]:
    curve = reliability_curve(probs, y_true)
    return {
        **curve,
        "ece_before": (
            _r(expected_calibration_error(probs_uncalibrated, y_true)) if probs_uncalibrated is not None else None
        ),
        "ece_after": _r(expected_calibration_error(probs, y_true)),
    }


def performance_drop(internal: dict[str, float | None], external: dict[str, float | None]) -> dict[str, float]:
    """External minus internal, per metric (negative = worse externally). Undefined metrics are skipped."""
    return {
        k: _r(external[k] - internal[k])  # type: ignore[operator]
        for k in external
        if external[k] is not None and internal.get(k) is not None
    }


def empty_metrics() -> dict[str, Any]:
    return {
        "is_demo": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "notes": "",
        "dataset": {"name": "", "split": {}, "description": ""},
        "internal": {},
        "external": [],
        "training_curves": {},
        "gallery": [],
    }


def update_metrics_file(path: Path, update: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    """Load (or create) the metrics JSON, apply ``update`` in place, and save.

    A demo file is replaced by a fresh one the first time real results are written.
    """
    data = json.loads(path.read_text()) if path.exists() else empty_metrics()
    if data.get("is_demo"):
        data = empty_metrics()
    update(data)
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1))
    return data
