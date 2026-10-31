from __future__ import annotations

from uuid import UUID

from app.application.dto.edit_history import UndoResult
from app.application.use_cases.edit_region import EditSessionNotFound
from app.application.use_cases.get_edit_history import applied_edits
from app.domain.entities.edit import EditStatus
from app.domain.ports.image_repository import ImageRepository
from app.domain.ports.image_storage import ImageStorage


class NothingToUndo(ValueError):
    pass


class UndoLastEditUseCase:
    """Reverts the most recent confirmed edit: the session goes back to the
    image that edit was applied on. Nothing is deleted — the reverted edit
    stays in the history, marked REVERTED — and undoing again reverts the
    one before it, back to the original upload."""

    def __init__(self, image_repository: ImageRepository, image_storage: ImageStorage) -> None:
        self._repo = image_repository
        self._storage = image_storage

    def execute(self, image_id: UUID) -> UndoResult:
        session = self._repo.get_edit_session_for_image(image_id)
        if session is None:
            raise EditSessionNotFound(str(image_id))

        confirmed = [
            e for e in applied_edits(self._repo, session) if e.status == EditStatus.CONFIRMED
        ]
        if not confirmed:
            raise NothingToUndo(str(image_id))
        last = confirmed[-1]

        last.revert()
        self._repo.save_edit(last)
        session.revert_to(last.source_image_ref)
        self._repo.save_edit_session(session)

        return UndoResult(
            reverted_edit_id=last.id, current_url=self._storage.url_for(session.current_image_ref)
        )
