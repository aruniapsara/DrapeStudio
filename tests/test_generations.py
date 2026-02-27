"""Tests for generation endpoints."""

import uuid


def _make_generation_body(idempotency_key=None):
    """Helper to create a valid generation request body."""
    return {
        "idempotency_key": idempotency_key or str(uuid.uuid4()),
        "garment_images": ["local://uploads/test-session/front.jpg"],
        "model_params": {
            "age_range": "25-34",
            "gender_presentation": "feminine",
            "skin_tone": "4",
            "body_mode": "simple",
            "body_type": "curvy",
        },
        "scene": {
            "environment": "studio_white",
            "pose_preset": "front_standing",
            "framing": "full_body",
        },
        "output": {"count": 3, "resolution": "high"},
    }


def test_create_generation_returns_201(client):
    """POST /v1/generations returns 201 with an id and queued status."""
    body = _make_generation_body()
    resp = client.post("/v1/generations", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["id"].startswith("gen_")
    assert data["status"] == "queued"


def test_get_generation_status(client):
    """GET /v1/generations/{id} returns the status."""
    body = _make_generation_body()
    create_resp = client.post("/v1/generations", json=body)
    gen_id = create_resp.json()["id"]

    status_resp = client.get(f"/v1/generations/{gen_id}")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["id"] == gen_id
    assert data["status"] == "queued"
    assert data["prompt_template_version"] == "v0.1"


def test_get_generation_not_found(client):
    """GET /v1/generations/{id} returns 404 for unknown ID."""
    resp = client.get("/v1/generations/gen_nonexistent")
    assert resp.status_code == 404


def test_idempotency_key_prevents_duplicate(client):
    """Same idempotency key with same params returns existing generation."""
    key = str(uuid.uuid4())
    body = _make_generation_body(idempotency_key=key)

    resp1 = client.post("/v1/generations", json=body)
    assert resp1.status_code == 201
    gen_id = resp1.json()["id"]

    # Second request with same key and params
    resp2 = client.post("/v1/generations", json=body)
    # Should return 200 with same ID (idempotent)
    assert resp2.status_code in (200, 201)
    assert resp2.json()["id"] == gen_id


def test_idempotency_key_conflict(client):
    """Same idempotency key with different params returns 409."""
    key = str(uuid.uuid4())
    body1 = _make_generation_body(idempotency_key=key)

    resp1 = client.post("/v1/generations", json=body1)
    assert resp1.status_code == 201

    # Second request with same key but different params
    body2 = _make_generation_body(idempotency_key=key)
    body2["model_params"]["age_range"] = "45+"  # Different params

    resp2 = client.post("/v1/generations", json=body2)
    assert resp2.status_code == 409


def test_get_outputs_for_queued_generation(client):
    """GET /v1/generations/{id}/outputs returns empty outputs when queued."""
    body = _make_generation_body()
    create_resp = client.post("/v1/generations", json=body)
    gen_id = create_resp.json()["id"]

    outputs_resp = client.get(f"/v1/generations/{gen_id}/outputs")
    assert outputs_resp.status_code == 200
    data = outputs_resp.json()
    assert data["status"] == "queued"
    assert data["outputs"] == []


def test_status_partial_returns_html(client):
    """GET /v1/generations/{id}/status-partial returns HTML fragment."""
    body = _make_generation_body()
    create_resp = client.post("/v1/generations", json=body)
    gen_id = create_resp.json()["id"]

    partial_resp = client.get(f"/v1/generations/{gen_id}/status-partial")
    assert partial_resp.status_code == 200
    assert "text/html" in partial_resp.headers["content-type"]
    assert "status-container" in partial_resp.text


def test_reject_too_many_images(client):
    """POST /v1/generations rejects more than 5 images."""
    body = _make_generation_body()
    body["garment_images"] = [f"local://uploads/test/img{i}.jpg" for i in range(6)]

    resp = client.post("/v1/generations", json=body)
    assert resp.status_code == 400 or resp.status_code == 422


def test_reject_no_images(client):
    """POST /v1/generations rejects empty image list."""
    body = _make_generation_body()
    body["garment_images"] = []

    resp = client.post("/v1/generations", json=body)
    assert resp.status_code == 400 or resp.status_code == 422
