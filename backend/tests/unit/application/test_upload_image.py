from app.application.dto.upload_image import UploadImageRequest
from app.application.use_cases.upload_image import UploadImageUseCase
from tests.unit.application.fakes import FakeImageRepository, FakeImageStorage


def test_upload_image_persists_image_and_starts_a_session():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    use_case = UploadImageUseCase(storage, repo)

    result = use_case.execute(
        UploadImageRequest(
            file_bytes=b"raw-bytes",
            original_filename="selfie.png",
            content_type="image/png",
            width=800,
            height=600,
        )
    )

    assert result.width == 800
    assert result.height == 600
    assert result.url.startswith("memory://original/")

    stored_image = repo.get_image(result.image_id)
    assert stored_image is not None
    assert stored_image.original_filename == "selfie.png"
    assert storage.load(stored_image.storage_ref) == b"raw-bytes"

    session = repo.get_edit_session_for_image(result.image_id)
    assert session is not None
    assert session.current_image_ref == stored_image.storage_ref
    assert session.edit_ids == []
