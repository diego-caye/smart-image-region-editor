from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.entities.edit import EditStatus
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor
from app.domain.value_objects.region_type import RegionType


@dataclass(slots=True)
class EditHistoryEntry:
    edit_id: UUID
    region_type: RegionType | None  # None if the region is gone
    operation: EditOperation
    color: GarmentColor | None
    status: EditStatus  # CONFIRMED or REVERTED
    result_url: str | None
    created_at: datetime


@dataclass(slots=True)
class EditHistory:
    image_id: UUID
    original_url: str
    current_url: str
    entries: list[EditHistoryEntry]  # oldest first
    can_undo: bool


@dataclass(slots=True)
class UndoResult:
    reverted_edit_id: UUID
    current_url: str


@dataclass(slots=True)
class CurrentImage:
    data: bytes
    filename: str
