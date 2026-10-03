"""Accounts, sessions and per-account history isolation."""

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.auth import hash_password, verify_password
from tests.conftest import register


def _predict(c, data, **form):
    return c.post("/api/predict", files={"file": ("x.png", data, "image/png")}, data={"save_history": "true", **form})


def test_password_hashing():
    h = hash_password("correct horse 1")
    assert h.startswith("pbkdf2_sha256$") and "correct horse" not in h
    assert verify_password("correct horse 1", h)
    assert not verify_password("wrong", h)
    assert hash_password("same-pass1") != hash_password("same-pass1")  # salted


def test_register_login_logout_flow(anon_client):
    c = anon_client
    assert c.get("/api/auth/me").status_code == 401
    user = register(c, email="Dr.Ana@Example.com", name="  Ana  ")
    assert user["email"] == "dr.ana@example.com" and user["name"] == "Ana"
    cookie = c.cookies.get("pneumoscan_session")
    assert cookie and len(cookie) >= 40
    assert c.get("/api/auth/me").json()["email"] == "dr.ana@example.com"

    assert c.post("/api/auth/logout").status_code == 204
    assert c.get("/api/auth/me").status_code == 401
    # The old token is revoked server-side, not just removed from the browser.
    c.cookies.set("pneumoscan_session", cookie)
    assert c.get("/api/auth/me").status_code == 401

    r = c.post("/api/auth/login", json={"email": "DR.ANA@example.com", "password": "s3cure-pass"})
    assert r.status_code == 200 and c.get("/api/auth/me").status_code == 200


def test_register_validation_and_duplicates(anon_client):
    c = anon_client
    bad = [
        {"name": "A", "email": "not-an-email", "password": "s3cure-pass"},
        {"name": "A", "email": "a@b.co", "password": "short1"},
        {"name": "A", "email": "a@b.co", "password": "lettersonly"},
        {"name": "   ", "email": "a@b.co", "password": "s3cure-pass"},
    ]
    for body in bad:
        assert c.post("/api/auth/register", json=body).status_code == 422, body
    register(c, email="dup@example.com")
    r = c.post("/api/auth/register", json={"name": "B", "email": "DUP@example.com", "password": "an0ther-pass"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "email_taken"


def test_wrong_password_and_lockout(anon_client):
    c = anon_client
    register(c, email="lock@example.com")
    c.post("/api/auth/logout")
    for _ in range(5):
        r = c.post("/api/auth/login", json={"email": "lock@example.com", "password": "nope-nope1"})
        assert r.status_code == 401 and r.json()["detail"]["code"] == "invalid_credentials"
    r = c.post("/api/auth/login", json={"email": "lock@example.com", "password": "s3cure-pass"})
    assert r.status_code == 429  # locked even with the right password
    unknown = c.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever1"})
    assert unknown.status_code == 401  # same response as a wrong password


def test_analysis_requires_login(anon_client, sample_bytes):
    c = anon_client
    assert _predict(c, sample_bytes["normal_01"]).status_code == 401
    assert c.post("/api/validate", files={"file": ("x.png", sample_bytes["normal_01"], "image/png")}).status_code == 401
    assert c.get("/api/history").status_code == 401
    assert c.delete("/api/history").status_code == 401
    # Public endpoints stay public.
    assert c.get("/api/health").status_code == 200
    assert c.get("/api/samples").status_code == 200


def test_history_is_private_per_account(settings, sample_bytes):
    app = create_app(settings)
    with TestClient(app) as alice, TestClient(app) as bob:
        register(alice, email="alice@example.com", name="Alice")
        register(bob, email="bob@example.com", name="Bob")

        a_id = _predict(alice, sample_bytes["viral_01"], source_name="alice-scan").json()["id"]
        _predict(alice, sample_bytes["normal_01"])
        b_id = _predict(bob, sample_bytes["bacterial_01"], source_name="bob-scan").json()["id"]

        assert {h["source_name"] for h in alice.get("/api/history").json()} >= {"alice-scan"}
        assert len(alice.get("/api/history").json()) == 2
        assert [h["source_name"] for h in bob.get("/api/history").json()] == ["bob-scan"]

        # Bob cannot read or delete Alice's analysis even with its ID.
        assert bob.get(f"/api/history/{a_id}").status_code == 404
        assert bob.delete(f"/api/history/{a_id}").status_code == 404
        assert alice.get(f"/api/history/{a_id}").status_code == 200

        # "Delete all" only clears the caller's own history.
        assert bob.delete("/api/history").status_code == 204
        assert bob.get("/api/history").json() == []
        assert len(alice.get("/api/history").json()) == 2
        assert alice.get(f"/api/history/{b_id}").status_code == 404
