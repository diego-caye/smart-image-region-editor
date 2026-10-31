from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.adapters.http.schemas.operations import operation_display
from app.application.dto.edit_history import EditHistory, EditHistoryEntry
from app.domain.entities.edit import EditStatus
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor
from app.domain.value_objects.region_type import RegionType


class EditHistoryEntryResponse(BaseModel):
    edit_id: UUID
    region_type: RegionType | None
    operation: EditOperation
    label: str
    emoji: str
    color: GarmentColor | None
    status: EditStatus
    result_url: str | None
    created_at: datetime


    @staticmethod
    def from_entry(entry: EditHistoryEntry) -> EditHistoryEntryResponse:
        emoji, label = operation_display(entry.operation)
        return EditHistoryEntryResponse(
            edit_id=entry.edit_id,
            region_type=entry.region_type,
            operation=entry.operation,
            label=label,
            emoji=emoji,
            color=entry.color,
            status=entry.status,
            result_url=entry.result_url,
            created_at=entry.created_at,
        )


class EditHistoryResponse(BaseModel):
    image_id: UUID
    original_url: str
    current_url: str
    entries: list[EditHistoryEntryResponse]
    can_undo: bool

    @staticmethod
    def from_result(result: EditHistory) -> EditHistoryResponse:
        return EditHistoryResponse(
            image_id=result.image_id,
            original_url=result.original_url,
            current_url=result.current_url,
            entries=[EditHistoryEntryResponse.from_entry(e) for e in result.entries],
            can_undo=result.can_undo,
        )


class UndoResponse(BaseModel):
    reverted_edit_id: UUID
    current_url: str
