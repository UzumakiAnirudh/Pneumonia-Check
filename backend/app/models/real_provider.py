"""TorchModelProvider — runs trained DenseNet121 / Swin weights from ``backend/weights``.

Expected files (any subset; missing ones are reported by /api/health):

    weights/densenet_stage1.pth   weights/swin_stage1.pth
    weights/densenet_stage2.pth   weights/swin_stage2.pth
    weights/densenet_three_class.pth  weights/swin_three_class.pth   (three_class mode only)

Each ``.pth`` may have a sidecar ``<name>.json`` written by ``training/train.py`` containing the
preprocessing config used during training, which is then applied here.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn

from app.models.architectures import (
    ARCHS,
    TASK_CLASSES,
    build_model,
    get_module,
    load_state_dict,
    read_metadata,
    reshape_transform_for,
    weights_filename,
)
from app.models.provider import (
    InferenceOutput,
    ModelInfo,
    ModelProvider,
    ModelUnavailableError,
)
from app.services.gradcam import compute_gradcam
from app.services.preprocessing import PreprocessConfig, prepare_uint8, to_model_tensor

logger = logging.getLogger(__name__)


def resolve_device(name: str = "auto") -> torch.device:
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


@dataclass
class LoadedModel:
    model: nn.Module
    preprocess: PreprocessConfig
    lock: threading.Lock


class TorchModelProvider(ModelProvider):
    is_mock = False

    def __init__(
        self,
        weights_dir: Path,
        tasks: list[str],
        device: torch.device,
        default_preprocess: PreprocessConfig | None = None,
    ) -> None:
        self.weights_dir = weights_dir
        self.device = device
        self.default_preprocess = default_preprocess or PreprocessConfig()
        self.models: dict[tuple[str, str], LoadedModel] = {}
        for arch in ARCHS:
            for task in tasks:
                self._try_load(arch, task)

    def _try_load(self, arch: str, task: str) -> None:
        path = self.weights_dir / weights_filename(arch, task)
        if not path.exists():
            logger.warning("Weights not found: %s", path)
            return
        try:
            model = build_model(arch, num_classes=len(TASK_CLASSES[task]), pretrained=False)
            model.load_state_dict(load_state_dict(path))
            model.eval().to(self.device)
        except Exception:
            logger.exception("Failed to load %s", path)
            return
        meta = read_metadata(self.weights_dir, arch, task)
        cfg = PreprocessConfig.from_dict(meta.get("preprocess")) if meta else self.default_preprocess
        self.models[(arch, task)] = LoadedModel(model=model, preprocess=cfg, lock=threading.Lock())
        logger.info("Loaded %s %s from %s (preprocess=%s)", arch, task, path.name, cfg)

    @property
    def device_name(self) -> str:
        return str(self.device)

    def available(self, arch: str, task: str) -> bool:
        return (arch, task) in self.models

    def status(self, tasks: list[str]) -> list[ModelInfo]:
        out = []
        for key, spec in ARCHS.items():
            weights = {task: (key, task) in self.models for task in tasks}
            out.append(
                ModelInfo(
                    key=key,
                    name=spec.display_name,
                    ready=all(weights.values()),
                    weights=weights,
                )
            )
        return out

    def infer(self, arch: str, task: str, gray: np.ndarray, explain: bool = False) -> InferenceOutput:
        loaded = self.models.get((arch, task))
        if loaded is None:
            raise ModelUnavailableError(
                f"No weights for {ARCHS[arch].display_name} ({task}). "
                f"Place {weights_filename(arch, task)} in {self.weights_dir}."
            )
        start = time.perf_counter()
        img = prepare_uint8(gray, loaded.preprocess)
        x = to_model_tensor(img).unsqueeze(0).to(self.device)
        spec = ARCHS[arch]
        cam = None
        # Grad-CAM registers hooks on the shared module, so serialise per model.
        with loaded.lock:
            if explain:
                logits, cam = compute_gradcam(
                    loaded.model,
                    get_module(loaded.model, spec.target_layer),
                    x,
                    reshape_transform=reshape_transform_for(arch),
                )
            else:
                with torch.inference_mode():
                    logits = loaded.model(x).float().cpu().numpy()[0]
        return InferenceOutput(
            logits=np.asarray(logits, dtype=np.float32),
            input_image=img,
            cam=cam,
            target_layer=spec.target_layer,
            elapsed_ms=(time.perf_counter() - start) * 1000,
        )
