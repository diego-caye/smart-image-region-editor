from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.domain.entities.edit import EditStatus
from app.domain.value_objects.edit_operation import EditOperation


class EditRegionRequestBody(BaseModel):
    region_id: UUID
    operation: EditOperation


class EditRegionResponse(BaseModel):
    edit_id: UUID
    status: EditStatus
    preview_url: str | None
    error_message: str | None = None


class ConfirmEditResponse(BaseModel):
    edit_id: UUID
    status: EditStatus
    final_url: str | None


class DiscardEditResponse(BaseModel):
    edit_id: UUID
    status: EditStatus
