"""Export real example X-rays for the app from the held-out TEST split.

One child (Kermany) and one adult image per class — Normal, Bacterial, Viral — picked at random
(seeded; never selected by model output) from test images the models never saw in training or
calibration. Written to backend/samples/ with a samples.json manifest; the UI shows the
ground-truth label and source of each.

Adult examples prefer images with an open Creative Commons licence (Cohen et al. metadata);
Shenzhen normals come from the US National Library of Medicine.

Example:
    python export_samples.py
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import _common
import cv2
import pandas as pd

from app.services.preprocessing import load_image, make_display_image
from dataset import load_splits

TITLES = {"NORMAL": "Normal", "BACTERIAL": "Bacterial", "VIRAL": "Viral"}
SOURCE_TEXT = {
    "kermany": "Kermany et al., pediatric (CC BY 4.0)",
    "shenzhen": "Shenzhen No.3 Hospital via US NLM, adult",
    "cohen": "Cohen et al. COVID-19 image data collection, adult",
    "figure1": "Figure1 COVID-19 dataset, adult",
}


def cohen_licences() -> dict[str, str]:
    meta = _common.TRAINING_DIR / "data" / "external" / "covid-chestxray-dataset" / "metadata.csv"
    if not meta.exists():
        return {}
    m = pd.read_csv(meta)
    return {fn: str(lic) for fn, lic in zip(m["filename"], m["license"]) if isinstance(lic, str)}


def pick(rows: pd.DataFrame, seed: int, licences: dict[str, str]) -> pd.Series | None:
    if rows.empty:
        return None
    open_rows = rows[rows["path"].map(lambda p: licences.get(Path(p).name, "").upper().startswith("CC"))]
    pool = open_rows if (rows["source"] == "cohen").all() and not open_rows.empty else rows
    return pool.sample(1, random_state=seed).iloc[0]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--splits", type=Path, default=_common.DEFAULT_SPLITS)
    p.add_argument("--out", type=Path, default=_common.BACKEND_DIR / "samples")
    p.add_argument("--max-side", type=int, default=1024, help="Downscale large images to keep the repo small")
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    test = load_splits(args.splits)["test"]
    if "source" not in test:
        test = test.assign(source="kermany")
    licences = cohen_licences()
    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)

    manifest = []
    for label, title in TITLES.items():
        for group, is_adult in (("child", False), ("adult", True)):
            rows = test[(test["label"] == label) & ((test["source"] != "kermany") == is_adult)]
            row = pick(rows, args.seed, licences)
            if row is None:
                print(f"no {group} {label} test image available — skipped")
                continue
            sid = f"{label.lower()}_{group}"
            gray = make_display_image(load_image(Path(row["path"]).read_bytes(), row["path"]).gray, args.max_side)
            cv2.imwrite(str(args.out / f"{sid}.jpg"), gray, [cv2.IMWRITE_JPEG_QUALITY, 92])
            licence = licences.get(Path(row["path"]).name)
            source = SOURCE_TEXT.get(row["source"], row["source"]) + (f" ({licence})" if licence else "")
            manifest.append(
                {
                    "id": sid,
                    "label": label,
                    "title": f"{title} · {group}",
                    "description": f"Held-out test image. Ground truth: {title}. Source: {source}.",
                    "file": f"{sid}.jpg",
                    "synthetic": False,
                }
            )
    (args.out / "samples.json").write_text(json.dumps(manifest, indent=2))
    print(f"Exported {len(manifest)} test-split samples to {args.out}")


if __name__ == "__main__":
    main()
