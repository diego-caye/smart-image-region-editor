"""Integration test for the edit/confirm/discard endpoints. Detector/
segmenter/editor are overridden with the same in-memory fakes the
application-level unit tests use (tests/unit/application/fakes.py); the
REAL PillowImageCompositor is used as-is (fast, pure Pillow, no GPU) for
genuine pixel-level coverage of the actual compositing math. Storage/DB are
isolated to tmp_path exactly like test_images_api.py.
"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image as PILImage
from sqlmodel import Session

from app.adapters.http.dependencies import (
    get_edit_progress_tracker,
    get_image_compositor,
    get_image_detector,
    get_image_editor,
    get_image_segmenter,
    get_image_storage,
    get_session,
)
from app.adapters.imaging.pillow_image_compositor import PillowImageCompositor
from app.domain.entities.region import DetectedRegion
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.region_type import RegionType
from app.infrastructure.config.settings import Settings
from app.infrastructure.database.engine import init_db, make_engine
from app.infrastructure.progress.in_memory_edit_progress_tracker import InMemoryEditProgressTracker
from app.infrastructure.storage.filesystem_image_storage import FilesystemImageStorage
from app.main import app
from tests.unit.application.fakes import FakeImageDetector, FakeImageEditor, FakeImageSegmenter


def _client(tmp_path, *, editor_should_fail: bool = False) -> TestClient:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}", storage_root=tmp_path / "images"
    )
    engine = make_engine(settings)
    init_db(engine)
    storage = FilesystemImageStorage(settings.storage_root, static_url_prefix=settings.static_url_prefix)

    canned_region = DetectedRegion.new(
        image_id=None,  # AnalyzeImageUseCase re-stamps image_id itself
        region_type=RegionType.RIGHT_HAND,
        bounding_box=BoundingBox(x_min=10, y_min=10, x_max=30, y_max=30),
        confidence=0.9,
    )

    app.dependency_overrides[get_image_storage] = lambda: storage
    app.dependency_overrides[get_image_detector] = lambda: FakeImageDetector([canned_region])
    app.dependency_overrides[get_image_segmenter] = lambda: FakeImageSegmenter(
        mask_bytes=_mask_png((64, 48), (5, 5, 35, 35))
    )
    app.dependency_overrides[get_image_editor] = lambda: FakeImageEditor(
        should_fail=editor_should_fail
    )
    app.dependency_overrides[get_image_compositor] = lambda: PillowImageCompositor()
    tracker = InMemoryEditProgressTracker()
    app.dependency_overrides[get_edit_progress_tracker] = lambda: tracker

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _png_bytes(size=(64, 48)) -> bytes:
    buffer = io.BytesIO()
    PILImage.new("RGB", size, color="red").save(buffer, format="PNG")
    return buffer.getvalue()


def _mask_png(size, white_box) -> bytes:
    mask = PILImage.new("L", size, color=0)
    mask.paste(255, white_box)
    buffer = io.BytesIO()
    mask.save(buffer, format="PNG")
    return buffer.getvalue()


def _upload_and_analyze(client: TestClient) -> tuple[str, str]:
    upload = client.post("/images", files={"file": ("photo.png", _png_bytes(), "image/png")})
    image_id = upload.json()["image_id"]
    analyze = client.post(f"/images/{image_id}/analyze")
    region_id = analyze.json()["regions"][0]["region_id"]
    return image_id, region_id


def test_create_edit_returns_a_preview(tmp_path):
    client = _client(tmp_path)
    image_id, region_id = _upload_and_analyze(client)

    response = client.post(
        f"/images/{image_id}/edits", json={"region_id": region_id, "operation": "peace_sign"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "preview_ready"
    assert body["preview_url"] is not None

    preview_response = client.get(body["preview_url"])
    assert preview_response.status_code == 200


def test_create_edit_rejects_an_operation_invalid_for_the_region(tmp_path):
    client = _client(tmp_path)
    image_id, region_id = _upload_and_analyze(client)  # region_type is right_hand

    response = client.post(
        f"/images/{image_id}/edits", json={"region_id": region_id, "operation": "smile"}
    )

    assert response.status_code == 422


def test_create_edit_404s_for_an_unknown_image(tmp_path):
    client = _client(tmp_path)
    _, region_id = _upload_and_analyze(client)

    from uuid import uuid4

    response = client.post(
        f"/images/{uuid4()}/edits", json={"region_id": region_id, "operation": "peace_sign"}
    )
    assert response.status_code == 404


def test_edit_records_failure_without_a_bare_500(tmp_path):
    client = _client(tmp_path, editor_should_fail=True)
    image_id, region_id = _upload_and_analyze(client)

    response = client.post(
        f"/images/{image_id}/edits", json={"region_id": region_id, "operation": "peace_sign"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["preview_url"] is None
    assert body["error_message"]


def test_confirm_then_discard_lifecycle(tmp_path):
    client = _client(tmp_path)
    image_id, region_id = _upload_and_analyze(client)

    edit = client.post(
        f"/images/{image_id}/edits", json={"region_id": region_id, "operation": "fist"}
    ).json()

    confirm_response = client.post(f"/edits/{edit['edit_id']}/confirm")
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"

    # a confirmed edit can no longer be discarded
    discard_response = client.post(f"/edits/{edit['edit_id']}/discard")
    assert discard_response.status_code == 409


def test_discarding_a_preview_works_and_a_second_edit_still_applies_to_the_original(tmp_path):
    client = _client(tmp_path)
    image_id, region_id = _upload_and_analyze(client)

    first = client.post(
        f"/images/{image_id}/edits", json={"region_id": region_id, "operation": "wave"}
    ).json()
    discard_response = client.post(f"/edits/{first['edit_id']}/discard")
    assert discard_response.status_code == 200
    assert discard_response.json()["status"] == "discarded"

    second = client.post(
        f"/images/{image_id}/edits", json={"region_id": region_id, "operation": "fist"}
    ).json()
    assert second["status"] == "preview_ready"


def test_confirm_unknown_edit_404s(tmp_path):
    client = _client(tmp_path)
    from uuid import uuid4

    response = client.post(f"/edits/{uuid4()}/confirm")
    assert response.status_code == 404


def test_progress_can_be_read_by_the_id_the_client_chose(tmp_path):
    client = _client(tmp_path)
    image_id, region_id = _upload_and_analyze(client)

    assert client.get("/edits/progress/my-edit-1").status_code == 404  # nothing reported yet

    client.post(
        f"/images/{image_id}/edits",
        json={"region_id": region_id, "operation": "peace_sign", "progress_id": "my-edit-1"},
    )

    progress = client.get("/edits/progress/my-edit-1")
    assert progress.status_code == 200
    assert progress.json() == {"stage": "done", "fraction": 1.0, "step": None, "steps": None}


def test_progress_id_must_be_a_simple_token(tmp_path):
    client = _client(tmp_path)
    image_id, region_id = _upload_and_analyze(client)

    response = client.post(
        f"/images/{image_id}/edits",
        json={"region_id": region_id, "operation": "peace_sign", "progress_id": "../../etc"},
    )

    assert response.status_code == 422
