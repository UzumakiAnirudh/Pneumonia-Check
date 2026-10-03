"""Build a fresh, patient-grouped 70/15/15 split of the Kermany pediatric CXR dataset.

Labels come from the folder (NORMAL / PNEUMONIA) and, for pneumonia, the filename
(``person1_bacteria_1.jpeg`` -> BACTERIAL, ``person1_virus_6.jpeg`` -> VIRAL).

Patient IDs:
* pneumonia: ``personN``;
* normal:    ``IM-XXXX`` / ``NORMAL2-IM-XXXX`` -> the ``XXXX`` number (grouped conservatively,
  ignoring the NORMAL2 prefix — over-grouping can never cause leakage).

The original train/val/test folders are pooled and re-split; the 16-image Kaggle ``val``
folder is NOT used as a validation set. Exact duplicate files (e.g. the nested copy in the
Kaggle zip) are removed by content hash. The split is stratified by label *and* grouped by
patient using StratifiedGroupKFold (20 folds -> 14 train / 3 val / 3 test).

Usage:
    python prepare_data.py --data-root /path/to/chest_xray --out data/splits.csv
"""

from __future__ import annotations

import argparse
import hashlib
import re
from collections import Counter
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

IMAGE_EXTS = {".jpeg", ".jpg", ".png"}
PNEUMONIA_RE = re.compile(r"(person\d+)_(bacteria|virus)", re.IGNORECASE)
NORMAL_RE = re.compile(r"IM-(\d+)", re.IGNORECASE)


def parse_label(path: Path) -> tuple[str, str] | None:
    """Return (label, patient_id) for a Kermany image path, or None if unrecognised."""
    folder = path.parent.name.upper()
    name = path.name
    if folder == "PNEUMONIA":
        m = PNEUMONIA_RE.search(name)
        if not m:
            return None
        return ("BACTERIAL" if m.group(2).lower() == "bacteria" else "VIRAL"), f"p_{m.group(1).lower()}"
    if folder == "NORMAL":
        m = NORMAL_RE.search(name)
        return ("NORMAL", f"n_{int(m.group(1))}") if m else ("NORMAL", f"n_{path.stem}")
    return None


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def collect(data_root: Path) -> pd.DataFrame:
    rows, seen = [], set()
    for path in sorted(data_root.rglob("*")):
        if path.suffix.lower() not in IMAGE_EXTS or "__MACOSX" in path.parts:
            continue
        parsed = parse_label(path)
        if parsed is None:
            continue
        digest = md5(path)
        if digest in seen:
            continue
        seen.add(digest)
        rows.append({"path": str(path.resolve()), "label": parsed[0], "patient_id": parsed[1]})
    if not rows:
        raise SystemExit(f"No Kermany images found under {data_root}")
    return pd.DataFrame(rows)


def split(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    sgkf = StratifiedGroupKFold(n_splits=20, shuffle=True, random_state=seed)
    fold = pd.Series(-1, index=df.index)
    for i, (_, idx) in enumerate(sgkf.split(df, df["label"], groups=df["patient_id"])):
        fold.iloc[idx] = i
    df = df.copy()
    df["split"] = fold.map(lambda f: "train" if f < 14 else "val" if f < 17 else "test")
    # Sanity: no patient in more than one split.
    leaks = df.groupby("patient_id")["split"].nunique()
    assert (leaks == 1).all(), "patient leakage between splits"
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--data-root",
        type=Path,
        required=True,
        help="Folder containing the Kermany images",
    )
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "data" / "splits.csv")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = split(collect(args.data_root), args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)

    print(f"Wrote {len(df)} images ({df['patient_id'].nunique()} patients) to {args.out}")
    table = pd.crosstab(df["split"], df["label"], margins=True)
    print(table.to_string())
    for s in ("train", "val", "test"):
        print(
            f"{s:5s}: {len(df[df.split == s]) / len(df):.1%}",
            dict(Counter(df[df.split == s]["label"])),
        )


if __name__ == "__main__":
    main()
