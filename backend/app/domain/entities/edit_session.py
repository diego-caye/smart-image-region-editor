from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(slots=True)
class EditSession:
    """Tracks the ordered chain of edits applied to one Image, and which image
    ref the *next* edit should be applied on top of — the original upload,
    or the last confirmed edit's result. This is what lets a second edit
    (e.g. mouth) build on a first (e.g. hand) instead of overwriting it.
    """

    id: UUID
    image_id: UUID
    current_image_ref: str
    edit_ids: list[UUID] = field(default_factory=list)

    @staticmethod
    def new(*, image_id: UUID, original_image_ref: str) -> EditSession:
        return EditSession(id=uuid4(), image_id=image_id, current_image_ref=original_image_ref)

    def record_edit(self, edit_id: UUID) -> None:
        self.edit_ids.append(edit_id)

    def advance_after_confirm(self, new_current_image_ref: str) -> None:
        self.current_image_ref = new_current_image_ref

    def is_current(self, image_ref: str) -> bool:
        """Whether an edit made on top of image_ref would still apply on top
        of the current image — False once another edit was confirmed or
        undone since."""
        return image_ref == self.current_image_ref

    def revert_to(self, previous_image_ref: str) -> None:
        """Undo: go back to the image the reverted edit was applied on."""
        self.current_image_ref = previous_image_ref
