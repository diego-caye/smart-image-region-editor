"""ComfyUIClient's websocket handling, fed a scripted message sequence
modeled on a real run (see docs/architecture.md) — no server needed."""

from __future__ import annotations

import json

import pytest

from app.infrastructure.image_editing.comfyui.client import (
    ComfyUIClient,
    ComfyUIExecutionError,
    ComfyUITimeoutError,
    NodeEvent,
)

PROMPT = {
    "load_image": {"class_type": "LoadImage"},
    "positive_cond": {"class_type": "TextEncodeQwenImageEditPlus"},
    "sampler": {"class_type": "KSampler"},
    "vae_decode": {"class_type": "VAEDecode"},
    "save_image": {"class_type": "SaveImage"},
}
IMAGE_REF = {"filename": "smart_editor_00001_.png", "subfolder": "", "type": "output"}


def _msg(kind: str, **data) -> str:
    return json.dumps({"type": kind, "data": data})


class ScriptedSocket:
    def __init__(self, messages):
        self._messages = list(messages)

    def recv(self, timeout=None):
        if not self._messages:
            raise TimeoutError
        return self._messages.pop(0)


def _run(messages, on_event=None, timeout_seconds=60.0):
    client = ComfyUIClient("http://comfyui:8188", timeout_seconds=timeout_seconds)
    return client._wait_for_output(
        ScriptedSocket(messages), PROMPT, "p1", "save_image", on_event
    )


def test_returns_the_output_image_and_reports_nodes_and_steps_on_the_way():
    events: list[NodeEvent] = []
    image_ref = _run(
        [
            _msg("status", status={"exec_info": {"queue_remaining": 1}}),
            _msg("execution_start", prompt_id="p1"),
            _msg("executing", node="load_image", prompt_id="p1"),
            _msg("executing", node="positive_cond", prompt_id="p1"),
            _msg("executing", node="sampler", prompt_id="p1"),
            b"\x00\x01binary-preview",
            _msg("progress", value=1, max=4, node="sampler", prompt_id="p1"),
            _msg("progress", value=4, max=4, node="sampler", prompt_id="p1"),
            _msg("executing", node="vae_decode", prompt_id="p1"),
            _msg("executing", node="save_image", prompt_id="p1"),
            _msg("executed", node="save_image", output={"images": [IMAGE_REF]}, prompt_id="p1"),
        ],
        on_event=events.append,
    )

    assert image_ref == IMAGE_REF
    assert events == [
        NodeEvent("LoadImage"),
        NodeEvent("TextEncodeQwenImageEditPlus"),
        NodeEvent("KSampler"),
        NodeEvent("KSampler", step=1, steps=4),
        NodeEvent("KSampler", step=4, steps=4),
        NodeEvent("VAEDecode"),
        NodeEvent("SaveImage"),
    ]


def test_ignores_other_prompts_events():
    events: list[NodeEvent] = []
    _run(
        [
            _msg("executing", node="sampler", prompt_id="someone-else"),
            _msg("executed", node="save_image", output={"images": [{"filename": "x"}]}, prompt_id="someone-else"),
            _msg("executed", node="save_image", output={"images": [IMAGE_REF]}, prompt_id="p1"),
        ],
        on_event=events.append,
    )
    assert events == []


def test_execution_error_raises():
    with pytest.raises(ComfyUIExecutionError, match="CUDA out of memory"):
        _run(
            [
                _msg("executing", node="sampler", prompt_id="p1"),
                _msg("execution_error", exception_message="CUDA out of memory", prompt_id="p1"),
            ]
        )


def test_no_output_before_the_socket_goes_quiet_is_a_timeout():
    with pytest.raises(ComfyUITimeoutError):
        _run([_msg("executing", node="sampler", prompt_id="p1")])


def test_finishing_without_the_output_on_the_socket_falls_back_to_history(monkeypatch):
    client = ComfyUIClient("http://comfyui:8188", timeout_seconds=60.0)
    monkeypatch.setattr(client, "_image_ref_from_history", lambda prompt_id, node_id: IMAGE_REF)
    image_ref = client._wait_for_output(
        ScriptedSocket([_msg("executing", node=None, prompt_id="p1")]),
        PROMPT,
        "p1",
        "save_image",
        None,
    )
    assert image_ref == IMAGE_REF


@pytest.mark.parametrize(
    ("http_url", "ws_url"),
    [("http://comfyui:8188", "ws://comfyui:8188"), ("https://host/", "wss://host")],
)
def test_websocket_url_follows_the_http_scheme(http_url, ws_url):
    assert ComfyUIClient(http_url, timeout_seconds=1)._ws_url == ws_url
