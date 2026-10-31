import pytest

from app.application.dto.edit_region import EditRegionRequest
from app.application.use_cases.confirm_edit import ConfirmEditUseCase, StalePreview
from app.application.use_cases.discard_edit import DiscardEditUseCase
from app.application.use_cases.edit_region import EditRegionUseCase
from app.application.use_cases.get_current_image import GetCurrentImageUseCase
from app.application.use_cases.get_edit_history import GetEditHistoryUseCase
from app.application.use_cases.undo_last_edit import NothingToUndo, UndoLastEditUseCase
from app.domain.entities.edit import EditStatus
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.region_type import RegionType
from tests.unit.application.fakes import (
    FakeImageCompositor,
    FakeImageEditor,
    FakeImageRepository,
    FakeImageSegmenter,
    FakeImageStorage,
)
from tests.unit.application.test_edit_region import _setup_image_with_region


class _World:
    def __init__(self) -> None:
        self.storage = FakeImageStorage()
        self.repo = FakeImageRepository()
        self.uploaded, self.region = _setup_image_with_region(self.storage, self.repo)
        self.image_id = self.uploaded.image_id
        self._edit = EditRegionUseCase(
            self.repo,
            self.storage,
            FakeImageSegmenter(),
            FakeImageEditor(),
            FakeImageCompositor(),
        )
        self.confirm = ConfirmEditUseCase(self.repo, self.storage)
        self.undo = UndoLastEditUseCase(self.repo, self.storage)
        self.history = GetEditHistoryUseCase(self.repo, self.storage)
        self.current = GetCurrentImageUseCase(self.repo, self.storage)

    def preview(self, operation: EditOperation):
        return self._edit.execute(
            EditRegionRequest(image_id=self.image_id, region_id=self.region.id, operation=operation)
        )

    def apply(self, operation: EditOperation):
        result = self.preview(operation)
        self.confirm.execute(result.edit_id)
        return self.repo.get_edit(result.edit_id)

    def current_ref(self) -> str:
        return self.repo.get_edit_session_for_image(self.image_id).current_image_ref


def test_history_lists_only_applied_edits_in_order():
    world = _World()
    wave = world.apply(EditOperation.WAVE)
    discarded = world.preview(EditOperation.FIST)
    DiscardEditUseCase(world.repo).execute(discarded.edit_id)
    peace = world.apply(EditOperation.PEACE_SIGN)
    world.preview(EditOperation.THUMBS_UP)  # pending preview, not applied

    history = world.history.execute(world.image_id)

    assert [e.edit_id for e in history.entries] == [wave.id, peace.id]
    assert history.entries[0].region_type is RegionType.RIGHT_HAND
    assert history.can_undo
    assert history.current_url == world.storage.url_for(peace.final_ref)


def test_undo_steps_back_one_edit_at_a_time_down_to_the_original():
    world = _World()
    original_ref = world.current_ref()
    wave = world.apply(EditOperation.WAVE)
    peace = world.apply(EditOperation.PEACE_SIGN)

    first = world.undo.execute(world.image_id)
    assert first.reverted_edit_id == peace.id
    assert world.current_ref() == wave.final_ref

    world.undo.execute(world.image_id)
    assert world.current_ref() == original_ref

    history = world.history.execute(world.image_id)
    assert [e.status for e in history.entries] == [EditStatus.REVERTED, EditStatus.REVERTED]
    assert not history.can_undo
    with pytest.raises(NothingToUndo):
        world.undo.execute(world.image_id)


def test_a_new_edit_after_undo_builds_on_the_restored_image():
    world = _World()
    wave = world.apply(EditOperation.WAVE)
    world.undo.execute(world.image_id)

    fist = world.apply(EditOperation.FIST)

    assert fist.source_image_ref == wave.source_image_ref
    # undoing now reverts the fist, not the already-reverted wave
    assert world.undo.execute(world.image_id).reverted_edit_id == fist.id


def test_a_preview_made_before_an_undo_can_no_longer_be_accepted():
    world = _World()
    world.apply(EditOperation.WAVE)
    stale = world.preview(EditOperation.PEACE_SIGN)  # made on top of the wave
    world.undo.execute(world.image_id)

    with pytest.raises(StalePreview):
        world.confirm.execute(stale.edit_id)
    assert world.repo.get_edit(stale.edit_id).status == EditStatus.PREVIEW_READY


def test_download_is_the_current_image_named_after_the_upload():
    world = _World()
    original = world.current.execute(world.image_id)
    assert original.filename == "hand.png"

    wave = world.apply(EditOperation.WAVE)
    edited = world.current.execute(world.image_id)

    assert edited.filename == "hand-edited.png"
    assert edited.data == world.storage.load(wave.final_ref)
