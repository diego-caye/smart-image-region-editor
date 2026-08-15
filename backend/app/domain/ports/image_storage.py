from __future__ import annotations

from abc import ABC, abstractmethod


class ImageStorage(ABC):
    """Stores and retrieves raw image bytes behind an opaque reference
    string. Domain/Application never see a filesystem path or a bucket URL —
    only this ref, which they pass around and hand back to this same port.
    """

    @abstractmethod
    def save(self, data: bytes, *, kind: str, suggested_name: str | None = None) -> str:
        """Persist bytes under a logical `kind` (e.g. 'original', 'mask',
        'preview', 'final') and return an opaque storage_ref."""
        ...

    @abstractmethod
    def load(self, storage_ref: str) -> bytes: ...

    @abstractmethod
    def url_for(self, storage_ref: str) -> str:
        """A URL the frontend can load the image from."""
        ...
