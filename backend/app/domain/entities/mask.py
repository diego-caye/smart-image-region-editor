from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(slots=True)
class Mask:
    """A precise, pixel-level mask for a region, stored full-size (same
    dimensions as the image it was produced from) behind an opaque
    storage_ref, so downstream ports never need crop-offset math to use it.
    """

    id: UUID
    region_id: UUID
    storage_ref: str
    width: int
    height: int
    feather_px: int = 0
    grow_px: int = 0

    @staticmethod
    def new(
        *,
        region_id: UUID,
        storage_ref: str,
        width: int,
        height: int,
        feather_px: int = 0,
        grow_px: int = 0,
    ) -> Mask:
        return Mask(
            id=uuid4(),
            region_id=region_id,
            storage_ref=storage_ref,
            width=width,
            height=height,
            feather_px=feather_px,
            grow_px=grow_px,
        )
