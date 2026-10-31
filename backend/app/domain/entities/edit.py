from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor


class EditStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PREVIEW_READY = "preview_ready"
    CONFIRMED = "confirmed"
    DISCARDED = "discarded"
    FAILED = "failed"
    REVERTED = "reverted"  # was confirmed, then undone


class InvalidEditTransition(ValueError):
    pass


@dataclass(slots=True)
class Edit:
    """One localized transformation applied to one region, at one point in an
    EditSession's history. source_image_ref is whatever the edit was applied
    ON TOP OF — the original image, or a previously confirmed edit's result —
    which is what makes edits chainable without one destroying another.
    """

    id: UUID
    session_id: UUID
    region_id: UUID
    operation: EditOperation
    source_image_ref: str
    color: GarmentColor | None = None  # only for garment operations
    status: EditStatus = EditStatus.PENDING
    preview_ref: str | None = None
    final_ref: str | None = None
    seed: int | None = None
    model_metadata: dict = field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def new(
        *,
        session_id: UUID,
        region_id: UUID,
        operation: EditOperation,
        source_image_ref: str,
        color: GarmentColor | None = None,
    ) -> Edit:
        return Edit(
            id=uuid4(),
            session_id=session_id,
            region_id=region_id,
            operation=operation,
            source_image_ref=source_image_ref,
            color=color,
        )

    def mark_processing(self) -> None:
        self._transition(EditStatus.PROCESSING)

    def mark_preview_ready(
        self, preview_ref: str, *, seed: int | None = None, model_metadata: dict | None = None
    ) -> None:
        self.preview_ref = preview_ref
        self.seed = seed
        if model_metadata:
            self.model_metadata = model_metadata
        self._transition(EditStatus.PREVIEW_READY)

    def confirm(self) -> None:
        if self.status != EditStatus.PREVIEW_READY:
            raise InvalidEditTransition(f"Cannot confirm an edit in status '{self.status}'")
        self.final_ref = self.preview_ref
        self._transition(EditStatus.CONFIRMED)

    def discard(self) -> None:
        if self.status not in (EditStatus.PREVIEW_READY, EditStatus.FAILED):
            raise InvalidEditTransition(f"Cannot discard an edit in status '{self.status}'")
        self._transition(EditStatus.DISCARDED)

    def revert(self) -> None:
        if self.status != EditStatus.CONFIRMED:
            raise InvalidEditTransition(f"Cannot revert an edit in status '{self.status}'")
        self._transition(EditStatus.REVERTED)

    def mark_failed(self, error_message: str) -> None:
        self.error_message = error_message
        self._transition(EditStatus.FAILED)

    def _transition(self, new_status: EditStatus) -> None:
        self.status = new_status
        self.updated_at = datetime.now(UTC)
