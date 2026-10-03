"""Train DenseNet121 or Swin-Tiny for Stage 1, Stage 2 or the 3-class task.

Both architectures use IDENTICAL settings by default (for a fair comparison):
ImageNet-pretrained weights, AdamW, lr 1e-4, weight decay 1e-4, batch 32, 25 epochs,
1 warm-up epoch then cosine decay, class-weighted cross-entropy, mixed precision on CUDA,
early stopping on validation ROC-AUC (patience 6).

Outputs:
    backend/weights/<arch>_<task>.pth    best state_dict
    backend/weights/<arch>_<task>.json   preprocessing + training metadata (read by the API)
    training/outputs/history_<arch>_<task>.json
    backend/metrics/metrics.json         training_curves.<arch>.<task> updated

Examples:
    python train.py --arch densenet --task stage1
    python train.py --arch swin --task stage2 --epochs 30
    python train.py --arch densenet --task three_class
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict
from pathlib import Path

import _common
import numpy as np
import torch
from sklearn.metrics import roc_auc_score
from torch import nn
from torch.utils.data import DataLoader, WeightedRandomSampler

from app.models.architectures import (
    ARCHS,
    TASK_CLASSES,
    build_model,
    metadata_filename,
    weights_filename,
)
from app.services.evaluation import update_metrics_file
from app.services.preprocessing import PreprocessConfig
from dataset import AugmentConfig, CXRDataset, load_splits


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--arch", choices=list(ARCHS), required=True)
    p.add_argument("--task", choices=list(TASK_CLASSES), required=True)
    p.add_argument("--splits", type=Path, default=_common.DEFAULT_SPLITS)
    p.add_argument("--weights-dir", type=Path, default=_common.DEFAULT_WEIGHTS)
    p.add_argument("--metrics-path", type=Path, default=_common.DEFAULT_METRICS)
    p.add_argument("--epochs", type=int, default=25)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--weight-decay", type=float, default=1e-4)
    p.add_argument("--warmup-epochs", type=float, default=1.0)
    p.add_argument("--patience", type=int, default=6)
    p.add_argument("--image-size", type=int, default=224)
    p.add_argument(
        "--no-clahe",
        action="store_true",
        help="Disable CLAHE (must match at inference — recorded in the .json)",
    )
    p.add_argument(
        "--hflip",
        action="store_true",
        help="Enable horizontal flip augmentation (off by default)",
    )
    p.add_argument(
        "--adult-fraction",
        type=float,
        default=0.3,
        help="Share of adult images per epoch when the split mixes sources (0 = plain shuffling)",
    )
    p.add_argument("--no-pretrained", action="store_true", help="Random init (smoke tests only)")
    p.add_argument("--no-class-weights", action="store_true")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--log-every", type=int, default=25, help="Print running train metrics every N steps (0 = off)")
    p.add_argument("--cache", action="store_true", help="Cache preprocessed images on disk (much faster on CPU/MPS)")
    p.add_argument("--device", default="auto")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Use at most N images per split (debugging)",
    )
    return p.parse_args()


def domain_sampler(df, adult_fraction: float, seed: int):
    """Oversample the (much smaller) adult domain so each epoch is ~``adult_fraction`` adult.

    Returns None when the split has no ``source`` column or only one domain.
    """
    if adult_fraction <= 0 or "source" not in df:
        return None
    adult = (df["source"] != "kermany").to_numpy()
    n_adult, n_child = int(adult.sum()), int((~adult).sum())
    if n_adult == 0 or n_child == 0:
        return None
    weights = np.where(adult, adult_fraction / n_adult, (1 - adult_fraction) / n_child)
    print(f"domain-balanced sampling: {n_adult} adult / {n_child} pediatric images, target {adult_fraction:.0%} adult")
    generator = torch.Generator().manual_seed(seed)
    return WeightedRandomSampler(
        torch.as_tensor(weights, dtype=torch.double), len(df), replacement=True, generator=generator
    )


def make_scheduler(optimizer, steps_per_epoch: int, epochs: int, warmup_epochs: float):
    total = max(1, steps_per_epoch * epochs)
    warmup = int(steps_per_epoch * warmup_epochs)

    def lr_lambda(step: int) -> float:
        if step < warmup:
            return (step + 1) / max(1, warmup)
        progress = (step - warmup) / max(1, total - warmup)
        return 0.5 * (1 + math.cos(math.pi * min(1.0, progress)))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


def evaluate(model, loader, device, criterion) -> dict[str, float]:
    logits, labels = _common.collect_logits(model, loader, device)
    probs = torch.softmax(torch.from_numpy(logits), dim=1).numpy()
    loss = float(
        criterion(
            torch.from_numpy(logits).to(device),
            torch.from_numpy(labels).long().to(device),
        ).item()
    )
    acc = float((probs.argmax(1) == labels).mean())
    try:
        auc = (
            roc_auc_score(labels, probs[:, 1])
            if probs.shape[1] == 2
            else roc_auc_score(labels, probs, multi_class="ovr", average="macro")
        )
    except ValueError:
        auc = float("nan")
    return {"loss": loss, "acc": acc, "auc": float(auc)}


def main() -> None:
    args = parse_args()
    _common.seed_everything(args.seed)
    device = _common.get_device(args.device)
    use_amp = device.type == "cuda"
    preprocess = PreprocessConfig(image_size=args.image_size, use_clahe=not args.no_clahe)

    splits = load_splits(args.splits)
    if args.limit:
        splits = {k: v.sample(min(args.limit, len(v)), random_state=args.seed) for k, v in splits.items()}
    train_ds = CXRDataset(
        splits["train"], args.task, preprocess, AugmentConfig(hflip=args.hflip), seed=args.seed, cache=args.cache
    )
    val_ds = CXRDataset(splits["val"], args.task, preprocess, cache=args.cache)
    loader_kw = dict(batch_size=args.batch_size, num_workers=args.workers, pin_memory=use_amp)
    sampler = domain_sampler(train_ds.df, args.adult_fraction, args.seed)
    train_loader = DataLoader(
        train_ds,
        shuffle=sampler is None,
        sampler=sampler,
        drop_last=len(train_ds) > args.batch_size,
        **loader_kw,
    )
    val_loader = DataLoader(val_ds, shuffle=False, **loader_kw)

    counts = train_ds.class_counts()
    print(
        f"{args.arch} {args.task} | device={device} | train={len(train_ds)} val={len(val_ds)} | counts={counts.tolist()}"
    )
    weights = None
    if not args.no_class_weights:
        weights = torch.tensor(
            counts.sum() / (len(counts) * np.maximum(counts, 1)),
            dtype=torch.float32,
            device=device,
        )
        print("class weights:", [round(w, 3) for w in weights.tolist()])
    criterion = nn.CrossEntropyLoss(weight=weights)

    model = build_model(args.arch, len(TASK_CLASSES[args.task]), pretrained=not args.no_pretrained).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = make_scheduler(optimizer, len(train_loader), args.epochs, args.warmup_epochs)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    args.weights_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.weights_dir / weights_filename(args.arch, args.task)
    history: list[dict] = []
    best_auc, best_epoch, bad_epochs = -1.0, 0, 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        t0, run_loss, run_correct, seen, skipped, step = time.time(), 0.0, 0, 0, 0, 0
        for x, y in train_loader:
            x, y = _common.to_device(x, device), _common.to_device(y, device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=use_amp):
                out = model(x)
                loss = criterion(out, y)
            if not torch.isfinite(loss):
                # Rare non-finite batches (seen with some kernels on Apple MPS): skip the update.
                skipped += 1
                scheduler.step()
                continue
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            grad_norm = nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            if not torch.isfinite(grad_norm):
                skipped += 1
                optimizer.zero_grad(set_to_none=True)
                scheduler.step()
                continue
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            run_loss += loss.item() * len(y)
            run_correct += (out.argmax(1) == y).sum().item()
            seen += len(y)
            step += 1
            if args.log_every and step % args.log_every == 0:
                print(
                    f"    step {step:4d} | running loss {run_loss / seen:.4f} acc {run_correct / seen:.3f} | "
                    f"batch loss {loss.item():.4f} | lr {optimizer.param_groups[0]['lr']:.2e}"
                )

        val = evaluate(model, val_loader, device, criterion)
        log = {
            "epoch": epoch,
            "train_loss": round(run_loss / max(seen, 1), 5),
            "val_loss": round(val["loss"], 5),
            "train_acc": round(run_correct / max(seen, 1), 5),
            "val_acc": round(val["acc"], 5),
            "val_auc": round(val["auc"], 5),
            "lr": optimizer.param_groups[0]["lr"],
            "skipped_batches": skipped,
        }
        history.append(log)
        print(
            f"epoch {epoch:3d} | train loss {log['train_loss']:.4f} acc {log['train_acc']:.3f} | "
            f"val loss {log['val_loss']:.4f} acc {log['val_acc']:.3f} auc {log['val_auc']:.4f} | {time.time() - t0:.0f}s"
            + (f" | skipped {skipped} non-finite batches" if skipped else "")
        )

        score = val["auc"] if not math.isnan(val["auc"]) else val["acc"]
        if score > best_auc:
            best_auc, best_epoch, bad_epochs = score, epoch, 0
            torch.save(model.state_dict(), out_path)
        else:
            bad_epochs += 1
            if bad_epochs >= args.patience:
                print(f"Early stopping at epoch {epoch} (best epoch {best_epoch}, val AUC {best_auc:.4f})")
                break

    meta = {
        "arch": args.arch,
        "timm_name": ARCHS[args.arch].timm_name,
        "task": args.task,
        "classes": TASK_CLASSES[args.task],
        "preprocess": preprocess.to_dict(),
        "augment": asdict(AugmentConfig(hflip=args.hflip)),
        "best_epoch": best_epoch,
        "best_val_auc": round(best_auc, 5),
        "hyperparameters": {k: v for k, v in vars(args).items() if not isinstance(v, Path)},
    }
    (args.weights_dir / metadata_filename(args.arch, args.task)).write_text(json.dumps(meta, indent=2))
    _common.OUTPUTS.mkdir(parents=True, exist_ok=True)
    (_common.OUTPUTS / f"history_{args.arch}_{args.task}.json").write_text(json.dumps(history, indent=1))

    def put_curves(data: dict) -> None:
        data.setdefault("training_curves", {}).setdefault(args.arch, {})[args.task] = history

    update_metrics_file(args.metrics_path, put_curves)
    print(f"Saved best weights (epoch {best_epoch}) to {out_path}")


if __name__ == "__main__":
    main()
