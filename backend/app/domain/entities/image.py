from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class Image:
    """An uploaded source image — the anchor everything else (regions, masks,
    edits, the edit session) hangs off. storage_ref is opaque; only an
    ImageStorage adapter knows what it actually points to.
    """

    id: UUID
    storage_ref: str
    original_filename: str
    content_type: str
    width: int
    height: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def new(
        *, storage_ref: str, original_filename: str, content_type: str, width: int, height: int
    ) -> Image:
        return Image(
            id=uuid4(),
            storage_ref=storage_ref,
            original_filename=original_filename,
            content_type=content_type,
            width=width,
            height=height,
        )
