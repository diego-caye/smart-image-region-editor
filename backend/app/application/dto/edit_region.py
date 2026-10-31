from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.edit import EditStatus
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor


@dataclass(slots=True)
class EditRegionRequest:
    image_id: UUID
    region_id: UUID
    operation: EditOperation
    color: GarmentColor | None = None
    progress_id: str | None = None  # see EditProgressTracker


@dataclass(slots=True)
class EditRegionResult:
    edit_id: UUID
    status: EditStatus
    preview_url: str | None
    error_message: str | None = None


@dataclass(slots=True)
class ConfirmEditResult:
    edit_id: UUID
    status: EditStatus
    final_url: str | None


@dataclass(slots=True)
class DiscardEditResult:
    edit_id: UUID
    status: EditStatus
