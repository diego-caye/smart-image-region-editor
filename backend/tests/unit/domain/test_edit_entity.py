from uuid import uuid4

import pytest

from app.domain.entities.edit import Edit, EditStatus, InvalidEditTransition
from app.domain.value_objects.edit_operation import EditOperation


def _new_edit() -> Edit:
    return Edit.new(
        session_id=uuid4(),
        region_id=uuid4(),
        operation=EditOperation.PEACE_SIGN,
        source_image_ref="images/original.png",
    )


def test_new_edit_starts_pending():
    edit = _new_edit()
    assert edit.status == EditStatus.PENDING


def test_full_happy_path_transitions():
    edit = _new_edit()
    edit.mark_processing()
    assert edit.status == EditStatus.PROCESSING

    edit.mark_preview_ready("images/preview.png", seed=7, model_metadata={"steps": 4})
    assert edit.status == EditStatus.PREVIEW_READY
    assert edit.preview_ref == "images/preview.png"
    assert edit.seed == 7

    edit.confirm()
    assert edit.status == EditStatus.CONFIRMED
    assert edit.final_ref == "images/preview.png"


def test_discard_from_preview_ready():
    edit = _new_edit()
    edit.mark_processing()
    edit.mark_preview_ready("images/preview.png")
    edit.discard()
    assert edit.status == EditStatus.DISCARDED


def test_cannot_confirm_before_preview_ready():
    edit = _new_edit()
    with pytest.raises(InvalidEditTransition):
        edit.confirm()


def test_cannot_discard_a_confirmed_edit():
    edit = _new_edit()
    edit.mark_processing()
    edit.mark_preview_ready("images/preview.png")
    edit.confirm()
    with pytest.raises(InvalidEditTransition):
        edit.discard()


def test_failed_edit_can_be_discarded():
    edit = _new_edit()
    edit.mark_processing()
    edit.mark_failed("ComfyUI timed out")
    assert edit.status == EditStatus.FAILED
    edit.discard()
    assert edit.status == EditStatus.DISCARDED
