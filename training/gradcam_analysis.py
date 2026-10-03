"""Grad-CAM analysis on the internal test set.

* Computes Grad-CAM for every test image (Stage 1, or the 3-class model) with the same code as
  the API (app.services.gradcam), and the share of attention inside the estimated lung fields.
* Builds a gallery of correct predictions, misclassifications and failure cases
  (correct but low-confidence, or with in-lung attention no higher than the lung area, i.e. chance).
* Saves overlays to backend/metrics/gallery/ and updates metrics.json ``gallery``.
* Writes per-category lung-attention statistics to training/outputs/gradcam_summary_<arch>.json.

Example:
    python gradcam_analysis.py --arch densenet --per-category 6
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import _common
import cv2
import numpy as np
import torch

from app.models.architectures import (
    ARCHS,
    TASK_CLASSES,
    get_module,
    reshape_transform_for,
)
from app.services.calibration import softmax
from app.services.evaluation import update_metrics_file
from app.services.gradcam import blend, colorize, compute_gradcam, describe_attention
from app.services.preprocessing import to_model_tensor
from dataset import CXRDataset, load_splits


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--arch", choices=list(ARCHS), required=True)
    p.add_argument("--task", choices=["stage1", "three_class"], default="stage1")
    p.add_argument("--per-category", type=int, default=6)
    p.add_argument(
        "--max-images",
        type=int,
        default=0,
        help="Analyse at most N test images (0 = all)",
    )
    p.add_argument("--low-confidence", type=float, default=0.75)
    p.add_argument("--splits", type=Path, default=_common.DEFAULT_SPLITS)
    p.add_argument("--weights-dir", type=Path, default=_common.DEFAULT_WEIGHTS)
    p.add_argument("--metrics-path", type=Path, default=_common.DEFAULT_METRICS)
    p.add_argument("--gallery-dir", type=Path, default=_common.DEFAULT_GALLERY)
    p.add_argument("--device", default="auto")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    device = _common.get_device(args.device)
    model, preprocess = _common.load_trained_model(args.arch, args.task, args.weights_dir, device)
    layer = get_module(model, ARCHS[args.arch].target_layer)
    temperature = _common.read_temperatures(args.weights_dir).get(f"{args.arch}_{args.task}", 1.0)
    classes = TASK_CLASSES[args.task]

    ds = CXRDataset(load_splits(args.splits)["test"], args.task, preprocess)
    order = np.arange(len(ds))
    if args.max_images and len(ds) > args.max_images:
        order = np.random.default_rng(args.seed).choice(order, args.max_images, replace=False)

    records = []
    for i, idx in enumerate(order):
        img = ds.load_uint8(int(idx))
        x = to_model_tensor(img).unsqueeze(0).to(device)
        logits, cam = compute_gradcam(model, layer, x, reshape_transform_for(args.arch))
        probs = softmax(logits, temperature)
        pred = int(probs.argmax())
        summary = describe_attention(cam, img)
        true = int(ds.labels[idx])
        records.append(
            {
                "idx": int(idx),
                "true": true,
                "pred": pred,
                "conf": float(probs[pred]),
                "lung_pct": summary.lung_attention_pct,
                "outside": summary.attention_outside_lungs,
                "description": summary.description,
                "cam": cam,
                "img": img,
            }
        )
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(order)}")

    def category(r) -> str:
        if r["true"] != r["pred"]:
            return "misclassified"
        if r["conf"] < args.low_confidence or r["outside"]:
            return "failure"
        return "correct"

    for r in records:
        r["category"] = category(r)

    summary = {}
    for cat in ("correct", "misclassified", "failure"):
        vals = [r["lung_pct"] for r in records if r["category"] == cat]
        summary[cat] = {
            "n": len(vals),
            "mean_lung_attention_pct": round(float(np.mean(vals)), 2) if vals else None,
        }
    summary["all"] = {
        "n": len(records),
        "mean_lung_attention_pct": round(float(np.mean([r["lung_pct"] for r in records])), 2),
    }
    print(json.dumps(summary, indent=2))
    _common.OUTPUTS.mkdir(parents=True, exist_ok=True)
    (_common.OUTPUTS / f"gradcam_summary_{args.arch}.json").write_text(json.dumps(summary, indent=2))

    args.gallery_dir.mkdir(parents=True, exist_ok=True)
    gallery = []
    picks = {
        "correct": sorted((r for r in records if r["category"] == "correct"), key=lambda r: -r["conf"]),
        "misclassified": sorted(
            (r for r in records if r["category"] == "misclassified"),
            key=lambda r: -r["conf"],
        ),
        "failure": sorted(
            (r for r in records if r["category"] == "failure"),
            key=lambda r: r["lung_pct"],
        ),
    }
    for cat, rows in picks.items():
        for r in rows[: args.per_category]:
            name = f"{args.arch}_{cat}_{r['idx']}.jpg"
            overlay = blend(r["img"], colorize(r["cam"]), 0.45)
            cv2.imwrite(
                str(args.gallery_dir / name),
                cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR),
                [cv2.IMWRITE_JPEG_QUALITY, 88],
            )
            if cat == "misclassified":
                note = f"Predicted {classes[r['pred']].title()} with {r['conf']:.0%} confidence."
            elif cat == "failure":
                note = (
                    "Correct label, but attention is not concentrated on the lung fields (no more than chance)."
                    if r["outside"]
                    else "Correct but low confidence — would be flagged for expert review."
                )
            else:
                note = r["description"]
            gallery.append(
                {
                    "model": args.arch,
                    "category": cat,
                    "true_label": classes[r["true"]],
                    "pred_label": classes[r["pred"]],
                    "confidence": round(r["conf"], 4),
                    "lung_attention_pct": r["lung_pct"],
                    "image": name,
                    "note": note,
                }
            )

    def put(data: dict) -> None:
        data["gallery"] = [g for g in data.get("gallery", []) if g.get("model") != args.arch] + gallery

    update_metrics_file(args.metrics_path, put)
    print(f"Saved {len(gallery)} gallery images to {args.gallery_dir}")


if __name__ == "__main__":
    torch.set_grad_enabled(True)
    main()
