from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ModelFileNotFound(FileNotFoundError):
    def __init__(self, what: str, path: Path) -> None:
        super().__init__(f"{what} not found at '{path}' and no Hugging Face fallback was given.")


def require_file(path: Path, *, what: str) -> Path:
    if not path.is_file():
        raise ModelFileNotFound(what, path)
    return path


def resolve_weights_file(
    configured_path: Path,
    *,
    what: str,
    hf_repo_id: str,
    hf_filename: str,
    cache_dir: Path,
) -> Path:
    """Uses configured_path directly if it already exists — e.g. reusing a
    local ComfyUI install's weights, avoiding a duplicate download, which is
    what the default settings point at. Otherwise downloads hf_filename
    from hf_repo_id (verified against the real Hugging Face API before
    being wired here, matching the file already on this machine's ComfyUI
    install byte-for-byte — see docs/architecture.md) into cache_dir, so
    the app is self-contained with no ComfyUI installed at all — a fresh
    git clone, or the Docker deployment where the ComfyUI-models bind mount
    is empty/absent.
    """
    if configured_path.is_file():
        return configured_path

    logger.info(
        "%s not found at %s; downloading %s from %s instead",
        what,
        configured_path,
        hf_filename,
        hf_repo_id,
    )
    from huggingface_hub import hf_hub_download

    downloaded = hf_hub_download(repo_id=hf_repo_id, filename=hf_filename, cache_dir=str(cache_dir))
    return Path(downloaded)
