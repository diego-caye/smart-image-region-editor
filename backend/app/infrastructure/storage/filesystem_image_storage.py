from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.domain.ports.image_storage import ImageStorage

_ALLOWED_KINDS = {"original", "mask", "preview", "final"}


class FilesystemImageStorage(ImageStorage):
    """Stores images as files under `root/<kind>/<uuid>.<ext>` and serves
    them back through a URL prefix a FastAPI StaticFiles mount answers for
    (wired in main.py). This is the MVP storage adapter; swapping it for
    S3/GCS later means writing one new adapter behind ImageStorage —
    Domain/Application don't change.
    """

    def __init__(self, root: Path, *, static_url_prefix: str) -> None:
        self._root = root
        self._static_url_prefix = static_url_prefix.rstrip("/")
        for kind in _ALLOWED_KINDS:
            (self._root / kind).mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, *, kind: str, suggested_name: str | None = None) -> str:
        if kind not in _ALLOWED_KINDS:
            raise ValueError(f"Unknown storage kind '{kind}'")
        extension = Path(suggested_name).suffix if suggested_name else ".png"
        if not extension:
            extension = ".png"
        filename = f"{uuid4().hex}{extension}"
        storage_ref = f"{kind}/{filename}"
        (self._root / storage_ref).write_bytes(data)
        return storage_ref

    def load(self, storage_ref: str) -> bytes:
        path = self._resolve(storage_ref)
        return path.read_bytes()

    def url_for(self, storage_ref: str) -> str:
        self._resolve(storage_ref)  # validate before handing out a URL
        return f"{self._static_url_prefix}/{storage_ref}"

    def _resolve(self, storage_ref: str) -> Path:
        path = (self._root / storage_ref).resolve()
        if self._root.resolve() not in path.parents:
            raise ValueError(f"storage_ref escapes storage root: {storage_ref!r}")
        return path
