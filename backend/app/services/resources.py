"""Static resources: evaluation metrics JSON and bundled sample images."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas.samples import SampleImage

GALLERY_URL_PREFIX = "/api/metrics/gallery/"
SAMPLES_URL_PREFIX = "/api/samples/files/"


def load_metrics(path: Path) -> dict[str, Any] | None:
    """Load the metrics file written by training/evaluate.py (and friends).

    Gallery image paths are rewritten to API URLs.
    """
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    for item in data.get("gallery", []):
        image = item.get("image", "")
        if image and not image.startswith(("http", "/", "data:")):
            item["image"] = GALLERY_URL_PREFIX + image
    return data


def load_samples(samples_dir: Path) -> list[SampleImage]:
    """Read ``samples/samples.json`` — [{id, label, title, description, file, synthetic}]."""
    manifest = samples_dir / "samples.json"
    if not manifest.exists():
        return []
    items = json.loads(manifest.read_text())
    out = []
    for it in items:
        file = it.get("file", f"{it['id']}.png")
        if not (samples_dir / file).exists():
            continue
        out.append(
            SampleImage(
                id=it["id"],
                label=it["label"],
                title=it["title"],
                description=it.get("description", ""),
                url=SAMPLES_URL_PREFIX + file,
                synthetic=bool(it.get("synthetic", False)),
            )
        )
    return out
