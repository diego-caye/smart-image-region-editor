from __future__ import annotations

from app.application.dto.upload_image import UploadImageRequest, UploadImageResult
from app.domain.entities.edit_session import EditSession
from app.domain.entities.image import Image
from app.domain.ports.image_repository import ImageRepository
from app.domain.ports.image_storage import ImageStorage


class UploadImageUseCase:
    """Stores an uploaded image and starts its EditSession."""

    def __init__(self, image_storage: ImageStorage, image_repository: ImageRepository) -> None:
        self._image_storage = image_storage
        self._image_repository = image_repository

    def execute(self, request: UploadImageRequest) -> UploadImageResult:
        storage_ref = self._image_storage.save(
            request.file_bytes, kind="original", suggested_name=request.original_filename
        )
        image = Image.new(
            storage_ref=storage_ref,
            original_filename=request.original_filename,
            content_type=request.content_type,
            width=request.width,
            height=request.height,
        )
        self._image_repository.save_image(image)

        session = EditSession.new(image_id=image.id, original_image_ref=storage_ref)
        self._image_repository.save_edit_session(session)

        return UploadImageResult(
            image_id=image.id,
            width=image.width,
            height=image.height,
            url=self._image_storage.url_for(storage_ref),
        )
