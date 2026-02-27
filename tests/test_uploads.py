"""Tests for upload endpoints."""

import io


def test_sign_url_returns_valid_structure(client):
    """POST /v1/uploads/sign returns proper upload info."""
    resp = client.post(
        "/v1/uploads/sign",
        json={
            "files": [
                {"kind": "image", "filename": "front.jpg", "content_type": "image/jpeg"}
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "uploads" in data
    assert len(data["uploads"]) == 1
    assert data["uploads"][0]["filename"] == "front.jpg"
    assert "upload_url" in data["uploads"][0]
    assert "file_url" in data["uploads"][0]
    assert data["expires_in_seconds"] == 900


def test_sign_url_multiple_files(client):
    """POST /v1/uploads/sign handles multiple files."""
    resp = client.post(
        "/v1/uploads/sign",
        json={
            "files": [
                {"kind": "image", "filename": "front.jpg", "content_type": "image/jpeg"},
                {"kind": "image", "filename": "back.png", "content_type": "image/png"},
                {"kind": "image", "filename": "detail.webp", "content_type": "image/webp"},
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["uploads"]) == 3


def test_sign_url_rejects_too_many_files(client):
    """POST /v1/uploads/sign rejects more than 5 files."""
    files = [
        {"kind": "image", "filename": f"img{i}.jpg", "content_type": "image/jpeg"}
        for i in range(6)
    ]
    resp = client.post("/v1/uploads/sign", json={"files": files})
    assert resp.status_code == 400


def test_sign_url_rejects_empty_files(client):
    """POST /v1/uploads/sign rejects empty file list."""
    resp = client.post("/v1/uploads/sign", json={"files": []})
    assert resp.status_code == 400


def test_sign_url_rejects_bad_content_type(client):
    """POST /v1/uploads/sign rejects unsupported file types."""
    resp = client.post(
        "/v1/uploads/sign",
        json={
            "files": [
                {"kind": "image", "filename": "doc.pdf", "content_type": "application/pdf"}
            ]
        },
    )
    assert resp.status_code == 400


def test_direct_upload_saves_file(client, sample_image_bytes):
    """Direct upload endpoint saves file to local storage."""
    resp = client.post(
        "/v1/uploads/direct/test-session/test.jpg",
        files={"file": ("test.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "file_url" in data


def test_direct_upload_rejects_bad_type(client):
    """Direct upload rejects non-image files."""
    resp = client.post(
        "/v1/uploads/direct/test-session/doc.pdf",
        files={"file": ("doc.pdf", io.BytesIO(b"fake pdf"), "application/pdf")},
    )
    assert resp.status_code == 400
