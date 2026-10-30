import pytest

from app.application.dto.edit_region import EditRegionRequest
from app.application.dto.upload_image import UploadImageRequest
from app.application.use_cases.confirm_edit import ConfirmEditUseCase
from app.application.use_cases.discard_edit import DiscardEditUseCase
from app.application.use_cases.edit_region import EditRegionUseCase
from app.application.use_cases.upload_image import UploadImageUseCase
from app.domain.entities.edit import EditStatus
from app.domain.entities.region import DetectedRegion
from app.domain.services.region_operation_rules import OperationNotAllowedForRegion
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.region_type import RegionType
from tests.unit.application.fakes import (
    FakeImageCompositor,
    FakeImageEditor,
    FakeImageRepository,
    FakeImageSegmenter,
    FakeImageStorage,
)


def _setup_image_with_region(storage, repo, region_type=RegionType.RIGHT_HAND):
    uploaded = UploadImageUseCase(storage, repo).execute(
        UploadImageRequest(
            file_bytes=b"original-bytes",
            original_filename="hand.png",
            content_type="image/png",
            width=800,
            height=600,
        )
    )
    region = DetectedRegion.new(
        image_id=uploaded.image_id,
        region_type=region_type,
        bounding_box=BoundingBox(x_min=400, y_min=400, x_max=500, y_max=500),
        confidence=0.9,
    )
    repo.save_regions([region])
    return uploaded, region


def test_edit_region_produces_a_preview_and_does_not_touch_the_session_yet():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded, region = _setup_image_with_region(storage, repo)

    use_case = EditRegionUseCase(
        repo, storage, FakeImageSegmenter(), FakeImageEditor(), FakeImageCompositor()
    )
    result = use_case.execute(
        EditRegionRequest(
            image_id=uploaded.image_id, region_id=region.id, operation=EditOperation.PEACE_SIGN
        )
    )

    assert result.status == EditStatus.PREVIEW_READY
    assert result.preview_url is not None

    session = repo.get_edit_session_for_image(uploaded.image_id)
    original_image = repo.get_image(uploaded.image_id)
    # confirming hasn't happened yet -> session still points at the original
    assert session.current_image_ref == original_image.storage_ref

    edit = repo.get_edit(result.edit_id)
    assert edit.status == EditStatus.PREVIEW_READY
    assert edit.source_image_ref == original_image.storage_ref


def test_edit_region_rejects_an_operation_invalid_for_the_region():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded, region = _setup_image_with_region(storage, repo, region_type=RegionType.FACE)

    use_case = EditRegionUseCase(
        repo, storage, FakeImageSegmenter(), FakeImageEditor(), FakeImageCompositor()
    )
    with pytest.raises(OperationNotAllowedForRegion):
        use_case.execute(
            EditRegionRequest(
                image_id=uploaded.image_id, region_id=region.id, operation=EditOperation.PEACE_SIGN
            )
        )


def test_edit_region_records_failure_instead_of_raising_when_the_editor_fails():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded, region = _setup_image_with_region(storage, repo)

    use_case = EditRegionUseCase(
        repo, storage, FakeImageSegmenter(), FakeImageEditor(should_fail=True), FakeImageCompositor()
    )
    result = use_case.execute(
        EditRegionRequest(
            image_id=uploaded.image_id, region_id=region.id, operation=EditOperation.FIST
        )
    )

    assert result.status == EditStatus.FAILED
    assert result.preview_url is None
    assert result.error_message == "fake editor failure"


def test_confirming_an_edit_advances_the_session_so_the_next_edit_builds_on_it():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded, region = _setup_image_with_region(storage, repo)

    edit_use_case = EditRegionUseCase(
        repo, storage, FakeImageSegmenter(), FakeImageEditor(), FakeImageCompositor()
    )
    confirm_use_case = ConfirmEditUseCase(repo, storage)

    first = edit_use_case.execute(
        EditRegionRequest(
            image_id=uploaded.image_id, region_id=region.id, operation=EditOperation.WAVE
        )
    )
    confirm_result = confirm_use_case.execute(first.edit_id)
    assert confirm_result.status == EditStatus.CONFIRMED

    session = repo.get_edit_session_for_image(uploaded.image_id)
    first_edit = repo.get_edit(first.edit_id)
    assert session.current_image_ref == first_edit.final_ref
    assert session.current_image_ref != repo.get_image(uploaded.image_id).storage_ref

    # a second edit now applies on top of the confirmed result, not the original
    second = edit_use_case.execute(
        EditRegionRequest(
            image_id=uploaded.image_id, region_id=region.id, operation=EditOperation.PEACE_SIGN
        )
    )
    second_edit = repo.get_edit(second.edit_id)
    assert second_edit.source_image_ref == first_edit.final_ref


def test_discarding_an_edit_leaves_the_session_untouched():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded, region = _setup_image_with_region(storage, repo)

    edit_use_case = EditRegionUseCase(
        repo, storage, FakeImageSegmenter(), FakeImageEditor(), FakeImageCompositor()
    )
    discard_use_case = DiscardEditUseCase(repo)

    result = edit_use_case.execute(
        EditRegionRequest(
            image_id=uploaded.image_id, region_id=region.id, operation=EditOperation.THUMBS_UP
        )
    )
    discard_result = discard_use_case.execute(result.edit_id)
    assert discard_result.status == EditStatus.DISCARDED

    session = repo.get_edit_session_for_image(uploaded.image_id)
    assert session.current_image_ref == repo.get_image(uploaded.image_id).storage_ref


def test_mask_is_only_segmented_once_and_then_reused():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded, region = _setup_image_with_region(storage, repo)

    segment_calls = {"count": 0}

    class CountingSegmenter(FakeImageSegmenter):
        def segment(self, image_bytes, region):  # noqa: ANN001
            segment_calls["count"] += 1
            return super().segment(image_bytes, region)

    edit_use_case = EditRegionUseCase(
        repo, storage, CountingSegmenter(), FakeImageEditor(), FakeImageCompositor()
    )
    edit_use_case.execute(
        EditRegionRequest(
            image_id=uploaded.image_id, region_id=region.id, operation=EditOperation.WAVE
        )
    )
    edit_use_case.execute(
        EditRegionRequest(
            image_id=uploaded.image_id, region_id=region.id, operation=EditOperation.FIST
        )
    )

    assert segment_calls["count"] == 1


@pytest.mark.parametrize(
    ("region_type", "operation", "expected_grow_px"),
    [
        # a gesture can reach past the original outline...
        (RegionType.RIGHT_HAND, EditOperation.PEACE_SIGN, 40),
        # ...a garment can't, so its margin stays tight
        (RegionType.TORSO, EditOperation.RED_SHIRT, 16),
    ],
)
def test_mask_grow_depends_on_the_region_type(region_type, operation, expected_grow_px):
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded, region = _setup_image_with_region(storage, repo, region_type=region_type)

    grow_px_seen = []

    class RecordingCompositor(FakeImageCompositor):
        def composite(self, *, grow_px, **kwargs):
            grow_px_seen.append(grow_px)
            return super().composite(grow_px=grow_px, **kwargs)

    EditRegionUseCase(
        repo, storage, FakeImageSegmenter(), FakeImageEditor(), RecordingCompositor()
    ).execute(
        EditRegionRequest(image_id=uploaded.image_id, region_id=region.id, operation=operation)
    )

    assert grow_px_seen == [expected_grow_px]
