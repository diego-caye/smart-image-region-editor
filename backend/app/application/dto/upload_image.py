from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class UploadImageRequest:
    """width/height/content_type are already known by the caller (the HTTP
    controller sniffs them with Pillow before invoking this use case) —
    Application itself never touches an image-decoding library."""

    file_bytes: bytes
    original_filename: str
    content_type: str
    width: int
    height: int


@dataclass(slots=True)
class UploadImageResult:
    image_id: UUID
    width: int
    height: int
    url: str
