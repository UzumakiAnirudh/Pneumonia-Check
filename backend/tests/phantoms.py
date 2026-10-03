"""Synthetic chest X-ray phantoms used ONLY by the test-suite.

Procedurally drawn images (torso, lungs, mediastinum, heart, ribs, clavicles). Kinds:
``normal``, ``bacterial`` (focal consolidation), ``viral`` (bilateral patchy opacities).
They give the validator, preprocessing and API tests deterministic CXR-like inputs.
"""

from __future__ import annotations

import cv2
import numpy as np

H, W = 1000, 900


def _ellipse(mask_shape, center, axes, angle=0.0) -> np.ndarray:
    m = np.zeros(mask_shape, np.uint8)
    cv2.ellipse(m, (int(center[0]), int(center[1])), (int(axes[0]), int(axes[1])), angle, 0, 360, 1, -1)
    return m.astype(np.float32)


def _blur(a: np.ndarray, sigma: float) -> np.ndarray:
    return cv2.GaussianBlur(a, (0, 0), sigmaX=sigma)


def _blobs(rng, n, centers, spread, radius, shape) -> np.ndarray:
    out = np.zeros(shape, np.float32)
    for _ in range(n):
        c = centers[rng.integers(len(centers))]
        x = c[0] + rng.normal(0, spread[0])
        y = c[1] + rng.normal(0, spread[1])
        r = radius * rng.uniform(0.6, 1.4)
        cv2.circle(out, (int(x), int(y)), int(r), 1.0, -1)
    return out


def _lung_polygon(side: int, rng) -> np.ndarray:
    """Rounded-triangle lung field. side=-1 -> image left (patient's right)."""
    cx = W * 0.5
    med = W * 0.075 + (W * 0.03 if side == 1 else 0)  # left lung sits further out (heart)
    lat = W * rng.uniform(0.36, 0.385)
    pts = []
    # medial border (top -> bottom), apex, lateral border, base
    for t in np.linspace(0, 1, 12):
        pts.append((cx + side * (med + W * 0.02 * np.sin(t * np.pi)), H * (0.2 + 0.58 * t)))
    for t in np.linspace(0, 1, 14):  # base: costophrenic angle -> medial
        x = cx + side * (med + (lat - med) * t)
        y = H * 0.78 + H * 0.06 * np.sin(np.pi * t * 0.9) - H * 0.02 * t
        pts.append((x, y))
    for t in np.linspace(1, 0, 18):  # lateral border up to apex
        x = cx + side * (W * 0.12 + (lat - W * 0.12) * np.sin(np.pi / 2 * (t**0.7)))
        y = H * (0.17 + 0.66 * t)
        pts.append((x, y))
    return np.array(pts, np.int32)


def make_phantom(kind: str, seed: int, focus: str = "right") -> np.ndarray:
    rng = np.random.default_rng(seed)
    shape = (H, W)
    img = np.full(shape, 0.03, np.float32)

    # Torso, neck and shoulders
    body = _ellipse(shape, (W * 0.5, H * 0.62), (W * 0.47, H * 0.56))
    body = np.maximum(body, _ellipse(shape, (W * 0.14, H * 0.2), (W * 0.2, H * 0.12), angle=-15))
    body = np.maximum(body, _ellipse(shape, (W * 0.86, H * 0.2), (W * 0.2, H * 0.12), angle=15))
    neck = np.zeros(shape, np.float32)
    neck[0 : int(H * 0.2), int(W * 0.4) : int(W * 0.6)] = 1
    body = np.maximum(body, neck)
    img += 0.46 * _blur(body, 22)

    # Lungs
    lungs = np.zeros(shape, np.float32)
    for side in (-1, 1):
        cv2.fillPoly(lungs, [_lung_polygon(side, rng)], 1.0)
    heart = _ellipse(shape, (W * 0.565, H * 0.665), (W * 0.15, H * 0.125), angle=-25)
    lungs = np.clip(lungs - _blur(heart, 8) * 0.95, 0, 1)
    lung_soft = _blur(lungs, 16)
    # Darker laterally/apically, denser near the hila
    yy, xx = np.mgrid[0:H, 0:W]
    hilar = np.exp(-(((np.abs(xx - W * 0.5) - W * 0.13) / (W * 0.09)) ** 2 + ((yy - H * 0.47) / (H * 0.12)) ** 2))
    img -= 0.36 * lung_soft
    img += 0.07 * hilar * lung_soft

    # Vascular markings: branching streaks from the hila
    vessels = np.zeros(shape, np.float32)
    for side in (-1, 1):
        for _ in range(26):
            x0, y0 = W * 0.5 + side * W * 0.13, H * 0.47 + rng.normal(0, 18)
            ang = rng.uniform(-1.2, 1.2)
            length = rng.uniform(0.08, 0.2) * W
            x1 = x0 + side * length * np.cos(ang)
            y1 = y0 + length * np.sin(ang) * 1.2
            cv2.line(vessels, (int(x0), int(y0)), (int(x1), int(y1)), 1.0, thickness=int(rng.integers(2, 5)))
    img += 0.05 * _blur(vessels, 3) * lung_soft

    # Mediastinum, spine, heart, aortic knob, trachea
    spine = np.zeros(shape, np.float32)
    spine[:, int(W * 0.47) : int(W * 0.53)] = 1
    img += 0.16 * _blur(spine * body, 10)
    plates = np.zeros(shape, np.float32)
    for i in range(14):  # vertebral end plates (subtle)
        y = int(H * 0.12 + i * H * 0.062)
        cv2.line(plates, (int(W * 0.475), y), (int(W * 0.525), y), 1.0, 4)
    img -= 0.05 * _blur(plates, 2.5)
    img += 0.15 * _blur(heart, 22)
    img += 0.09 * _blur(_ellipse(shape, (W * 0.56, H * 0.33), (W * 0.045, H * 0.035)), 10)
    trachea = np.zeros(shape, np.float32)
    trachea[int(H * 0.0) : int(H * 0.38), int(W * 0.487) : int(W * 0.513)] = 1
    img -= 0.1 * _blur(trachea, 6)

    # Diaphragm / upper abdomen — homogeneous soft-tissue density below the lungs
    abdomen = np.zeros(shape, np.float32)
    abdomen[int(H * 0.8) :, :] = 1
    img += 0.05 * _blur(abdomen * body, 30)

    # Ribs: posterior arcs (upper halves of ellipses), fainter anterior arcs
    ribs = np.zeros(shape, np.float32)
    spacing = H * rng.uniform(0.062, 0.068)
    for i in range(10):
        y0 = H * 0.24 + i * spacing
        width = W * (0.2 + 0.012 * min(i, 6))
        for side in (-1, 1):
            cx = W * 0.5 + side * (W * 0.035 + width)
            cv2.ellipse(
                ribs,
                (int(cx), int(y0)),
                (int(width), int(H * 0.06)),
                0,
                180 if side == -1 else 270,
                270 if side == -1 else 360,
                1.0,
                int(H * 0.016),
            )
            cv2.ellipse(
                ribs,
                (int(cx), int(y0 + H * 0.05)),
                (int(width), int(H * 0.08)),
                0,
                90 if side == 1 else 0,
                180 if side == 1 else 90,
                0.45,
                int(H * 0.012),
            )
    img += 0.085 * _blur(ribs * body, 3.5)

    # Clavicles: gently S-shaped
    clav = np.zeros(shape, np.float32)
    for side in (-1, 1):
        t = np.linspace(0, 1, 30)
        xs = W * 0.5 + side * (W * 0.06 + W * 0.3 * t)
        ys = H * 0.2 - H * 0.06 * t + H * 0.012 * np.sin(2 * np.pi * t)
        cv2.polylines(clav, [np.stack([xs, ys], 1).astype(np.int32)], False, 1.0, int(H * 0.024))
    img += 0.12 * _blur(clav, 4)

    # Pathology
    lung_mask = _blur(lungs, 6)
    if kind == "bacterial":
        side = -1 if focus == "right" else 1  # patient's right -> image left
        cx, cy = W * 0.5 + side * W * 0.245, H * (0.64 if focus == "right" else 0.6)
        cons = _blobs(rng, 18, [(cx, cy)], (W * 0.05, H * 0.05), W * 0.055, shape)
        cons = _blur(cons, 20)
        cons /= cons.max() + 1e-6
        bron = np.zeros(shape, np.float32)
        for _ in range(5):
            x0, y0 = cx + rng.normal(0, 25), cy - 60 + rng.normal(0, 20)
            cv2.line(bron, (int(x0), int(y0)), (int(x0 + side * rng.uniform(10, 40)), int(y0 + 90)), 1.0, 4)
        img += (0.42 * cons - 0.06 * _blur(bron, 2) * cons) * lung_mask
    elif kind == "viral":
        centers = [(W * 0.36, H * 0.5), (W * 0.64, H * 0.5), (W * 0.32, H * 0.64), (W * 0.7, H * 0.62)]
        patchy = _blobs(rng, 90, centers, (W * 0.06, H * 0.08), W * 0.02, shape)
        patchy = _blur(patchy, 12)
        patchy /= patchy.max() + 1e-6
        reticular = _blur(rng.normal(0, 1, shape).astype(np.float32), 2.5)
        reticular = np.clip(reticular, 0, None) / (reticular.max() + 1e-6)
        perihilar = hilar**0.5
        img += (0.17 * patchy + 0.07 * reticular + 0.06 * perihilar) * lung_mask

    # Film texture, slight blur, vignette and exposure variation
    img = _blur(img, 1.6)
    img += _blur(rng.normal(0, 0.03, shape).astype(np.float32), 1.0)
    vignette = 1 - 0.22 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    img = img * vignette * rng.uniform(0.96, 1.04) + 0.02
    img = np.clip(img, 0, 1) ** 0.95
    return (img * 255).astype(np.uint8)
