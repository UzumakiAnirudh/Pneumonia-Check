"""OnnxModelProvider — runs exported models with onnxruntime (no PyTorch needed).

Used for lightweight deployments (e.g. a 512 MB free web service). Each ``<arch>_<task>.onnx``
file (written by ``training/export_onnx.py``) returns both the logits and the raw 7x7 Grad-CAM for
the predicted class, computed in-graph with the exact closed-form gradient. Post-processing here
mirrors pytorch-grad-cam (min-max scale, bilinear resize to the input size), so explanations match
the PyTorch provider.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.models.provider import InferenceOutput, ModelInfo, ModelProvider, ModelUnavailableError
from app.models.specs import ARCHS, onnx_filename, read_metadata
from app.services.preprocessing import PreprocessConfig, prepare_uint8, to_model_array

logger = logging.getLogger(__name__)


@dataclass
class LoadedOnnx:
    session: object
    preprocess: PreprocessConfig
    lock: threading.Lock


def scale_cam(cam: np.ndarray, size: int) -> np.ndarray:
    """pytorch-grad-cam's scale_cam_image: min-max normalise, then resize (bilinear) to size x size."""
    cam = cam - cam.min()
    cam = cam / (1e-7 + cam.max())
    return cv2.resize(cam.astype(np.float32), (size, size))


class OnnxModelProvider(ModelProvider):
    is_mock = False

    def __init__(
        self, weights_dir: Path, tasks: list[str], default_preprocess: PreprocessConfig | None = None, threads: int = 1
    ) -> None:
        import onnxruntime as ort

        self.weights_dir = weights_dir
        self.default_preprocess = default_preprocess or PreprocessConfig()
        self.models: dict[tuple[str, str], LoadedOnnx] = {}
        options = ort.SessionOptions()
        options.enable_cpu_mem_arena = False  # lower peak memory on small instances
        options.intra_op_num_threads = threads
        for arch in ARCHS:
            for task in tasks:
                path = weights_dir / onnx_filename(arch, task)
                if not path.exists():
                    logger.warning("ONNX model not found: %s", path)
                    continue
                session = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
                meta = read_metadata(weights_dir, arch, task)
                cfg = PreprocessConfig.from_dict(meta.get("preprocess")) if meta else self.default_preprocess
                self.models[(arch, task)] = LoadedOnnx(session, cfg, threading.Lock())
                logger.info("Loaded %s (preprocess=%s)", path.name, cfg)

    @property
    def device_name(self) -> str:
        return "cpu (onnxruntime)"

    def available(self, arch: str, task: str) -> bool:
        return (arch, task) in self.models

    def status(self, tasks: list[str]) -> list[ModelInfo]:
        out = []
        for key, spec in ARCHS.items():
            weights = {task: (key, task) in self.models for task in tasks}
            out.append(ModelInfo(key=key, name=spec.display_name, ready=all(weights.values()), weights=weights))
        return out

    def infer(self, arch: str, task: str, gray: np.ndarray, explain: bool = False) -> InferenceOutput:
        loaded = self.models.get((arch, task))
        if loaded is None:
            raise ModelUnavailableError(
                f"No ONNX model for {ARCHS[arch].display_name} ({task}). "
                f"Run training/export_onnx.py to create {onnx_filename(arch, task)} in {self.weights_dir}."
            )
        start = time.perf_counter()
        img = prepare_uint8(gray, loaded.preprocess)
        x = to_model_array(img)[None]
        with loaded.lock:
            logits, cam = loaded.session.run(None, {"input": x})  # type: ignore[attr-defined]
        cam_full = scale_cam(cam[0], img.shape[0]) if explain else None
        return InferenceOutput(
            logits=np.asarray(logits[0], dtype=np.float32),
            input_image=img,
            cam=cam_full,
            target_layer=ARCHS[arch].target_layer,
            elapsed_ms=(time.perf_counter() - start) * 1000,
        )
