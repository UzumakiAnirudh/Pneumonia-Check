"""MockModelProvider — realistic simulated predictions without trained weights.

Outputs are *derived from the image* rather than random, so demos behave sensibly:
* "severity" — how much brighter (more opaque) the brightest lung regions are compared to the
  typical lung field -> drives Normal vs Pneumonia;
* "diffuseness" — whether the opacity is spread bilaterally (viral-like) or focal (bacterial-like)
  -> drives Bacterial vs Viral;
* the opacity map itself becomes the heatmap.

A deterministic per-image/per-architecture jitter makes the two architectures differ slightly.
This is NOT a diagnostic model.
"""

from __future__ import annotations

import hashlib
import time

import cv2
import numpy as np

from app.models.specs import ARCHS, TASK_CLASSES
from app.models.provider import InferenceOutput, ModelInfo, ModelProvider
from app.services.lung_mask import template_mask
from app.services.preprocessing import PreprocessConfig, prepare_uint8


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


class MockModelProvider(ModelProvider):
    is_mock = True

    def __init__(self, preprocess: PreprocessConfig | None = None, latency_ms: int = 0) -> None:
        self.cfg = preprocess or PreprocessConfig()
        self.latency_ms = latency_ms
        size = self.cfg.image_size
        self._lungs = template_mask(size)
        # Inner lung "cores", excluding the cardiac silhouette, for opacity statistics.
        core = np.zeros((size, size), np.uint8)
        for cx, cy, ax, ay in ((0.31, 0.50, 0.12, 0.27), (0.69, 0.49, 0.11, 0.25)):
            cv2.ellipse(
                core,
                (round(cx * size), round(cy * size)),
                (round(ax * size), round(ay * size)),
                0,
                0,
                360,
                1,
                -1,
            )
        core[int(0.58 * size) :, int(0.5 * size) : int(0.72 * size)] = 0
        self._core = core.astype(bool)
        # Soft cardiac silhouette: the heart border is bright but is not lung opacity.
        heart = np.zeros((size, size), np.float32)
        cv2.ellipse(
            heart,
            (round(0.58 * size), round(0.66 * size)),
            (round(0.15 * size), round(0.13 * size)),
            -25,
            0,
            360,
            1,
            -1,
        )
        self._not_heart = 1.0 - cv2.GaussianBlur(heart, (0, 0), sigmaX=size / 40)

    def available(self, arch: str, task: str) -> bool:
        return arch in ARCHS and task in TASK_CLASSES

    def status(self, tasks: list[str]) -> list[ModelInfo]:
        return [ModelInfo(key=k, name=s.display_name, ready=True) for k, s in ARCHS.items()]

    # ------------------------------------------------------------------ analysis

    def _analyse(self, img: np.ndarray) -> tuple[np.ndarray, float, float]:
        """Return (opacity map in [0, 1], severity, diffuseness).

        severity    = fraction of the lung cores that is markedly brighter than aerated lung
        diffuseness = left/right balance of that opacity (bilateral -> viral-like)
        """
        size = img.shape[0]
        blurred = cv2.GaussianBlur(img.astype(np.float32), (0, 0), sigmaX=size / 45)
        core = self._core
        baseline = float(np.percentile(blurred[core], 15))
        mediastinum = float(blurred[size // 4 : 3 * size // 4, int(size * 0.46) : int(size * 0.54)].mean())
        span = max(mediastinum - baseline, 20.0)
        opacity = np.clip((blurred - baseline) / span, 0, 1)

        active = (opacity > 0.35) & core
        severity = float(active[core].mean())
        half = size // 2
        left, right = float(active[:, :half].sum()), float(active[:, half:].sum())
        diffuseness = min(left, right) / (max(left, right) + 1e-6)
        return opacity * self._lungs * self._not_heart, severity, diffuseness

    @staticmethod
    def _rng(img: np.ndarray, arch: str, task: str) -> np.random.Generator:
        digest = hashlib.sha1(img.tobytes() + arch.encode() + task.encode()).digest()
        return np.random.default_rng(int.from_bytes(digest[:8], "little"))

    def _cam(self, opacity: np.ndarray, arch: str, predicted: str, rng: np.random.Generator) -> np.ndarray:
        size = opacity.shape[0]
        yy, xx = np.mgrid[0:size, 0:size] / size
        if predicted in ("NORMAL",):
            # Broad attention over both (clear) lung fields when nothing abnormal is found.
            fields = cv2.GaussianBlur(self._lungs.astype(np.float32), (0, 0), sigmaX=size / 16)
            hilar = np.exp(-(((np.abs(xx - 0.5) - 0.14) / 0.1) ** 2 + ((yy - 0.47) / 0.16) ** 2))
            cam = 0.55 * fields + 0.3 * hilar + 0.15 * opacity
        else:
            cam = opacity.copy()
        # Swin attention is typically blockier/more diffuse; DenseNet more focal.
        sigma = size / (14 if arch == "swin" else 22)
        cam = cv2.GaussianBlur(cam.astype(np.float32), (0, 0), sigmaX=sigma)
        if arch == "swin":
            coarse = cv2.resize(cam, (7, 7), interpolation=cv2.INTER_AREA)
            cam = 0.6 * cam + 0.4 * cv2.resize(coarse, (size, size), interpolation=cv2.INTER_CUBIC)
        shift = rng.integers(-4, 5, size=2)
        cam = np.roll(cam, tuple(int(s) for s in shift), axis=(0, 1))
        cam = np.clip(cam, 0, None)
        return cam / (cam.max() + 1e-8)

    # ------------------------------------------------------------------ inference

    def infer(self, arch: str, task: str, gray: np.ndarray, explain: bool = False) -> InferenceOutput:
        start = time.perf_counter()
        img = prepare_uint8(gray, self.cfg)
        opacity, severity, diffuseness = self._analyse(img)
        rng = self._rng(img, arch, task)
        jitter = rng.normal(0, 0.35 if arch == "swin" else 0.25)

        p_pneu = _sigmoid(45.0 * (severity - 0.20) + jitter)
        p_pneu = float(np.clip(p_pneu, 0.02, 0.965 + 0.03 * rng.random()))
        p_viral = _sigmoid(10.0 * (diffuseness - 0.5) + rng.normal(0, 0.4))
        p_viral = float(np.clip(p_viral, 0.04, 0.96))

        if task == "stage1":
            probs = np.array([1 - p_pneu, p_pneu])
        elif task == "stage2":
            probs = np.array([1 - p_viral, p_viral])
        else:
            probs = np.array([1 - p_pneu, p_pneu * (1 - p_viral), p_pneu * p_viral])
        logits = np.log(np.clip(probs, 1e-6, None)).astype(np.float32)

        cam = None
        if explain:
            predicted = TASK_CLASSES[task][int(np.argmax(logits))]
            cam = self._cam(opacity, arch, predicted, rng)

        if self.latency_ms:
            time.sleep(self.latency_ms / 1000 * (1.4 if arch == "swin" else 1.0) * (1.0 if explain else 0.4))
        return InferenceOutput(
            logits=logits,
            input_image=img,
            cam=cam,
            target_layer=f"{ARCHS[arch].target_layer} (simulated)",
            elapsed_ms=(time.perf_counter() - start) * 1000,
        )
