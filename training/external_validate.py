"""External validation of Stage 1 (Normal vs Pneumonia) on an independent dataset.

External sets (e.g. RSNA Pneumonia Detection Challenge) have no viral/bacterial labels, so
only Stage 1 is evaluated. The performance drop versus the internal test set is reported and
written to backend/metrics/metrics.json (``external`` list, replaced by dataset name).

Input options:
  1. Generic CSV with columns ``path`` and ``label`` (0/1 or NORMAL/PNEUMONIA):
        python external_validate.py --name "My hospital" --csv data/external.csv
  2. RSNA directly (DICOM images + stage_2_train_labels.csv; Target=1 means pneumonia):
        python external_validate.py --name "RSNA Pneumonia Detection" \\
            --rsna-labels rsna/stage_2_train_labels.csv --rsna-images rsna/stage_2_train_images --limit 2000

NOTE on RSNA: its negative class includes "No Lung Opacity / Not Normal" images; this domain
shift (adults, other abnormalities) is exactly what external validation is meant to expose.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import _common
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader

from app.models.architectures import ARCHS, weights_filename
from app.services.calibration import softmax
from app.services.evaluation import (
    binary_task_metrics,
    performance_drop,
    update_metrics_file,
)
from dataset import CXRDataset


def rsna_frame(labels_csv: Path, images_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(labels_csv).groupby("patientId", as_index=False)["Target"].max()
    df["path"] = df["patientId"].map(lambda pid: str(images_dir / f"{pid}.dcm"))
    df["label"] = df["Target"].map({0: "NORMAL", 1: "BACTERIAL"})  # pneumonia -> any positive stage-1 label
    return df[["path", "label"]]


def csv_frame(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    raw = df["label"].astype(str).str.upper()
    df["label"] = np.where(raw.isin(["1", "PNEUMONIA", "BACTERIAL", "VIRAL"]), "BACTERIAL", "NORMAL")
    return df[["path", "label"]]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--csv", type=Path)
    p.add_argument("--rsna-labels", type=Path)
    p.add_argument("--rsna-images", type=Path)
    p.add_argument("--limit", type=int, default=0, help="Stratified random subset size (0 = all)")
    p.add_argument("--arch", choices=list(ARCHS), nargs="*", default=list(ARCHS))
    p.add_argument("--weights-dir", type=Path, default=_common.DEFAULT_WEIGHTS)
    p.add_argument("--metrics-path", type=Path, default=_common.DEFAULT_METRICS)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--cache", action="store_true", help="Cache preprocessed images on disk (much faster on CPU/MPS)")
    p.add_argument("--device", default="auto")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    if args.csv:
        df = csv_frame(args.csv)
    elif args.rsna_labels and args.rsna_images:
        df = rsna_frame(args.rsna_labels, args.rsna_images)
    else:
        p.error("give --csv, or --rsna-labels and --rsna-images")
    if args.limit and len(df) > args.limit:
        frac = args.limit / len(df)
        df = df.groupby("label", group_keys=False).apply(lambda g: g.sample(frac=frac, random_state=args.seed))
    df = df.reset_index(drop=True)
    print(f"{args.name}: {len(df)} images, {int((df.label != 'NORMAL').sum())} pneumonia")

    device = _common.get_device(args.device)
    temps = _common.read_temperatures(args.weights_dir)
    internal = {}
    if args.metrics_path.exists():
        import json

        internal = json.loads(args.metrics_path.read_text()).get("internal", {})

    models: dict = {}
    for arch in args.arch:
        if not (args.weights_dir / weights_filename(arch, "stage1")).exists():
            continue
        model, preprocess = _common.load_trained_model(arch, "stage1", args.weights_dir, device)
        ds = CXRDataset(df, "stage1", preprocess, cache=args.cache)
        logits, labels = _common.collect_logits(
            model,
            DataLoader(ds, batch_size=args.batch_size, num_workers=args.workers),
            device,
        )
        res = binary_task_metrics(
            labels,
            softmax(logits, temps.get(f"{arch}_stage1", 1.0)),
            ["NORMAL", "PNEUMONIA"],
            softmax(logits),
        )
        ref = internal.get(arch, {}).get("stage1", {}).get("metrics")
        drop = performance_drop(ref, res["metrics"]) if ref else {}
        models[arch] = {"stage1": res, "drop": drop}
        print(
            f"{arch}: " + " ".join(f"{k}={v:.4f}" if v is not None else f"{k}=n/a" for k, v in res["metrics"].items())
        )
        if drop:
            print("   change vs internal: " + " ".join(f"{k}={v:+.4f}" for k, v in drop.items()))

    if not models:
        raise SystemExit(f"No Stage 1 weights found in {args.weights_dir}")

    def put(data: dict) -> None:
        entry = {
            "name": args.name,
            "description": args.description,
            "n": int(len(df)),
            "models": models,
        }
        data["external"] = [e for e in data.get("external", []) if e.get("name") != args.name] + [entry]

    update_metrics_file(args.metrics_path, put)
    print(f"Updated {args.metrics_path}")


if __name__ == "__main__":
    main()
