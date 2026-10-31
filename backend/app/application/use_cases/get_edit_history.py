from __future__ import annotations

from uuid import UUID

from app.application.dto.edit_history import EditHistory, EditHistoryEntry
from app.application.use_cases.edit_region import EditSessionNotFound, ImageNotFound
from app.domain.entities.edit import Edit, EditStatus
from app.domain.entities.edit_session import EditSession
from app.domain.ports.image_repository import ImageRepository
from app.domain.ports.image_storage import ImageStorage

# Previews that were never accepted, discarded ones and failures aren't part
# of the image's history — only what was applied (and possibly undone).
_HISTORY_STATUSES = frozenset({EditStatus.CONFIRMED, EditStatus.REVERTED})


def applied_edits(repo: ImageRepository, session: EditSession) -> list[Edit]:
    """The session's confirmed/reverted edits, in the order they were made."""
    order = {edit_id: i for i, edit_id in enumerate(session.edit_ids)}
    edits = [
        e
        for e in repo.get_edits_for_session(session.id)
        if e.status in _HISTORY_STATUSES and e.id in order
    ]
    return sorted(edits, key=lambda e: order[e.id])


class GetEditHistoryUseCase:
    def __init__(self, image_repository: ImageRepository, image_storage: ImageStorage) -> None:
        self._repo = image_repository
        self._storage = image_storage

    def execute(self, image_id: UUID) -> EditHistory:
        image = self._repo.get_image(image_id)
        if image is None:
            raise ImageNotFound(str(image_id))
        session = self._repo.get_edit_session_for_image(image_id)
        if session is None:
            raise EditSessionNotFound(str(image_id))

        edits = applied_edits(self._repo, session)
        entries = []
        for edit in edits:
            region = self._repo.get_region(edit.region_id)
            entries.append(
                EditHistoryEntry(
                    edit_id=edit.id,
                    region_type=region.region_type if region else None,
                    operation=edit.operation,
                    color=edit.color,
                    status=edit.status,
                    result_url=self._storage.url_for(edit.final_ref) if edit.final_ref else None,
                    created_at=edit.created_at,
                )
            )
        return EditHistory(
            image_id=image.id,
            original_url=self._storage.url_for(image.storage_ref),
            current_url=self._storage.url_for(session.current_image_ref),
            entries=entries,
            can_undo=any(e.status == EditStatus.CONFIRMED for e in edits),
        )
