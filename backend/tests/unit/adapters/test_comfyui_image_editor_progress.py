"""How ComfyUI node events become the user-visible editor stages."""

from __future__ import annotations

from app.adapters.image_editing.comfyui_image_editor import _progress_translator
from app.domain.ports.image_editor import EditorProgress, EditorStage
from app.infrastructure.image_editing.comfyui.client import NodeEvent


def test_node_events_of_a_real_run_become_editor_stages():
    reported: list[EditorProgress] = []
    translate = _progress_translator(reported.append)

    for event in [
        NodeEvent("LoadImage"),
        NodeEvent("TextEncodeQwenImageEditPlus"),
        NodeEvent("TextEncodeQwenImageEditPlus"),
        NodeEvent("KSampler"),
        NodeEvent("KSampler", step=1, steps=4),
        NodeEvent("KSampler", step=4, steps=4),
        NodeEvent("VAEDecode"),
        NodeEvent("SaveImage"),
    ]:
        translate(event)

    assert reported == [
        EditorProgress(EditorStage.READING_INSTRUCTION),
        EditorProgress(EditorStage.READING_INSTRUCTION),
        # KSampler *starting* is where the model weights actually load (~30s
        # measured); only its step events mean it's generating.
        EditorProgress(EditorStage.LOADING_MODEL),
        EditorProgress(EditorStage.GENERATING, 1, 4),
        EditorProgress(EditorStage.GENERATING, 4, 4),
        EditorProgress(EditorStage.DECODING),
    ]
