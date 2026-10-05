"""Download every dataset used by PneumoScan AI from its original public source.

Nothing here needs an account or API key. Already-downloaded parts are skipped, so it is safe to
re-run after an interruption.

What gets downloaded (into training/data/):

  kermany   Kermany et al. "Chest X-Ray Images (Pneumonia)", Mendeley Data v2 (CC BY 4.0)
            ~1.2 GB zip -> data/raw/chest_xray/{train,test}/{NORMAL,PNEUMONIA}/*.jpeg
  cohen     Cohen et al. COVID-19 image data collection (GitHub)            -> data/external/covid-chestxray-dataset
  figure1   Figure1 COVID-19 chest X-ray dataset (GitHub)                    -> data/external/Figure1-COVID-chestxray-dataset
  actualmed Actualmed COVID-19 chest X-ray dataset (GitHub, ~1.6 GB)         -> data/external/Actualmed-COVID-chestxray-dataset
  shenzhen  326 normal adult chest X-rays, Shenzhen No.3 Hospital via US NLM -> data/external/shenzhen_normal/*.png (+ .csv)

The four adult sources are only needed for the adult experiments (prepare_adult.py).

Examples:
    python download_data.py                 # everything (~5 GB)
    python download_data.py kermany         # only what the main models need
    python download_data.py --dry-run       # show what would happen
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
EXTERNAL = DATA / "external"

KERMANY_URL = (
    "https://data.mendeley.com/public-files/datasets/rscbjbr9sj/files/"
    "f12eaf6d-6023-432f-acc9-80c9d7393433/file_downloaded"
)
GITHUB_REPOS = {
    "cohen": "https://github.com/ieee8023/covid-chestxray-dataset.git",
    "figure1": "https://github.com/agchung/Figure1-COVID-chestxray-dataset.git",
    "actualmed": "https://github.com/agchung/Actualmed-COVID-chestxray-dataset.git",
}
SHENZHEN_BASE = (
    "https://data.lhncbc.nlm.nih.gov/public/Tuberculosis-Chest-X-ray-Datasets/Shenzhen-Hospital-CXR-Set/CXR_png/"
)


def download(url: str, dest: Path) -> None:
    """Stream a URL to a file, printing progress for large downloads."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            if total > 50_000_000:
                print(f"\r  {done / 1e6:,.0f} / {total / 1e6:,.0f} MB", end="", flush=True)
    if total > 50_000_000:
        print()
    tmp.replace(dest)


def kermany(dry: bool) -> None:
    target = DATA / "raw" / "chest_xray"
    if target.exists() and any(target.rglob("*.jpeg")):
        print(f"kermany: already present in {target}")
        return
    zip_path = DATA / "ChestXRay2017.zip"
    print(f"kermany: download {KERMANY_URL} (~1.2 GB) and unzip to {DATA / 'raw'}")
    if dry:
        return
    DATA.mkdir(parents=True, exist_ok=True)
    if not zip_path.exists():
        download(KERMANY_URL, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(DATA / "raw")
    n = sum(1 for p in target.rglob("*.jpeg") if "__MACOSX" not in p.parts)
    print(f"kermany: {n} images extracted")


def clone(name: str, dry: bool) -> None:
    url = GITHUB_REPOS[name]
    dest = EXTERNAL / Path(url).stem
    if dest.exists():
        print(f"{name}: already present in {dest}")
        return
    print(f"{name}: git clone --depth 1 {url}")
    if dry:
        return
    if shutil.which("git") is None:
        sys.exit("git is not installed — see docs/guide/01-computer-basics.md")
    EXTERNAL.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", url, str(dest)], check=True)


def shenzhen(dry: bool) -> None:
    folder = EXTERNAL / "shenzhen_normal"
    with urllib.request.urlopen(SHENZHEN_BASE + "index.html") as r:
        names = sorted(set(re.findall(r"CHNCXR_\d+_0\.png", r.read().decode("utf-8", "ignore"))))  # _0 = normal
    missing = [n for n in names if not (folder / n).exists()]
    print(f"shenzhen: {len(names)} normal images listed, {len(missing)} to download")
    if dry or not names:
        return
    folder.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda n: download(SHENZHEN_BASE + n, folder / n), missing))
    with open(EXTERNAL / "shenzhen_normal.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "label"])
        for n in names:
            w.writerow([str((folder / n).resolve()), 0])
    print(f"shenzhen: done -> {EXTERNAL / 'shenzhen_normal.csv'}")


def main() -> None:
    parts = ["kermany", "cohen", "figure1", "actualmed", "shenzhen"]
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("parts", nargs="*", help=f"Which datasets: {', '.join(parts)} (default: all)")
    p.add_argument("--dry-run", action="store_true", help="Only print what would be downloaded")
    args = p.parse_args()
    unknown = set(args.parts) - set(parts)
    if unknown:
        p.error(f"unknown dataset(s): {', '.join(sorted(unknown))}; choose from {', '.join(parts)}")
    for part in args.parts or parts:
        if part == "kermany":
            kermany(args.dry_run)
        elif part == "shenzhen":
            shenzhen(args.dry_run)
        else:
            clone(part, args.dry_run)
    print("Done. Next: python prepare_data.py --data-root data/raw/chest_xray")


if __name__ == "__main__":
    main()
