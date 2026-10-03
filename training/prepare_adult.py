"""Add adult chest X-rays to the training data (fixes the pediatric-only domain gap).

Sources (all public, no login):
* Cohen et al., COVID-19 image data collection (github.com/ieee8023/covid-chestxray-dataset):
  adult viral (COVID-19, SARS, MERS, influenza, varicella, herpes) and bacterial
  (Streptococcus, Mycoplasma, Klebsiella, Legionella, ...) pneumonia, plus a few normals.
* Figure1 COVID-19 chest X-ray dataset (github.com/agchung/Figure1-COVID-chestxray-dataset).
* Shenzhen No.3 Hospital normals via US NLM (adult normal PA films).
* Actualmed COVID-19 chest X-ray dataset (github.com/agchung/Actualmed-COVID-chestxray-dataset):
  NOT used for training — written to data/external/actualmed.csv as an unseen-hospital test
  (it contains both normal and COVID-19 images from the same site, so a "which source is this"
  shortcut cannot score well on it).

Rules: frontal views only (PA/AP), adults only where age is known, and only findings with a
definite class — unspecified "Pneumonia", fungal, tuberculosis, lipoid, aspiration and "todo"
images are excluded. Each source is split 70/15/15 per label and grouped by patient,
then merged with the existing Kermany split (left unchanged, so results stay comparable).

Usage:
    python prepare_adult.py            # -> data/splits_combined.csv, data/external/actualmed.csv
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
EXT = ROOT / "data" / "external"
FRONTAL = re.compile(r"^(PA|AP)", re.IGNORECASE)


def cohen_label(finding: str) -> str | None:
    f = str(finding)
    if f.startswith("Pneumonia/Viral/"):
        return "VIRAL"
    if f.startswith("Pneumonia/Bacterial"):
        return "BACTERIAL"
    if f == "No Finding":
        return "NORMAL"
    return None


def cohen(root: Path) -> pd.DataFrame:
    m = pd.read_csv(root / "metadata.csv")
    m = m[(m["modality"] == "X-ray") & m["view"].astype(str).str.match(FRONTAL)]
    m = m[m["age"].isna() | (m["age"] >= 18)]
    m = m.assign(label=m["finding"].map(cohen_label)).dropna(subset=["label"])
    paths = [root / folder / fn for folder, fn in zip(m["folder"], m["filename"])]
    return pd.DataFrame(
        {
            "path": [str(p.resolve()) for p in paths],
            "label": m["label"].to_numpy(),
            "patient_id": [f"cohen_{p}" for p in m["patientid"]],
            "source": "cohen",
            "exists": [p.exists() for p in paths],
        }
    )


def _image_for(root: Path, stem: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png"):
        p = root / "images" / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def figure1(root: Path) -> pd.DataFrame:
    m = pd.read_csv(root / "metadata.csv", encoding="latin-1")
    label = m["finding"].map({"COVID-19": "VIRAL", "No finding": "NORMAL"})
    rows = []
    for pid, lab in zip(m["patientid"], label):
        p = _image_for(root, str(pid))
        if isinstance(lab, str) and p is not None:
            rows.append(
                {"path": str(p.resolve()), "label": lab, "patient_id": f"fig1_{re.sub(r'[a-z]$', '', str(pid))}"}
            )
    return pd.DataFrame(rows).assign(source="figure1", exists=True)


def shenzhen(csv: Path) -> pd.DataFrame:
    df = pd.read_csv(csv)
    return pd.DataFrame(
        {
            "path": df["path"],
            "label": "NORMAL",
            "patient_id": [f"shz_{Path(p).stem}" for p in df["path"]],
            "source": "shenzhen",
            "exists": [Path(p).exists() for p in df["path"]],
        }
    )


def actualmed(root: Path) -> pd.DataFrame:
    m = pd.read_csv(root / "metadata.csv", encoding="latin-1")
    m = m.assign(label=m["finding"].map({"COVID-19": "VIRAL", "No finding": "NORMAL"})).dropna(subset=["label"])
    m = m[m["view"].astype(str).str.match(FRONTAL)]
    paths = [root / "images" / n for n in m["imagename"]]
    return pd.DataFrame(
        {
            "path": [str(p.resolve()) for p in paths],
            "label": m["label"].to_numpy(),
            "exists": [p.exists() for p in paths],
        }
    )


def split(df: pd.DataFrame, seed: int, fractions=(0.70, 0.15, 0.15)) -> pd.Series:
    """Patient-grouped 70/15/15 done separately for every label, so even rare classes
    (e.g. ~50 adult bacterial images) get a proportional test share.

    Patients are shuffled and assigned whole to the split that is furthest below its target
    image count, which keeps image proportions close to 70/15/15 without splitting a patient.
    """
    names = ("train", "val", "test")
    out = pd.Series("", index=df.index)
    # One label per patient (its most frequent finding) so a patient never spans splits.
    patient_label = df.groupby("patient_id")["label"].agg(lambda s: s.value_counts().index[0])
    for i, (_, patients) in enumerate(patient_label.groupby(patient_label)):
        pids = patients.index.to_numpy().copy()
        np.random.default_rng(seed + i).shuffle(pids)
        sizes = df["patient_id"].value_counts()
        total = int(sizes[pids].sum())
        filled = dict.fromkeys(names, 0)
        for pid in pids:
            target = min(names, key=lambda n: filled[n] / total - fractions[names.index(n)])
            out[df["patient_id"] == pid] = target
            filled[target] += int(sizes[pid])
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--kermany-splits", type=Path, default=ROOT / "data" / "splits.csv")
    p.add_argument("--out", type=Path, default=ROOT / "data" / "splits_combined.csv")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    adult = pd.concat(
        [
            cohen(EXT / "covid-chestxray-dataset"),
            figure1(EXT / "Figure1-COVID-chestxray-dataset"),
            shenzhen(EXT / "shenzhen_normal.csv"),
        ],
        ignore_index=True,
    )
    missing = int((~adult["exists"]).sum())
    adult = adult[adult["exists"]].drop(columns="exists").drop_duplicates("path").reset_index(drop=True)
    parts = []
    for source, df in adult.groupby("source"):
        df = df.copy()
        df["split"] = split(df, args.seed)
        parts.append(df)
    adult = pd.concat(parts, ignore_index=True)
    assert (adult.groupby("patient_id")["split"].nunique() == 1).all(), "patient leakage"

    kermany = pd.read_csv(args.kermany_splits).assign(source="kermany")
    combined = pd.concat([kermany, adult], ignore_index=True)
    combined.to_csv(args.out, index=False)

    ext = actualmed(EXT / "Actualmed-COVID-chestxray-dataset")
    ext = ext[ext["exists"]].drop(columns="exists")
    ext.assign(label=(ext["label"] != "NORMAL").astype(int)).to_csv(EXT / "actualmed.csv", index=False)

    print(f"Adult images added: {len(adult)} ({missing} listed in metadata but missing on disk)")
    print(pd.crosstab([adult["source"], adult["split"]], adult["label"]).to_string())
    print(f"\nCombined: {len(combined)} images -> {args.out}")
    print(pd.crosstab(combined["split"], combined["label"], margins=True).to_string())
    print(f"\nExternal test (Actualmed, never trained on): {len(ext)} images {ext['label'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
