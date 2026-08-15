from __future__ import annotations

from uuid import UUID

from app.application.dto.edit_region import ConfirmEditResult
from app.domain.ports.image_repository import ImageRepository
from app.domain.ports.image_storage import ImageStorage


class EditNotFound(ValueError):
    pass


class EditSessionNotFound(ValueError):
    pass


class ConfirmEditUseCase:
    """Confirming an edit makes its result the session's new current image,
    so the *next* edit (e.g. mouth, after hand) applies on top of it instead
    of the original — this is what makes multiple edits combine without one
    destroying another."""

    def __init__(self, image_repository: ImageRepository, image_storage: ImageStorage) -> None:
        self._repo = image_repository
        self._storage = image_storage

    def execute(self, edit_id: UUID) -> ConfirmEditResult:
        edit = self._repo.get_edit(edit_id)
        if edit is None:
            raise EditNotFound(str(edit_id))

        edit.confirm()
        self._repo.save_edit(edit)

        session = self._repo.get_edit_session(edit.session_id)
        if session is None:
            raise EditSessionNotFound(str(edit.session_id))
        session.advance_after_confirm(edit.final_ref)
        self._repo.save_edit_session(session)

        return ConfirmEditResult(
            edit_id=edit.id,
            status=edit.status,
            final_url=self._storage.url_for(edit.final_ref),
        )
