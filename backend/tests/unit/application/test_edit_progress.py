import pytest

from app.application.dto.edit_progress import EditProgress, EditStage
from app.domain.ports.image_editor import EditorProgress, EditorStage


def test_fraction_only_moves_forward_across_a_full_run():
    run = [
        EditProgress.at(EditStage.SEGMENTING),
        EditProgress.at(EditStage.READING_INSTRUCTION),
        EditProgress.at(EditStage.LOADING_MODEL),
        *(EditProgress.at(EditStage.GENERATING, step, 4) for step in range(1, 5)),
        EditProgress.at(EditStage.DECODING),
        EditProgress.at(EditStage.COMPOSITING),
        EditProgress.at(EditStage.DONE),
    ]
    fractions = [p.fraction for p in run]
    assert fractions == sorted(fractions)
    assert len(set(fractions)) == len(fractions)
    assert fractions[-1] == 1.0


def test_generating_spans_between_loading_and_decoding():
    loading = EditProgress.at(EditStage.LOADING_MODEL).fraction
    decoding = EditProgress.at(EditStage.DECODING).fraction
    last_step = EditProgress.at(EditStage.GENERATING, 4, 4).fraction
    assert loading < EditProgress.at(EditStage.GENERATING, 1, 4).fraction < last_step < decoding


@pytest.mark.parametrize("editor_stage", list(EditorStage))
def test_every_editor_stage_maps_to_a_pipeline_stage(editor_stage):
    progress = EditProgress.from_editor(EditorProgress(editor_stage, step=1, steps=4))
    assert progress.stage.value == editor_stage.value
