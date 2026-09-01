from __future__ import annotations

from pathlib import Path


class ModelFileNotFound(FileNotFoundError):
    def __init__(self, what: str, path: Path) -> None:
        super().__init__(
            f"{what} not found at '{path}'. Check the relevant setting in .env "
            f"(see backend/README.md) — by default it points at your local "
            f"ComfyUI install's weights so nothing is downloaded twice."
        )


def require_file(path: Path, *, what: str) -> Path:
    if not path.is_file():
        raise ModelFileNotFound(what, path)
    return path
