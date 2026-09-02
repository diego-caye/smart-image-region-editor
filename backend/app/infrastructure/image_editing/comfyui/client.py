"""Raw HTTP client for the local ComfyUI server. Every endpoint here was
confirmed against the real server.py of the installed ComfyUI (see
docs/architecture.md) — nothing is guessed. This module knows nothing about
Qwen, edit operations, or Domain; it only knows how to queue a prompt graph
and fetch results. adapters/image_editing/comfyui_image_editor.py is the
translation layer that gives this generic client meaning.
"""

from __future__ import annotations

import time
import uuid

import httpx


class ComfyUIError(Exception):
    pass


class ComfyUIValidationError(ComfyUIError):
    """The server rejected the prompt graph before running it (POST /prompt
    returned an error/node_errors)."""


class ComfyUIExecutionError(ComfyUIError):
    """The prompt was queued but a node raised during execution."""


class ComfyUITimeoutError(ComfyUIError):
    """The prompt did not finish within comfyui_timeout_seconds."""


class ComfyUIClient:
    def __init__(self, base_url: str, *, poll_interval_seconds: float, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._poll_interval_seconds = poll_interval_seconds
        self._timeout_seconds = timeout_seconds
        self._client_id = uuid.uuid4().hex

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

    def run_prompt(self, prompt: dict, *, output_node_id: str) -> bytes:
        """Queue a prompt graph (POST /prompt), poll GET /history/{id} until
        it completes, and return the bytes of the image produced by the
        SaveImage node at output_node_id (fetched via GET /view)."""
        prompt_id = self._queue_prompt(prompt)
        entry = self._wait_for_completion(prompt_id)
        return self._download_output_image(entry, output_node_id)

    def _queue_prompt(self, prompt: dict) -> str:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self._base_url}/prompt",
                json={"prompt": prompt, "client_id": self._client_id},
            )
        if response.status_code != 200:
            detail = _safe_json(response)
            raise ComfyUIValidationError(f"ComfyUI rejected the prompt: {detail}")
        body = response.json()
        node_errors = body.get("node_errors") or {}
        if node_errors:
            raise ComfyUIValidationError(f"ComfyUI reported node errors: {node_errors}")
        return body["prompt_id"]

    def _wait_for_completion(self, prompt_id: str) -> dict:
        deadline = time.monotonic() + self._timeout_seconds
        with httpx.Client(timeout=30.0) as client:
            while time.monotonic() < deadline:
                response = client.get(f"{self._base_url}/history/{prompt_id}")
                response.raise_for_status()
                history = response.json()
                entry = history.get(prompt_id)
                if entry is not None:
                    status = entry.get("status", {})
                    for message in status.get("messages", []):
                        if message[0] == "execution_error":
                            raise ComfyUIExecutionError(f"ComfyUI execution failed: {message[1]}")
                    if status.get("completed"):
                        return entry
                time.sleep(self._poll_interval_seconds)
        raise ComfyUITimeoutError(
            f"ComfyUI prompt {prompt_id} did not complete within {self._timeout_seconds}s"
        )

    def _download_output_image(self, entry: dict, output_node_id: str) -> bytes:
        outputs = entry.get("outputs", {})
        node_output = outputs.get(output_node_id)
        if not node_output or not node_output.get("images"):
            raise ComfyUIExecutionError(
                f"No image output found on node '{output_node_id}'; outputs were: {outputs}"
            )
        image_ref = node_output["images"][0]
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
    except Exception:
        return response.text
