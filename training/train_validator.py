"""Train the input validator: chest X-ray vs anything else (MobileNetV3-Small).

Data layout (ImageFolder):
    data/validator/
        cxr/     frontal chest X-rays (e.g. a sample of Kermany train images, RSNA, NIH)
        other/   natural photos, documents/screenshots, other X-ray body parts (MURA), CT slices...

Class 0 must be ``cxr`` (the API reads P(class 0) as the CXR probability); folders are
sorted alphabetically so ``cxr`` < ``other`` satisfies this.

Colour is kept (validator_tensor) because colour photos are an important negative class.
Saves backend/weights/validator.pth. The API then uses it instead of the heuristic.

Example:
    python train_validator.py --data data/validator --epochs 8
"""

from __future__ import annotations

import argparse
from pathlib import Path

import _common
import numpy as np
import torch
from sklearn.metrics import classification_report
from torch import nn
from torch.utils.data import DataLoader, Dataset, random_split

from app.services.preprocessing import load_image, validator_tensor

EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".dcm"}


class FolderDataset(Dataset):
    def __init__(self, root: Path, augment: bool = False) -> None:
        self.items = []
        self.classes = sorted(d.name for d in root.iterdir() if d.is_dir())
        if self.classes[:1] != ["cxr"]:
            raise SystemExit(f"Expected class folders 'cxr' and 'other' in {root}, found {self.classes}")
        for ci, c in enumerate(self.classes):
            self.items += [(p, ci) for p in sorted((root / c).rglob("*")) if p.suffix.lower() in EXTS]
        self.augment = augment

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, i: int):
        path, label = self.items[i]
        try:
            rgb = load_image(path.read_bytes(), path.name).rgb
        except Exception:
            rgb = np.zeros((224, 224, 3), np.uint8)
        x = validator_tensor(rgb)[0]
        if self.augment:
            if torch.rand(1) < 0.5:
                x = torch.flip(x, dims=[2])  # orientation is irrelevant for "is this a CXR?"
            x = x * (1 + 0.1 * torch.randn(1)) + 0.1 * torch.randn(1)
        return x, label


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", type=Path, default=_common.TRAINING_DIR / "data" / "validator")
    p.add_argument("--weights-dir", type=Path, default=_common.DEFAULT_WEIGHTS)
    p.add_argument("--epochs", type=int, default=8)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--val-fraction", type=float, default=0.15)
    p.add_argument("--no-pretrained", action="store_true")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--device", default="auto")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    import timm

    _common.seed_everything(args.seed)
    device = _common.get_device(args.device)
    full = FolderDataset(args.data, augment=True)
    n_val = max(1, int(len(full) * args.val_fraction))
    train_ds, val_ds = random_split(
        full,
        [len(full) - n_val, n_val],
        generator=torch.Generator().manual_seed(args.seed),
    )
    counts = np.bincount([full.items[i][1] for i in train_ds.indices], minlength=2)
    print(f"classes={full.classes} train={len(train_ds)} val={len(val_ds)} counts={counts.tolist()}")

    model = timm.create_model("mobilenetv3_small_100", pretrained=not args.no_pretrained, num_classes=2).to(device)
    weights = torch.tensor(counts.sum() / (2 * np.maximum(counts, 1)), dtype=torch.float32, device=device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    loader_kw = dict(batch_size=args.batch_size, num_workers=args.workers)
    train_loader = DataLoader(train_ds, shuffle=True, **loader_kw)
    val_loader = DataLoader(val_ds, shuffle=False, **loader_kw)

    best = -1.0
    out = args.weights_dir / "validator.pth"
    args.weights_dir.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()
        scheduler.step()
        logits, labels = _common.collect_logits(model, val_loader, device)
        acc = float((logits.argmax(1) == labels).mean())
        print(f"epoch {epoch}: val acc {acc:.4f}")
        if acc > best:
            best = acc
            torch.save(model.state_dict(), out)
    logits, labels = _common.collect_logits(model, val_loader, device)
    print(
        classification_report(
            labels,
            logits.argmax(1),
            target_names=full.classes,
            digits=4,
            zero_division=0,
        )
    )
    print(f"Saved {out} (best val acc {best:.4f})")


if __name__ == "__main__":
    main()
