from __future__ import annotations

from pathlib import PurePosixPath
from uuid import UUID

from app.application.dto.edit_history import CurrentImage
from app.application.use_cases.edit_region import EditSessionNotFound, ImageNotFound
from app.domain.ports.image_repository import ImageRepository
from app.domain.ports.image_storage import ImageStorage


class GetCurrentImageUseCase:
    """The image as it stands now — the original, or the result of the last
    confirmed edit — with a filename to save it under."""

    def __init__(self, image_repository: ImageRepository, image_storage: ImageStorage) -> None:
        self._repo = image_repository
        self._storage = image_storage

    def execute(self, image_id: UUID) -> CurrentImage:
        image = self._repo.get_image(image_id)
        if image is None:
            raise ImageNotFound(str(image_id))
        session = self._repo.get_edit_session_for_image(image_id)
        if session is None:
            raise EditSessionNotFound(str(image_id))

        ref = session.current_image_ref
        stem = PurePosixPath(image.original_filename).stem or "image"
        suffix = PurePosixPath(ref).suffix or ".png"
        edited = ref != image.storage_ref
        return CurrentImage(
            data=self._storage.load(ref),
            filename=f"{stem}-edited{suffix}" if edited else f"{stem}{suffix}",
        )
