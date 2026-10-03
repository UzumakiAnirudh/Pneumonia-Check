"""Simple lung-field mask used to measure where Grad-CAM attention falls.

This is deliberately lightweight (no segmentation network): an anatomical template
of two ellipses, refined per side by the convex hull of dark (air-filled) pixels.
Using the convex hull keeps consolidated (bright) regions inside the lung field.
"""

from __future__ import annotations

import cv2
import numpy as np

# Template in normalised coords for a frontal CXR (image-left = patient's right lung).
_TEMPLATE = (
    # (cx, cy, half-width, half-height)
    (0.31, 0.50, 0.165, 0.33),
    (0.69, 0.51, 0.155, 0.32),
)


def template_mask(size: int) -> np.ndarray:
    """Two-ellipse anatomical lung template as a boolean (size, size) mask."""
    mask = np.zeros((size, size), dtype=np.uint8)
    for cx, cy, ax, ay in _TEMPLATE:
        cv2.ellipse(
            mask,
            (round(cx * size), round(cy * size)),
            (round(ax * size), round(ay * size)),
            0,
            0,
            360,
            1,
            -1,
        )
    return mask.astype(bool)


def estimate_lung_mask(img: np.ndarray, refine: bool = True) -> np.ndarray:
    """Estimate lung fields on a square uint8 grayscale image.

    Args:
        img: uint8 (N, N) image, e.g. the 224x224 model input.
        refine: refine the template with an Otsu/convex-hull step; falls back to the template
            when the refined region looks implausible.
    """
    size = img.shape[0]
    base = template_mask(size)
    if not refine:
        return base

    blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=size / 112)
    search = cv2.dilate(base.astype(np.uint8), np.ones((size // 14, size // 14), np.uint8)).astype(bool)
    vals = blurred[search]
    if vals.size == 0:
        return base
    thresh, _ = cv2.threshold(vals.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark = ((blurred <= thresh) & search).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    refined = np.zeros_like(dark)
    half = size // 2
    for side_slice in (slice(0, half), slice(half, size)):
        part = np.zeros_like(dark)
        part[:, side_slice] = dark[:, side_slice]
        n, labels, stats, _ = cv2.connectedComponentsWithStats(part, connectivity=8)
        if n <= 1:
            continue
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        pts = np.column_stack(np.nonzero(labels == largest))[:, ::-1].astype(np.int32)
        hull = cv2.convexHull(pts)
        cv2.fillConvexPoly(refined, hull, 1)

    area, base_area = int(refined.sum()), int(base.sum())
    if not (0.45 * base_area <= area <= 1.6 * base_area):
        return base
    return refined.astype(bool)
