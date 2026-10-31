"""API-level integration test using FastAPI's TestClient. Storage and the DB
are overridden per-test to an isolated tmp_path via dependency_overrides —
the standard FastAPI pattern — so tests never touch the real backend/data/.
"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image as PILImage
from sqlmodel import Session

from app.adapters.http.dependencies import get_image_storage, get_session
from app.infrastructure.config.settings import Settings
from app.infrastructure.database.engine import init_db, make_engine
from app.infrastructure.storage.filesystem_image_storage import FilesystemImageStorage
from app.main import app


def _client(tmp_path) -> TestClient:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        storage_root=tmp_path / "images",
    )
    engine = make_engine(settings)
    init_db(engine)
    storage = FilesystemImageStorage(settings.storage_root, static_url_prefix=settings.static_url_prefix)

    app.dependency_overrides[get_image_storage] = lambda: storage

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _png_bytes(size=(64, 48)) -> bytes:
    buffer = io.BytesIO()
    PILImage.new("RGB", size, color="red").save(buffer, format="PNG")
    return buffer.getvalue()


def test_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_image_returns_dimensions_and_a_loadable_url(tmp_path):
    client = _client(tmp_path)
    response = client.post(
        "/images", files={"file": ("selfie.png", _png_bytes((64, 48)), "image/png")}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["width"] == 64
    assert body["height"] == 48
    assert body["url"].startswith("/static/original/")

    # the static mount actually serves the bytes back
    image_response = client.get(body["url"])
    assert image_response.status_code == 200
    assert image_response.content == _png_bytes((64, 48))


def test_upload_rejects_non_image_payload(tmp_path):
    client = _client(tmp_path)
    response = client.post(
        "/images", files={"file": ("notes.txt", b"hello world", "text/plain")}
    )
    assert response.status_code == 400


def test_list_operations_for_right_hand():
    client = TestClient(app)
    response = client.get("/regions/right_hand/operations")
    assert response.status_code == 200
    body = response.json()
    operations = {op["operation"] for op in body["operations"]}
    assert "peace_sign" in operations
    peace_sign = next(op for op in body["operations"] if op["operation"] == "peace_sign")
    assert peace_sign["emoji"] == "✌️"
    assert peace_sign["colors"] == []


def test_garments_list_the_palette_to_pick_a_color_from():
    client = TestClient(app)
    body = client.get("/regions/torso/operations").json()
    hoodie = next(op for op in body["operations"] if op["operation"] == "hoodie")
    assert hoodie["colors"] == ["red", "blue", "green", "yellow", "black", "white", "gray"]


def test_list_operations_rejects_unknown_region_type():
    client = TestClient(app)
    response = client.get("/regions/not_a_region/operations")
    assert response.status_code == 422
