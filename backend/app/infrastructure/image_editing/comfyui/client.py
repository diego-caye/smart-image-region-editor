"""Raw client for the local ComfyUI server. Every endpoint and websocket
event here was confirmed against the real server source of the installed
ComfyUI (server.py, execution.py, main.py — see docs/architecture.md) —
nothing is guessed. This module knows nothing about Qwen, edit operations,
or Domain; it only knows how to queue a prompt graph and fetch results.
adapters/image_editing/comfyui_image_editor.py is the translation layer
that gives this generic client meaning.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.infrastructure.idle_release import IdleReleaser


class ComfyUIError(Exception):
    pass


class ComfyUIValidationError(ComfyUIError):
    """The server rejected the prompt graph before running it (POST /prompt
    returned an error/node_errors)."""


class ComfyUIExecutionError(ComfyUIError):
    """The prompt was queued but a node raised during execution."""


class ComfyUITimeoutError(ComfyUIError):
    """The prompt did not finish within comfyui_timeout_seconds."""


@dataclass(frozen=True, slots=True)
class NodeEvent:
    """A node of the running prompt started (step is None), or reported
    progress (sampling steps)."""

    class_type: str
    step: int | None = None
    steps: int | None = None


class MessageSource(Protocol):
    """What _wait_for_output needs from a websocket — lets tests feed it
    scripted messages without a server."""

    def recv(self, timeout: float | None = None) -> str | bytes: ...


class ComfyUIClient:
    def __init__(
        self, base_url: str, *, timeout_seconds: float, idle_unload_seconds: float = 0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._ws_url = "ws" + self._base_url.removeprefix("http")  # http->ws, https->wss
        self._timeout_seconds = timeout_seconds
        # ComfyUI keeps models loaded between prompts; this asks it to let go
        # once edits stop coming (see IdleReleaser). 0 = never ask.
        self._idle = (
            IdleReleaser(idle_unload_seconds, self.free_memory, name="ComfyUI models")
            if idle_unload_seconds > 0
            else None
        )

    def free_memory(self) -> None:
        """POST /free: unload every model and free cached memory. Takes
        effect right away even when ComfyUI is idle — its prompt worker is
        woken by the flag (PromptQueue.set_flag notifies the queue)."""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self._base_url}/free", json={"unload_models": True, "free_memory": True}
            )
        response.raise_for_status()

    def upload_image(self, data: bytes, *, filename: str) -> str:
        """POST /upload/image. Returns the filename ComfyUI actually stored
        it under (overwrite=true, so normally the same one given)."""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self._base_url}/upload/image",
                files={"image": (filename, data, "image/png")},
                data={"type": "input", "overwrite": "true"},
            )
        response.raise_for_status()
        return response.json()["name"]

    def run_prompt(
        self,
        prompt: dict,
        *,
        output_node_id: str,
        on_event: Callable[[NodeEvent], None] | None = None,
    ) -> bytes:
        """Queue a prompt graph (POST /prompt), follow it over the /ws
        websocket, and return the bytes of the image produced by the node at
        output_node_id (fetched via GET /view).

        The websocket rather than polling GET /history: it reports each
        node as it runs (which is what makes a progress bar possible), and
        it delivers the output as soon as that node finishes, while /history
        only completes ~10s later, after ComfyUI's post-run cleanup (model
        unloading). The end-to-end gain is smaller — ~4s in a measured run —
        since downloading the image overlaps that cleanup and is slowed by
        it. ComfyUI only sends events to the
        client_id a prompt was queued with, so the socket is opened first,
        under a fresh id per call so concurrent edits don't see each
        other's events."""
        from websockets.sync.client import connect

        client_id = uuid.uuid4().hex
        try:
            with connect(
                f"{self._ws_url}/ws?clientId={client_id}", max_size=None, open_timeout=30
            ) as ws:
                prompt_id = self._queue_prompt(prompt, client_id)
                image_ref = self._wait_for_output(ws, prompt, prompt_id, output_node_id, on_event)
            return self._download_image(image_ref)
        finally:
            if self._idle is not None:
                self._idle.touch()

    def _queue_prompt(self, prompt: dict, client_id: str) -> str:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self._base_url}/prompt",
                json={"prompt": prompt, "client_id": client_id},
            )
        if response.status_code != 200:
            detail = _safe_json(response)
            raise ComfyUIValidationError(f"ComfyUI rejected the prompt: {detail}")
        body = response.json()
        node_errors = body.get("node_errors") or {}
        if node_errors:
            raise ComfyUIValidationError(f"ComfyUI reported node errors: {node_errors}")
        return body["prompt_id"]

    def _wait_for_output(
        self,
        ws: MessageSource,
        prompt: dict,
        prompt_id: str,
        output_node_id: str,
        on_event: Callable[[NodeEvent], None] | None,
    ) -> dict:
        """Returns the output node's image reference ({filename, subfolder,
        type}) once that node has run."""
        deadline = time.monotonic() + self._timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            try:
                if remaining <= 0:
                    raise TimeoutError
                raw = ws.recv(timeout=remaining)
            except TimeoutError as exc:
                raise ComfyUITimeoutError(
                    f"ComfyUI prompt {prompt_id} did not complete within {self._timeout_seconds}s"
                ) from exc
            if isinstance(raw, bytes):
                continue  # live preview frames

            message = json.loads(raw)
            kind, data = message.get("type"), message.get("data") or {}
            if data.get("prompt_id") != prompt_id:
                continue  # queue status broadcasts, other prompts
            node = data.get("node")

            if kind == "execution_error":
                detail = data.get("exception_message") or data
                raise ComfyUIExecutionError(f"ComfyUI execution failed: {detail}")
            if kind == "executed" and node == output_node_id:
                images = (data.get("output") or {}).get("images") or []
                if not images:
                    raise ComfyUIExecutionError(
                        f"No image output on node '{output_node_id}': {data.get('output')}"
                    )
                return images[0]
            if kind == "executing" and node is None:
                # Finished without the output node reporting over the socket
                # (e.g. every node was served from cache). By this event the
                # history is written — unlike at execution_success, which
                # arrives before ComfyUI's post-run cleanup.
                return self._image_ref_from_history(prompt_id, output_node_id)
            if on_event is not None and node is not None and kind in ("executing", "progress"):
                class_type = prompt.get(node, {}).get("class_type", "")
                if kind == "executing":
                    on_event(NodeEvent(class_type))
                else:
                    on_event(NodeEvent(class_type, step=data.get("value"), steps=data.get("max")))

    def _image_ref_from_history(self, prompt_id: str, output_node_id: str) -> dict:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{self._base_url}/history/{prompt_id}")
        response.raise_for_status()
        outputs = response.json().get(prompt_id, {}).get("outputs", {})
        images = (outputs.get(output_node_id) or {}).get("images") or []
        if not images:
            raise ComfyUIExecutionError(
                f"No image output found on node '{output_node_id}'; outputs were: {outputs}"
            )
        return images[0]

    def _download_image(self, image_ref: dict) -> bytes:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{self._base_url}/view",
                params={
                    "filename": image_ref["filename"],
                    "subfolder": image_ref.get("subfolder", ""),
                    "type": image_ref.get("type", "output"),
                },
            )
        response.raise_for_status()
        return response.content


def _safe_json(response: httpx.Response) -> str:
    try:
        return str(response.json())
    except ValueError:  # body isn't JSON (json.JSONDecodeError is a ValueError)
        return response.text
