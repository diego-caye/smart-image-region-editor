import pytest

from app.application.dto.edit_progress import EditStage
from app.application.dto.edit_region import EditRegionRequest
from app.application.dto.upload_image import UploadImageRequest
from app.application.use_cases.confirm_edit import ConfirmEditUseCase
from app.application.use_cases.discard_edit import DiscardEditUseCase
from app.application.use_cases.edit_region import EditRegionUseCase
from app.application.use_cases.upload_image import UploadImageUseCase
from app.domain.entities.edit import EditStatus
from app.domain.entities.region import DetectedRegion
from app.domain.services.operation_options import InvalidOperationOptions
from app.domain.services.region_operation_rules import OperationNotAllowedForRegion
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor
from app.domain.value_objects.mask_scope import MaskScope
from app.domain.value_objects.region_type import RegionType
from tests.unit.application.fakes import (
    FakeImageCompositor,
    FakeImageEditor,
    FakeImageRepository,
    FakeImageSegmenter,
    FakeImageStorage,
    RecordingProgressTracker,
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
        def segment(self, image_bytes, region, **kwargs):
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
    ("region_type", "operation", "color", "expected_grow_px"),
    [
        # a gesture can reach past the original outline...
        (RegionType.RIGHT_HAND, EditOperation.PEACE_SIGN, None, 40),
        # ...a garment can't, so its margin stays tight
        (RegionType.TORSO, EditOperation.SHIRT_COLOR, GarmentColor.RED, 16),
    ],
)
def test_mask_grow_depends_on_the_region_type(region_type, operation, color, expected_grow_px):
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
        EditRegionRequest(
            image_id=uploaded.image_id, region_id=region.id, operation=operation, color=color
        )
    )

    assert grow_px_seen == [expected_grow_px]


def test_progress_is_reported_through_every_stage_when_a_progress_id_is_given():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded, region = _setup_image_with_region(storage, repo)
    tracker = RecordingProgressTracker()

    EditRegionUseCase(
        repo,
        storage,
        FakeImageSegmenter(),
        FakeImageEditor(),
        FakeImageCompositor(),
        progress_tracker=tracker,
    ).execute(
        EditRegionRequest(
            image_id=uploaded.image_id,
            region_id=region.id,
            operation=EditOperation.WAVE,
            progress_id="p-1",
        )
    )

    stages = [progress.stage for _, progress in tracker.reports]
    assert stages == [
        EditStage.SEGMENTING,
        EditStage.READING_INSTRUCTION,
        EditStage.LOADING_MODEL,
        EditStage.GENERATING,
        EditStage.GENERATING,
        EditStage.DECODING,
        EditStage.COMPOSITING,
        EditStage.DONE,
    ]
    assert {progress_id for progress_id, _ in tracker.reports} == {"p-1"}
    assert tracker.get("p-1").fraction == 1.0


def test_without_a_progress_id_nothing_is_reported():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded, region = _setup_image_with_region(storage, repo)
    tracker = RecordingProgressTracker()

    EditRegionUseCase(
        repo,
        storage,
        FakeImageSegmenter(),
        FakeImageEditor(),
        FakeImageCompositor(),
        progress_tracker=tracker,
    ).execute(
        EditRegionRequest(image_id=uploaded.image_id, region_id=region.id, operation=EditOperation.WAVE)
    )

    assert tracker.reports == []


def test_the_chosen_color_reaches_the_editor_and_is_kept_on_the_edit():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded, region = _setup_image_with_region(storage, repo, region_type=RegionType.TORSO)

    result = EditRegionUseCase(
        repo, storage, FakeImageSegmenter(), FakeImageEditor(), FakeImageCompositor()
    ).execute(
        EditRegionRequest(
            image_id=uploaded.image_id,
            region_id=region.id,
            operation=EditOperation.HOODIE,
            color=GarmentColor.GREEN,
        )
    )

    edit = repo.get_edit(result.edit_id)
    assert edit.color is GarmentColor.GREEN
    assert edit.model_metadata["color"] is GarmentColor.GREEN


def test_a_garment_without_its_color_is_rejected_before_anything_runs():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded, region = _setup_image_with_region(storage, repo, region_type=RegionType.TORSO)

    with pytest.raises(InvalidOperationOptions):
        EditRegionUseCase(
            repo, storage, FakeImageSegmenter(), FakeImageEditor(), FakeImageCompositor()
        ).execute(
            EditRegionRequest(
                image_id=uploaded.image_id, region_id=region.id, operation=EditOperation.HOODIE
            )
        )
    assert repo.edits == {}


def test_inner_and_whole_region_masks_are_segmented_once_each_and_kept_apart():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded, region = _setup_image_with_region(storage, repo, region_type=RegionType.TORSO)
    segmenter = FakeImageSegmenter()
    use_case = EditRegionUseCase(
        repo, storage, segmenter, FakeImageEditor(), FakeImageCompositor()
    )

    def edit(operation):
        use_case.execute(
            EditRegionRequest(
                image_id=uploaded.image_id,
                region_id=region.id,
                operation=operation,
                color=GarmentColor.RED,
            )
        )

    edit(EditOperation.HOODIE)  # inner layer
    edit(EditOperation.JACKET)  # whole region
    edit(EditOperation.T_SHIRT)  # inner layer again: cached
    edit(EditOperation.JACKET)  # whole region again: cached

    assert segmenter.scopes_seen == [MaskScope.INNER_LAYER, MaskScope.WHOLE_REGION]
    masks = repo.get_masks_for_region(region.id)
    assert {m.scope for m in masks} == {MaskScope.INNER_LAYER, MaskScope.WHOLE_REGION}
    # the region links to its whole-region mask, never the inner one
    linked = repo.get_mask(repo.get_region(region.id).mask_id)
    assert linked.scope is MaskScope.WHOLE_REGION

