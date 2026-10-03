"""ONNX deployment path: same outputs as PyTorch, and the API runs without PyTorch installed."""

import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import pytest
import torch

ort = pytest.importorskip("onnxruntime")
TRAINING = Path(__file__).resolve().parents[2] / "training"


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    """Random-init DenseNet + Swin (stage1 & stage2) exported to .pth and .onnx in a temp dir."""
    sys.path.insert(0, str(TRAINING))
    from export_onnx import wrap

    from app.models.architectures import TASK_CLASSES, build_model, weights_filename

    d = tmp_path_factory.mktemp("weights")
    torch.manual_seed(0)
    for arch in ("densenet", "swin"):
        for task in ("stage1", "stage2"):
            model = build_model(arch, len(TASK_CLASSES[task])).eval()
            torch.save(model.state_dict(), d / weights_filename(arch, task))
            with torch.no_grad():
                torch.onnx.export(
                    wrap(arch, model).eval(),
                    (torch.randn(1, 3, 224, 224),),
                    str(d / f"{arch}_{task}.onnx"),
                    input_names=["input"],
                    output_names=["logits", "cam"],
                    dynamic_axes={"input": {0: "b"}, "logits": {0: "b"}, "cam": {0: "b"}},
                    opset_version=17,
                    dynamo=False,
                )
    return d


@pytest.mark.parametrize("arch", ["densenet", "swin"])
def test_onnx_matches_torch(exported, arch, sample_bytes):
    from app.models.onnx_provider import OnnxModelProvider
    from app.models.real_provider import TorchModelProvider
    from app.services.preprocessing import load_image

    gray = load_image(sample_bytes["bacterial_01"]).gray
    t = TorchModelProvider(exported, ["stage1"], torch.device("cpu")).infer(arch, "stage1", gray, explain=True)
    o = OnnxModelProvider(exported, ["stage1"]).infer(arch, "stage1", gray, explain=True)
    assert np.allclose(t.logits, o.logits, atol=1e-3)
    assert o.cam.shape == t.cam.shape == (224, 224)
    if t.cam.std() > 0:
        assert np.corrcoef(t.cam.ravel(), o.cam.ravel())[0, 1] > 0.999


def test_api_runs_without_torch(exported, tmp_path):
    """Block `import torch` entirely and serve a prediction from the ONNX models."""
    script = textwrap.dedent(f"""
        import sys
        sys.modules["torch"] = None  # any `import torch` now raises ImportError
        from fastapi.testclient import TestClient
        from app.config import Settings
        from app.main import create_app
        s = Settings(_env_file=None, use_mock_models=False, weights_dir=r"{exported}",
                     database_url=r"sqlite:///{tmp_path / 'db.sqlite'}", metrics_path=r"{tmp_path / 'm.json'}")
        with TestClient(create_app(s)) as c:
            assert c.get("/api/health").json()["device"] == "cpu (onnxruntime)"
            assert c.post("/api/auth/register", json={{"name": "A", "email": "a@b.co", "password": "pass-word-1"}}).status_code == 201
            r = c.post("/api/predict", files={{"file": ("x.png", open(r"{tmp_path / 'x.png'}", "rb").read(), "image/png")}}, data={{"model": "both"}})
            assert r.status_code == 200, r.text
            assert all(res["explanation"]["heatmap_png"] for res in r.json()["results"])
        print("NO_TORCH_OK")
        """)
    from tests.phantoms import make_phantom
    from tests.conftest import encode

    (tmp_path / "x.png").write_bytes(encode(make_phantom("viral", 53, "right")))
    out = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1]
    )
    assert "NO_TORCH_OK" in out.stdout, out.stderr[-2000:]
