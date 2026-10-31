from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.application.dto.edit_progress import EditStage
from app.domain.entities.edit import EditStatus
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor


class EditRegionRequestBody(BaseModel):
    region_id: UUID
    operation: EditOperation
    # Required exactly for operations whose catalog entry lists colors.
    color: GarmentColor | None = None
    # Chosen by the client so it can poll GET /edits/progress/{progress_id}
    # while this request is still running (a UUID in practice).
    progress_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,64}$")


class EditProgressResponse(BaseModel):
    stage: EditStage
    fraction: float
    step: int | None = None
    steps: int | None = None


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
