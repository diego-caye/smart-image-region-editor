from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.ports.image_editor import EditorProgress, EditorStage


class EditStage(StrEnum):
    """The whole edit pipeline, as shown to the user: the editor's own
    stages (domain EditorStage) plus what the use case does around them."""

    SEGMENTING = "segmenting"
    READING_INSTRUCTION = EditorStage.READING_INSTRUCTION.value
    LOADING_MODEL = EditorStage.LOADING_MODEL.value
    GENERATING = EditorStage.GENERATING.value
    DECODING = EditorStage.DECODING.value
    COMPOSITING = "compositing"
    DONE = "done"


# Rough position of each stage in the run. Stage-based rather than
# time-based on purpose: model load time varies a lot (cached vs. not), so
# a time estimate would lie; the stage label tells the user what's actually
# happening and the bar only has to move monotonically.
_STAGE_FRACTION = {
    EditStage.SEGMENTING: 0.05,
    EditStage.READING_INSTRUCTION: 0.15,
    EditStage.LOADING_MODEL: 0.30,
    EditStage.DECODING: 0.90,
    EditStage.COMPOSITING: 0.96,
    EditStage.DONE: 1.0,
}
_GENERATING_START, _GENERATING_SPAN = 0.30, 0.55


@dataclass(frozen=True, slots=True)
class EditProgress:
    stage: EditStage
    fraction: float  # 0-1, monotonic over a run
    step: int | None = None
    steps: int | None = None

    @staticmethod
    def at(stage: EditStage, step: int | None = None, steps: int | None = None) -> EditProgress:
        if stage is EditStage.GENERATING:
            done = (step or 0) / steps if steps else 0.0
            fraction = _GENERATING_START + _GENERATING_SPAN * done
        else:
            fraction = _STAGE_FRACTION[stage]
        return EditProgress(stage=stage, fraction=fraction, step=step, steps=steps)

    @staticmethod
    def from_editor(progress: EditorProgress) -> EditProgress:
        return EditProgress.at(EditStage(progress.stage.value), progress.step, progress.steps)
