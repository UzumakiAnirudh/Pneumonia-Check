"""Learn temperature scaling on the validation set and write backend/weights/temperature.json.

Examples:
    python calibrate.py --arch densenet --task stage1
    python calibrate.py --all          # every <arch>_<task>.pth found in the weights dir
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import _common
import numpy as np
from torch.utils.data import DataLoader

from app.models.architectures import ARCHS, TASK_CLASSES, weights_filename
from app.services.calibration import (
    expected_calibration_error,
    fit_temperature,
    softmax,
)
from dataset import CXRDataset, load_splits


def calibrate_one(arch: str, task: str, args, device) -> float:
    model, preprocess = _common.load_trained_model(arch, task, args.weights_dir, device)
    ds = CXRDataset(load_splits(args.splits)["val"], task, preprocess, cache=args.cache)
    logits, labels = _common.collect_logits(
        model,
        DataLoader(ds, batch_size=args.batch_size, num_workers=args.workers),
        device,
    )
    t = fit_temperature(logits, labels)
    before = expected_calibration_error(softmax(logits), labels)
    after = expected_calibration_error(softmax(logits, t), labels)
    print(f"{arch}_{task}: T = {t:.4f} | ECE {before:.4f} -> {after:.4f} | n = {len(labels)}")
    return t


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--arch", choices=list(ARCHS))
    p.add_argument("--task", choices=list(TASK_CLASSES))
    p.add_argument("--all", action="store_true")
    p.add_argument("--splits", type=Path, default=_common.DEFAULT_SPLITS)
    p.add_argument("--weights-dir", type=Path, default=_common.DEFAULT_WEIGHTS)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--cache", action="store_true", help="Cache preprocessed images on disk (much faster on CPU/MPS)")
    p.add_argument("--device", default="auto")
    args = p.parse_args()

    if args.all:
        pairs = [(a, t) for a in ARCHS for t in TASK_CLASSES if (args.weights_dir / weights_filename(a, t)).exists()]
    elif args.arch and args.task:
        pairs = [(args.arch, args.task)]
    else:
        p.error("give --arch and --task, or --all")

    device = _common.get_device(args.device)
    temps = _common.read_temperatures(args.weights_dir)
    for arch, task in pairs:
        temps[f"{arch}_{task}"] = round(calibrate_one(arch, task, args, device), 5)
    out = args.weights_dir / "temperature.json"
    out.write_text(json.dumps(temps, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    np.set_printoptions(precision=4)
    main()
