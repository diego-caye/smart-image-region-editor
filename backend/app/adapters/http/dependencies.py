"""FastAPI dependency wiring — the composition root's HTTP-facing half.
This is the only place allowed to know both "FastAPI's Depends()" and
"which concrete adapter implements which Domain port". Controllers only
import from here, never construct an adapter themselves.
"""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends
from sqlmodel import Session

from app.adapters.persistence.sqlalchemy_image_repository import SqlAlchemyImageRepository
from app.application.use_cases.analyze_image import AnalyzeImageUseCase
from app.application.use_cases.get_detected_regions import GetDetectedRegionsUseCase
from app.application.use_cases.list_operations_for_region import ListOperationsForRegionUseCase
from app.application.use_cases.upload_image import UploadImageUseCase
from app.domain.ports.image_detector import ImageDetector
from app.domain.ports.image_repository import ImageRepository
from app.domain.ports.image_segmenter import ImageSegmenter
from app.domain.ports.image_storage import ImageStorage
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.database.engine import make_engine
from app.infrastructure.storage.filesystem_image_storage import FilesystemImageStorage


@lru_cache
def _engine():
    return make_engine(get_settings())


@lru_cache
def get_image_storage() -> ImageStorage:
    settings: Settings = get_settings()
    return FilesystemImageStorage(settings.storage_root, static_url_prefix=settings.static_url_prefix)


def get_session() -> Generator[Session, None, None]:
    with Session(_engine()) as session:
        yield session


def get_image_repository(session: Session = Depends(get_session)) -> ImageRepository:
    return SqlAlchemyImageRepository(session)


def get_upload_image_use_case(
    storage: ImageStorage = Depends(get_image_storage),
    repo: ImageRepository = Depends(get_image_repository),
) -> UploadImageUseCase:
    return UploadImageUseCase(storage, repo)


def get_list_operations_use_case() -> ListOperationsForRegionUseCase:
    # No ports to inject: this use case is a pure domain-rule lookup.
    return ListOperationsForRegionUseCase()


@lru_cache
def get_image_detector() -> ImageDetector:
    # Imported lazily so the app still boots without ultralytics/torch
    # installed (e.g. before Phase 3's ML deps are set up) — only hitting
    # /analyze requires them. Loading two YOLO models is expensive, hence
    # the process-wide singleton via lru_cache.
    from app.adapters.vision.yolo_sam2_image_detector import YoloImageDetector
    from app.infrastructure.vision.device import resolve_device
    from app.infrastructure.vision.model_registry import require_file
    from app.infrastructure.vision.yolo_detector import YoloDetector

    settings = get_settings()
    device = resolve_device(settings.detection_device)
    face_detector = YoloDetector(
        require_file(settings.yolo_face_model_path, what="Face YOLO weights"),
        device=device,
        label="face",
    )
    hand_detector = YoloDetector(
        require_file(settings.yolo_hand_model_path, what="Hand YOLO weights"),
        device=device,
        label="hand",
    )
    return YoloImageDetector(face_detector, hand_detector)


def get_analyze_image_use_case(
    repo: ImageRepository = Depends(get_image_repository),
    storage: ImageStorage = Depends(get_image_storage),
    detector: ImageDetector = Depends(get_image_detector),
) -> AnalyzeImageUseCase:
    return AnalyzeImageUseCase(repo, storage, detector)


def get_get_detected_regions_use_case(
    repo: ImageRepository = Depends(get_image_repository),
) -> GetDetectedRegionsUseCase:
    return GetDetectedRegionsUseCase(repo)


@lru_cache
def get_image_segmenter() -> ImageSegmenter:
    # Not wired to any HTTP endpoint yet (segmentation is lazy — only
    # EditRegionUseCase, landing in the Qwen-editing phase, actually needs
    # it) but built and verified now, alongside detection, since both share
    # the same GPU/device-management concerns.
    from app.adapters.vision.sam2_image_segmenter import Sam2ImageSegmenter
    from app.infrastructure.vision.device import resolve_device
    from app.infrastructure.vision.sam2_segmenter import Sam2MaskPredictor

    settings = get_settings()
    predictor = Sam2MaskPredictor(
        settings.sam2_model_id,
        device=resolve_device(settings.segmentation_device),
        cache_dir=settings.models_cache_dir,
    )
    return Sam2ImageSegmenter(predictor)
