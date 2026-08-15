import pytest

from app.application.dto.upload_image import UploadImageRequest
from app.application.use_cases.analyze_image import AnalyzeImageUseCase, ImageNotFound
from app.application.use_cases.get_detected_regions import GetDetectedRegionsUseCase
from app.application.use_cases.upload_image import UploadImageUseCase
from app.domain.entities.region import DetectedRegion
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.region_type import RegionType
from tests.unit.application.fakes import FakeImageDetector, FakeImageRepository, FakeImageStorage


def _upload_a_fake_image(storage, repo):
    use_case = UploadImageUseCase(storage, repo)
    return use_case.execute(
        UploadImageRequest(
            file_bytes=b"raw-bytes",
            original_filename="selfie.png",
            content_type="image/png",
            width=800,
            height=600,
        )
    )


def test_analyze_image_persists_detected_regions():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded = _upload_a_fake_image(storage, repo)

    canned_face = DetectedRegion.new(
        image_id=uploaded.image_id,
        region_type=RegionType.FACE,
        bounding_box=BoundingBox(x_min=100, y_min=100, x_max=300, y_max=300),
        confidence=0.95,
    )
    canned_hand = DetectedRegion.new(
        image_id=uploaded.image_id,
        region_type=RegionType.RIGHT_HAND,
        bounding_box=BoundingBox(x_min=400, y_min=400, x_max=500, y_max=500),
        confidence=0.8,
    )
    detector = FakeImageDetector([canned_face, canned_hand])
    use_case = AnalyzeImageUseCase(repo, storage, detector)

    result = use_case.execute(uploaded.image_id)

    assert {r.region_type for r in result.regions} == {RegionType.FACE, RegionType.RIGHT_HAND}
    assert len(repo.get_regions_for_image(uploaded.image_id)) == 2


def test_analyze_image_raises_for_unknown_image():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    use_case = AnalyzeImageUseCase(repo, storage, FakeImageDetector([]))

    from uuid import uuid4

    with pytest.raises(ImageNotFound):
        use_case.execute(uuid4())


def test_get_detected_regions_reads_back_without_redetecting():
    storage = FakeImageStorage()
    repo = FakeImageRepository()
    uploaded = _upload_a_fake_image(storage, repo)

    canned_face = DetectedRegion.new(
        image_id=uploaded.image_id,
        region_type=RegionType.FACE,
        bounding_box=BoundingBox(x_min=100, y_min=100, x_max=300, y_max=300),
        confidence=0.95,
    )
    AnalyzeImageUseCase(repo, storage, FakeImageDetector([canned_face])).execute(uploaded.image_id)

    result = GetDetectedRegionsUseCase(repo).execute(uploaded.image_id)
    assert len(result.regions) == 1
    assert result.regions[0].region_type == RegionType.FACE
