"""Evaluate trained models on the internal test split.

For each <arch>_<task> it computes accuracy, precision, recall/sensitivity, specificity, F1,
ROC-AUC, the confusion matrix, ROC curve and a calibration (reliability) curve using the
calibrated probabilities (temperature from weights/temperature.json). When both Stage 1 and
Stage 2 weights exist, the combined two-stage pipeline is also evaluated as a 3-class problem.

Writes:
    backend/metrics/metrics.json         internal.<arch>.<task>   (read by the dashboard)
    training/outputs/figures/*.png       ROC, confusion matrix and calibration plots for the report

Examples:
    python evaluate.py                    # every model found
    python evaluate.py --arch swin --tasks stage1 stage2
"""

from __future__ import annotations

import argparse
from pathlib import Path

import _common
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402

from app.models.architectures import ARCHS, TASK_CLASSES, weights_filename  # noqa: E402
from app.services.calibration import softmax  # noqa: E402
from app.services.evaluation import (
    binary_task_metrics,
    multiclass_task_metrics,
    update_metrics_file,
)  # noqa: E402
from dataset import CXRDataset, load_splits  # noqa: E402

FIG_DIR = _common.OUTPUTS / "figures"


def plot_task(name: str, result: dict) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    labels = result["labels"]
    cm = np.array(result["confusion_matrix"])

    fig, ax = plt.subplots(figsize=(4, 3.6), dpi=150)
    ax.imshow(cm / cm.sum(axis=1, keepdims=True).clip(min=1), cmap="Blues", vmin=0, vmax=1)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j,
                i,
                cm[i, j],
                ha="center",
                va="center",
                color="white" if cm[i, j] > cm[i].sum() / 2 else "black",
            )
    ax.set_xticks(range(len(labels)), labels, rotation=20)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(name)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"cm_{name}.png")
    plt.close(fig)

    if result.get("roc"):
        fig, ax = plt.subplots(figsize=(4, 4), dpi=150)
        ax.plot(
            result["roc"]["fpr"],
            result["roc"]["tpr"],
            lw=2,
            label=f"AUC = {result['roc']['auc']:.3f}",
        )
        ax.plot([0, 1], [0, 1], "--", color="grey", lw=1)
        ax.set_xlabel("False positive rate")
        ax.set_ylabel("True positive rate")
        ax.set_title(f"ROC — {name}")
        ax.legend(loc="lower right")
        fig.tight_layout()
        fig.savefig(FIG_DIR / f"roc_{name}.png")
        plt.close(fig)

    cal = result.get("calibration")
    if cal and cal["bin_confidence"]:
        fig, ax = plt.subplots(figsize=(4, 4), dpi=150)
        ax.plot([0, 1], [0, 1], "--", color="grey", lw=1, label="Perfect")
        ax.plot(
            cal["bin_confidence"],
            cal["bin_accuracy"],
            "o-",
            lw=2,
            label=f"ECE = {cal['ece_after']:.3f}",
        )
        ax.set_xlabel("Confidence")
        ax.set_ylabel("Accuracy")
        ax.set_title(f"Calibration — {name}")
        ax.legend(loc="upper left")
        fig.tight_layout()
        fig.savefig(FIG_DIR / f"calibration_{name}.png")
        plt.close(fig)


def test_logits(arch: str, task: str, df: pd.DataFrame, args, device) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (logits, labels, domain per row: 'adult' or 'pediatric')."""
    model, preprocess = _common.load_trained_model(arch, task, args.weights_dir, device)
    ds = CXRDataset(df, task, preprocess, cache=args.cache)
    logits, labels = _common.collect_logits(
        model,
        DataLoader(ds, batch_size=args.batch_size, num_workers=args.workers),
        device,
    )
    return logits, labels, domains_of(ds.df)


def domains_of(df: pd.DataFrame) -> np.ndarray:
    if "source" not in df:
        return np.full(len(df), "pediatric")
    return np.where(df["source"].fillna("kermany").to_numpy() == "kermany", "pediatric", "adult")


def by_domain(fn, labels, probs, class_names, domains) -> dict:
    """Same metrics restricted to each population present in the test set."""
    out = {}
    for d in ("pediatric", "adult"):
        k = domains == d
        if k.sum() >= 5:
            out[d] = fn(labels[k], probs[k], class_names)
    return out


def fmt(res: dict) -> str:
    return " ".join(f"{k}={v:.4f}" if v is not None else f"{k}=n/a" for k, v in res["metrics"].items())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--arch", choices=list(ARCHS), nargs="*", default=list(ARCHS))
    p.add_argument("--tasks", choices=list(TASK_CLASSES), nargs="*", default=list(TASK_CLASSES))
    p.add_argument("--splits", type=Path, default=_common.DEFAULT_SPLITS)
    p.add_argument("--weights-dir", type=Path, default=_common.DEFAULT_WEIGHTS)
    p.add_argument("--metrics-path", type=Path, default=_common.DEFAULT_METRICS)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--cache", action="store_true", help="Cache preprocessed images on disk (much faster on CPU/MPS)")
    p.add_argument("--device", default="auto")
    args = p.parse_args()

    device = _common.get_device(args.device)
    splits = load_splits(args.splits)
    test = splits["test"]
    temps = _common.read_temperatures(args.weights_dir)
    results: dict[str, dict] = {}
    domain_results: dict[str, dict] = {}

    for arch in args.arch:
        results[arch] = {}
        for task in args.tasks:
            if not (args.weights_dir / weights_filename(arch, task)).exists():
                continue
            logits, labels, doms = test_logits(arch, task, test, args, device)
            t = temps.get(f"{arch}_{task}", 1.0)
            probs, raw = softmax(logits, t), softmax(logits)
            fn = binary_task_metrics if len(TASK_CLASSES[task]) == 2 else multiclass_task_metrics
            res = fn(labels, probs, TASK_CLASSES[task], raw)
            results[arch][task] = res
            domain_results.setdefault(arch, {})[task] = by_domain(fn, labels, probs, TASK_CLASSES[task], doms)
            plot_task(f"{arch}_{task}", res)
            print(f"{arch:9s} {task:12s} n={res['n']:5d} {fmt(res)}")
            for d, r in domain_results[arch][task].items():
                print(f"{'':9s}   {d:10s} n={r['n']:5d} {fmt(r)}")

        # Two-stage pipeline on the full test set: P(N), P(P)P(B|P), P(P)P(V|P).
        if all((args.weights_dir / weights_filename(arch, t)).exists() for t in ("stage1", "stage2")):
            l1, _, doms = test_logits(arch, "stage1", test, args, device)
            # Stage 2 is applied to every image (labels are irrelevant here), mapping all rows.
            stage2_df = test.assign(label=test["label"].where(test["label"] != "NORMAL", "BACTERIAL"))
            l2, _, _ = test_logits(arch, "stage2", stage2_df, args, device)
            p1 = softmax(l1, temps.get(f"{arch}_stage1", 1.0))
            p2 = softmax(l2, temps.get(f"{arch}_stage2", 1.0))
            p3 = np.c_[p1[:, 0], p1[:, 1] * p2[:, 0], p1[:, 1] * p2[:, 1]]
            y3 = test["label"].map({"NORMAL": 0, "BACTERIAL": 1, "VIRAL": 2}).to_numpy()
            res = multiclass_task_metrics(y3, p3, TASK_CLASSES["three_class"])
            results[arch]["pipeline"] = res
            domain_results[arch]["pipeline"] = by_domain(
                multiclass_task_metrics, y3, p3, TASK_CLASSES["three_class"], doms
            )
            plot_task(f"{arch}_pipeline", res)
            print(f"{arch:9s} {'pipeline':12s} n={res['n']:5d} {fmt(res)}")
            for d, r in domain_results[arch]["pipeline"].items():
                print(f"{'':9s}   {d:10s} n={r['n']:5d} {fmt(r)}")

    counts = splits["train"].shape[0], splits["val"].shape[0], test.shape[0]

    def put(data: dict) -> None:
        for arch, tasks in results.items():
            if tasks:
                data.setdefault("internal", {}).setdefault(arch, {}).update(tasks)
        mixed = "source" in test and (test["source"] != "kermany").any()
        data["dataset"] = {
            "name": (
                "Kermany pediatric + adult (Cohen, Figure1, Shenzhen)"
                if mixed
                else "Kermany et al. — Chest X-Ray Images (Pneumonia)"
            ),
            "split": dict(zip(("train", "val", "test"), map(int, counts))),
            "description": (
                "Pediatric Kermany CXRs plus adult viral/bacterial pneumonia and normal CXRs; each source "
                "re-split 70/15/15 grouped by patient."
                if mixed
                else "Pediatric (1–5 y) AP chest X-rays, single centre; re-split 70/15/15 grouped by patient."
            ),
        }
        if mixed:
            # Shenzhen is now part of training, so it can no longer serve as an external test.
            data["external"] = [e for e in data.get("external", []) if not e.get("name", "").startswith("Shenzhen")]
        data["by_domain"] = domain_results
        data["notes"] = "Internal test set results from training/evaluate.py."

    update_metrics_file(args.metrics_path, put)
    print(f"Updated {args.metrics_path}; figures in {FIG_DIR}")


if __name__ == "__main__":
    main()
