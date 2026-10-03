from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import make_settings, register


def _post(client, data, path="/api/predict", **form):
    return client.post(path, files={"file": ("x.png", data, "image/png")}, data=form)


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["use_mock_models"] is True
    assert {m["key"] for m in body["models"]} == {"densenet", "swin"}
    assert body["validator"]["method"] == "heuristic"


def test_validate_endpoint(client, sample_bytes, colour_photo):
    ok = _post(client, sample_bytes["normal_01"], "/api/validate").json()
    assert ok["is_valid"] and ok["image"]["width"] > 0
    bad = _post(client, colour_photo, "/api/validate").json()
    assert not bad["is_valid"]
    assert bad["message"] == "This doesn't look like a chest X-ray. Please upload a frontal chest X-ray image."


def test_predict_and_history_roundtrip(client, sample_bytes):
    r = _post(
        client, sample_bytes["viral_02"], model="both", threshold="0.8", save_history="true", source_name="Viral B"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["saved_to_history"] and len(body["results"]) == 2
    assert all(res["reliability"]["threshold"] == 0.8 for res in body["results"])

    items = client.get("/api/history").json()
    assert len(items) == 1 and items[0]["source_name"] == "Viral B"
    assert items[0]["thumbnail"].startswith("data:image/jpeg;base64,")
    item = client.get(f"/api/history/{body['id']}").json()
    assert item["results"][0]["explanation"]["overlay_png"] is None  # overlays are never stored
    assert client.delete(f"/api/history/{body['id']}").status_code == 204
    assert client.get(f"/api/history/{body['id']}").status_code == 404


def test_predict_without_history(client, sample_bytes):
    body = _post(client, sample_bytes["normal_02"], model="densenet").json()
    assert body["saved_to_history"] is False
    assert client.get("/api/history").json() == []


def test_predict_rejects_non_cxr(client, document):
    r = _post(client, document)
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["code"] == "not_chest_xray" and detail["validation"]["is_chest_xray"] is False


def test_predict_bad_inputs(client, sample_bytes):
    assert _post(client, b"garbage").status_code == 400
    assert _post(client, sample_bytes["normal_01"], model="resnet").status_code == 422


def test_clear_history(client, sample_bytes):
    for _ in range(2):
        _post(client, sample_bytes["normal_01"], save_history="true")
    assert len(client.get("/api/history").json()) == 2
    assert client.delete("/api/history").status_code == 204
    assert client.get("/api/history").json() == []


def test_samples_and_metrics(tmp_path, sample_bytes):
    samples = tmp_path / "samples"
    samples.mkdir()
    (samples / "normal_01.png").write_bytes(sample_bytes["normal_01"])
    (samples / "samples.json").write_text(
        '[{"id": "normal_01", "label": "NORMAL", "title": "Normal A", "file": "normal_01.png"},'
        ' {"id": "gone", "label": "VIRAL", "title": "Missing file", "file": "gone.png"}]'
    )
    metrics = tmp_path / "metrics.json"
    settings = make_settings(tmp_path, samples_dir=samples, metrics_path=metrics, gallery_dir=tmp_path / "gallery")
    with TestClient(create_app(settings)) as c:
        listed = c.get("/api/samples").json()
        assert [s["id"] for s in listed] == ["normal_01"]  # entries without a file are skipped
        assert c.get(listed[0]["url"]).status_code == 200

        assert c.get("/api/metrics").json()["detail"]["code"] == "metrics_missing"
        metrics.write_text('{"internal": {"densenet": {}}, "gallery": [{"image": "a.jpg"}]}')
        body = c.get("/api/metrics").json()
        assert "densenet" in body["internal"]
        assert body["gallery"][0]["image"] == "/api/metrics/gallery/a.jpg"


def test_history_disabled(tmp_path, sample_bytes):
    with TestClient(create_app(make_settings(tmp_path, history_enabled=False))) as c:
        register(c)
        body = _post(c, sample_bytes["normal_01"], save_history="true").json()
        assert body["saved_to_history"] is False
        assert c.get("/api/health").json()["history_enabled"] is False
        assert c.get("/api/history").json() == []


def test_real_mode_without_weights_returns_503(tmp_path, sample_bytes):
    with TestClient(create_app(make_settings(tmp_path, use_mock_models=False))) as c:
        register(c)
        assert c.get("/api/health").json()["status"] == "degraded"
        r = _post(c, sample_bytes["normal_01"])
        assert r.status_code == 503 and r.json()["detail"]["code"] == "model_unavailable"


def test_health_reports_training_status(tmp_path):
    status = tmp_path / "training_status.json"
    status.write_text(
        '{"state": "training", "label": "Training Swin Transformer Stage 1", "percent": 55.0, "epoch": 4, "epochs": 10}'
    )
    with TestClient(create_app(make_settings(tmp_path, training_status_path=status))) as c:
        t = c.get("/api/health").json()["training"]
        assert t["state"] == "training" and t["percent"] == 55.0 and t["epoch"] == 4
        status.write_text("not json")
        assert c.get("/api/health").json()["training"] is None  # corrupt file never breaks health


def test_blank_database_url_falls_back_to_sqlite():
    from app.config import Settings

    assert Settings(_env_file=None, database_url="  ").database_url.startswith("sqlite:///")
