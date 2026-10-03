"""Image decoding and preprocessing.

This module is the single source of truth for preprocessing: the training code in
``/training`` imports it, so inference matches training exactly.

Pipeline (model input):
    decode (PNG/JPEG/DICOM, metadata discarded) -> grayscale uint8
    -> resize to ``image_size`` x ``image_size`` (INTER_AREA)
    -> optional CLAHE
    -> replicate to 3 channels -> [0, 1] -> ImageNet mean/std normalisation
"""

from __future__ import annotations

import base64
import io
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import torch

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

# DICOM attributes removed immediately after reading (defence in depth; only pixels are kept).
DICOM_IDENTIFYING_TAGS = (
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientSex",
    "PatientAge",
    "PatientAddress",
    "OtherPatientIDs",
    "OtherPatientNames",
    "ReferringPhysicianName",
    "PerformingPhysicianName",
    "InstitutionName",
    "InstitutionAddress",
    "AccessionNumber",
    "StudyID",
    "StudyDate",
    "StudyTime",
    "SeriesDate",
    "AcquisitionDate",
    "ContentDate",
    "StationName",
    "DeviceSerialNumber",
)


class ImageDecodeError(ValueError):
    """Raised when uploaded bytes cannot be decoded as a supported image."""


@dataclass(frozen=True)
class PreprocessConfig:
    """Preprocessing parameters. Saved next to trained weights so inference can match training."""

    image_size: int = 224
    use_clahe: bool = True
    clahe_clip_limit: float = 2.0
    clahe_tile_grid: int = 8

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PreprocessConfig":
        if not data:
            return cls()
        fields = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**fields)


@dataclass
class LoadedImage:
    """Decoded image pixels with no metadata attached."""

    gray: np.ndarray  # uint8, (H, W)
    rgb: np.ndarray  # uint8, (H, W, 3) — colour kept for the validator's colour check
    format: str
    is_dicom: bool
    file_size: int

    @property
    def width(self) -> int:
        return int(self.gray.shape[1])

    @property
    def height(self) -> int:
        return int(self.gray.shape[0])


# --------------------------------------------------------------------------- decoding


def is_dicom_bytes(data: bytes, filename: str | None = None) -> bool:
    """DICOM files carry the magic 'DICM' at byte offset 128."""
    if len(data) > 132 and data[128:132] == b"DICM":
        return True
    return bool(filename and filename.lower().endswith((".dcm", ".dicom")))


def _to_uint8(arr: np.ndarray) -> np.ndarray:
    """Min-max scale any numeric array to uint8."""
    arr = arr.astype(np.float32)
    lo, hi = float(np.percentile(arr, 0.5)), float(np.percentile(arr, 99.5))
    if hi <= lo:
        lo, hi = float(arr.min()), float(arr.max())
    if hi <= lo:
        return np.zeros(arr.shape, dtype=np.uint8)
    return np.clip((arr - lo) / (hi - lo) * 255.0, 0, 255).astype(np.uint8)


def strip_dicom_identifiers(ds: Any) -> Any:
    """Remove patient/institution identifiers and private tags from a pydicom Dataset in place."""
    for tag in DICOM_IDENTIFYING_TAGS:
        if tag in ds:
            delattr(ds, tag)
    try:
        ds.remove_private_tags()
    except Exception:  # pragma: no cover - defensive
        pass
    return ds


def _decode_dicom(data: bytes) -> np.ndarray:
    try:
        import pydicom
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImageDecodeError("DICOM support requires the 'pydicom' package.") from exc
    try:
        ds = pydicom.dcmread(io.BytesIO(data), force=True)
        strip_dicom_identifiers(ds)
        arr = ds.pixel_array
        try:
            from pydicom.pixels import apply_voi_lut
        except ImportError:  # pydicom < 3
            from pydicom.pixel_data_handlers.util import apply_voi_lut  # type: ignore
        try:
            arr = apply_voi_lut(arr, ds)
        except Exception:
            pass
        if arr.ndim == 3 and arr.shape[-1] not in (3, 4):
            arr = arr[0]  # multi-frame: first frame
        if arr.ndim == 3:
            arr = cv2.cvtColor(arr.astype(np.float32), cv2.COLOR_RGB2GRAY)
        gray = _to_uint8(arr)
        if str(getattr(ds, "PhotometricInterpretation", "")).upper() == "MONOCHROME1":
            gray = 255 - gray
        del ds
        return gray
    except ImageDecodeError:
        raise
    except Exception as exc:
        raise ImageDecodeError("Could not read the DICOM file.") from exc


def load_image(data: bytes, filename: str | None = None) -> LoadedImage:
    """Decode PNG/JPEG/DICOM bytes into metadata-free pixel arrays.

    EXIF orientation is applied, then all metadata is discarded (only pixels are kept).
    """
    if not data:
        raise ImageDecodeError("The uploaded file is empty.")

    if is_dicom_bytes(data, filename):
        gray = _decode_dicom(data)
        rgb = np.stack([gray] * 3, axis=-1)
        return LoadedImage(gray=gray, rgb=rgb, format="DICOM", is_dicom=True, file_size=len(data))

    try:
        with Image.open(io.BytesIO(data)) as im:
            fmt = (im.format or "UNKNOWN").upper()
            im = ImageOps.exif_transpose(im)
            if im.mode in ("I;16", "I;16B", "I;16L", "I", "F"):
                gray = _to_uint8(np.array(im))
                rgb = np.stack([gray] * 3, axis=-1)
            else:
                rgb = np.array(im.convert("RGB"), dtype=np.uint8)
                gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageDecodeError("Unsupported or corrupted image. Please upload a PNG, JPEG or DICOM file.") from exc

    if fmt not in ("PNG", "JPEG", "MPO", "BMP", "TIFF", "WEBP"):
        raise ImageDecodeError(f"Unsupported image format: {fmt}.")
    return LoadedImage(
        gray=np.ascontiguousarray(gray),
        rgb=np.ascontiguousarray(rgb),
        format="JPEG" if fmt == "MPO" else fmt,
        is_dicom=False,
        file_size=len(data),
    )


# ---------------------------------------------------------------------- preprocessing


def apply_clahe(gray: np.ndarray, clip_limit: float = 2.0, tile_grid: int = 8) -> np.ndarray:
    """Contrast Limited Adaptive Histogram Equalisation on a uint8 grayscale image."""
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid))
    return clahe.apply(gray)


def prepare_uint8(gray: np.ndarray, cfg: PreprocessConfig = PreprocessConfig()) -> np.ndarray:
    """Resize (and optionally CLAHE) a grayscale image -> uint8 (size, size).

    Training applies augmentation to this output, then :func:`to_model_tensor`.
    """
    if gray.ndim == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_RGB2GRAY)
    resized = cv2.resize(gray, (cfg.image_size, cfg.image_size), interpolation=cv2.INTER_AREA)
    if cfg.use_clahe:
        resized = apply_clahe(resized, cfg.clahe_clip_limit, cfg.clahe_tile_grid)
    return resized


def to_model_array(img_uint8: np.ndarray) -> np.ndarray:
    """uint8 (H, W) grayscale -> normalised float32 array (3, H, W). NumPy-only twin of to_model_tensor."""
    x = np.repeat((img_uint8.astype(np.float32) / 255.0)[None], 3, axis=0)
    mean = np.asarray(IMAGENET_MEAN, dtype=np.float32)[:, None, None]
    std = np.asarray(IMAGENET_STD, dtype=np.float32)[:, None, None]
    return (x - mean) / std


def to_model_tensor(img_uint8: np.ndarray) -> torch.Tensor:
    """uint8 (H, W) grayscale -> normalised float tensor (3, H, W)."""
    import torch

    x = torch.from_numpy(img_uint8.astype(np.float32) / 255.0)
    x = x.unsqueeze(0).repeat(3, 1, 1)
    mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
    std = torch.tensor(IMAGENET_STD).view(3, 1, 1)
    return (x - mean) / std


def preprocess(gray: np.ndarray, cfg: PreprocessConfig = PreprocessConfig()) -> torch.Tensor:
    """Full inference preprocessing -> batch tensor (1, 3, size, size)."""
    return to_model_tensor(prepare_uint8(gray, cfg)).unsqueeze(0)


def validator_tensor(rgb: np.ndarray, size: int = 224) -> torch.Tensor:
    """Input for the learned CXR validator: colour is kept (photos are a key negative class)."""
    import torch

    resized = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    x = torch.from_numpy(resized).permute(2, 0, 1)
    mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
    std = torch.tensor(IMAGENET_STD).view(3, 1, 1)
    return ((x - mean) / std).unsqueeze(0)


# --------------------------------------------------------------------------- encoding


def make_display_image(gray: np.ndarray, max_side: int = 512) -> np.ndarray:
    """Aspect-preserving downscale used for the viewer, overlays and thumbnails."""
    h, w = gray.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale >= 1.0:
        return gray.copy()
    return cv2.resize(gray, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)


def encode_png_data_uri(arr: np.ndarray) -> str:
    """Encode a uint8 grayscale or RGB array as a ``data:image/png;base64`` URI."""
    if arr.ndim == 3:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode(".png", arr, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    if not ok:  # pragma: no cover
        raise RuntimeError("PNG encoding failed")
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def encode_jpeg_data_uri(arr: np.ndarray, quality: int = 80) -> str:
    if arr.ndim == 3:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode(".jpg", arr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:  # pragma: no cover
        raise RuntimeError("JPEG encoding failed")
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def resize_to(arr: np.ndarray, width: int, height: int) -> np.ndarray:
    interp = cv2.INTER_AREA if arr.shape[1] > width else cv2.INTER_LINEAR
    return cv2.resize(arr, (width, height), interpolation=interp)
