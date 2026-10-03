"""PyTorch datasets for the CXR tasks.

Images are decoded and preprocessed with the backend's own functions
(``load_image`` -> ``prepare_uint8`` -> augmentation -> ``to_model_tensor``), so training
matches inference exactly. Augmentation is applied to the resized uint8 image:

* small rotation (±7°), slight zoom (0.92–1.08) and translation (±4%);
* brightness / contrast jitter (±10%);
* NO horizontal flip by default — cardiac position (situs) and laterality matter.
"""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import _common  # noqa: F401  (adds backend/ to sys.path)
import cv2
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from app.models.architectures import TASK_CLASSES
from app.services.preprocessing import (
    PreprocessConfig,
    load_image,
    prepare_uint8,
    to_model_tensor,
)

CACHE_DIR = Path(__file__).resolve().parent / "data" / "cache"


def preprocess_cached(paths: list[str], preprocess: PreprocessConfig, workers: int = 8) -> dict[str, np.ndarray]:
    """Decode + ``prepare_uint8`` every path once and keep the result on disk.

    The cache key covers the preprocessing config, so changing CLAHE / size rebuilds it.
    Augmentation is still applied fresh to the cached image every epoch.
    """
    key = hashlib.sha1(json.dumps(preprocess.to_dict(), sort_keys=True).encode()).hexdigest()[:10]
    store_path = CACHE_DIR / f"images_{key}.npz"
    store: dict[str, np.ndarray] = {}
    if store_path.exists():
        with np.load(store_path) as f:
            store = dict(zip(json.loads(str(f["paths"])), f["images"]))
    missing = [p for p in dict.fromkeys(paths) if p not in store]
    if missing:

        def work(path: str) -> np.ndarray:
            return prepare_uint8(load_image(Path(path).read_bytes(), path).gray, preprocess)

        with ThreadPoolExecutor(workers) as pool:
            for path, img in zip(missing, pool.map(work, missing)):
                store[path] = img
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        keys = list(store)
        np.savez(store_path, paths=json.dumps(keys), images=np.stack([store[k] for k in keys]))
    return {p: store[p] for p in paths}


TASK_LABEL_MAP: dict[str, dict[str, int]] = {
    "stage1": {"NORMAL": 0, "BACTERIAL": 1, "VIRAL": 1},
    "stage2": {"BACTERIAL": 0, "VIRAL": 1},
    "three_class": {"NORMAL": 0, "BACTERIAL": 1, "VIRAL": 2},
}


@dataclass
class AugmentConfig:
    rotation_deg: float = 7.0
    zoom: tuple[float, float] = (0.92, 1.08)
    translate: float = 0.04
    brightness: float = 0.10
    contrast: float = 0.10
    hflip: bool = False


def augment(img: np.ndarray, cfg: AugmentConfig, rng: np.random.Generator) -> np.ndarray:
    h, w = img.shape
    angle = rng.uniform(-cfg.rotation_deg, cfg.rotation_deg)
    scale = rng.uniform(*cfg.zoom)
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
    m[:, 2] += rng.uniform(-cfg.translate, cfg.translate, size=2) * (w, h)
    out = cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    # Contrast around the image mean, then a brightness shift; clip (NOT abs) to the uint8 range.
    alpha = 1 + rng.uniform(-cfg.contrast, cfg.contrast)
    beta = 255 * rng.uniform(-cfg.brightness, cfg.brightness)
    mean = float(out.mean())
    out = np.clip((out.astype(np.float32) - mean) * alpha + mean + beta, 0, 255).astype(np.uint8)
    if cfg.hflip and rng.random() < 0.5:
        out = out[:, ::-1].copy()
    return out


def task_frame(df: pd.DataFrame, task: str) -> pd.DataFrame:
    """Filter a split frame to the rows relevant for ``task`` (Stage 2 = pneumonia only)."""
    keep = df["label"].isin(TASK_LABEL_MAP[task].keys())
    return df[keep].reset_index(drop=True)


class CXRDataset(Dataset):
    def __init__(
        self,
        df: pd.DataFrame,
        task: str,
        preprocess: PreprocessConfig = PreprocessConfig(),
        augment_cfg: AugmentConfig | None = None,
        seed: int = 0,
        cache: bool = False,
    ) -> None:
        self.df = task_frame(df, task)
        self.task = task
        self.preprocess = preprocess
        self.augment_cfg = augment_cfg
        self.labels = self.df["label"].map(TASK_LABEL_MAP[task]).to_numpy()
        self.seed = seed
        self._cache = preprocess_cached(self.df["path"].tolist(), preprocess) if cache else None

    @property
    def classes(self) -> list[str]:
        return TASK_CLASSES[self.task]

    def class_counts(self) -> np.ndarray:
        return np.bincount(self.labels, minlength=len(self.classes))

    def __len__(self) -> int:
        return len(self.df)

    def load_uint8(self, idx: int) -> np.ndarray:
        if self._cache is not None:
            return self._cache[self.df.loc[idx, "path"]]
        gray = load_image(Path(self.df.loc[idx, "path"]).read_bytes(), self.df.loc[idx, "path"]).gray
        return prepare_uint8(gray, self.preprocess)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        img = self.load_uint8(idx)
        if self.augment_cfg is not None:
            rng = np.random.default_rng((self.seed, idx, torch.randint(0, 2**31 - 1, (1,)).item()))
            img = augment(img, self.augment_cfg, rng)
        return to_model_tensor(img), int(self.labels[idx])


def load_splits(path: Path) -> dict[str, pd.DataFrame]:
    df = pd.read_csv(path)
    return {s: df[df["split"] == s].reset_index(drop=True) for s in ("train", "val", "test")}
