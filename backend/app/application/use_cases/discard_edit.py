from __future__ import annotations

from uuid import UUID

from app.application.dto.edit_region import DiscardEditResult
from app.domain.ports.image_repository import ImageRepository


class EditNotFound(ValueError):
    pass


class DiscardEditUseCase:
    """Discarding an edit leaves the session's current image untouched — the
    preview is simply thrown away."""

    def __init__(self, image_repository: ImageRepository) -> None:
        self._repo = image_repository

    def execute(self, edit_id: UUID) -> DiscardEditResult:
        edit = self._repo.get_edit(edit_id)
        if edit is None:
            raise EditNotFound(str(edit_id))
        edit.discard()
        self._repo.save_edit(edit)
        return DiscardEditResult(edit_id=edit.id, status=edit.status)
