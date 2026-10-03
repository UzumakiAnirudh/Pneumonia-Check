"""Shared fixtures. Tests run against the mock provider with a temporary SQLite DB."""

from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.main import create_app


def encode(arr: np.ndarray, fmt: str = "PNG", **kwargs) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, fmt, **kwargs)
    return buf.getvalue()


@pytest.fixture(scope="session")
def sample_bytes() -> dict[str, bytes]:
    """Deterministic synthetic CXR phantoms (see tests/phantoms.py)."""
    from tests.phantoms import make_phantom

    specs = {
        "normal_01": ("normal", 11, "right"),
        "normal_02": ("normal", 23, "right"),
        "bacterial_01": ("bacterial", 31, "right"),
        "bacterial_02": ("bacterial", 47, "left"),
        "viral_01": ("viral", 53, "right"),
        "viral_02": ("viral", 67, "right"),
    }
    return {name: encode(make_phantom(kind, seed, focus)) for name, (kind, seed, focus) in specs.items()}


@pytest.fixture
def colour_photo() -> bytes:
    rng = np.random.default_rng(0)
    img = np.zeros((600, 800, 3), np.uint8)
    img[:300] = (80, 140, 220)
    img[300:] = (60, 160, 60)
    img = cv2.GaussianBlur(img, (0, 0), 5) + rng.integers(0, 30, img.shape).astype(np.uint8)
    return encode(img, "JPEG")


@pytest.fixture
def document() -> bytes:
    doc = np.full((1100, 850), 250, np.uint8)
    for y in range(80, 1000, 30):
        cv2.putText(doc, "Lorem ipsum dolor sit amet consectetur", (60, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 20, 2)
    return encode(doc)


def make_settings(tmp_path: Path, **overrides) -> Settings:
    defaults = dict(
        mock_latency_ms=0,
        use_mock_models=True,
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        weights_dir=tmp_path / "weights",
        _env_file=None,
    )
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path)


def register(
    client: TestClient, email: str = "dr.a@example.com", name: str = "Dr A", password: str = "s3cure-pass"
) -> dict:
    """Register (which also logs in: the session cookie is kept by the client)."""
    r = client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def anon_client(settings: Settings):
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture
def client(anon_client: TestClient):
    """A client logged in as a fresh account."""
    register(anon_client)
    return anon_client
