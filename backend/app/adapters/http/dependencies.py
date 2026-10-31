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
from app.application.ports.edit_progress_tracker import EditProgressTracker
from app.application.use_cases.analyze_image import AnalyzeImageUseCase
from app.application.use_cases.confirm_edit import ConfirmEditUseCase
from app.application.use_cases.discard_edit import DiscardEditUseCase
from app.application.use_cases.edit_region import EditRegionUseCase
from app.application.use_cases.get_detected_regions import GetDetectedRegionsUseCase
from app.application.use_cases.list_operations_for_region import ListOperationsForRegionUseCase
from app.application.use_cases.upload_image import UploadImageUseCase
from app.domain.ports.image_compositor import ImageCompositor
from app.domain.ports.image_detector import ImageDetector
from app.domain.ports.image_editor import ImageEditor
from app.domain.ports.image_repository import ImageRepository
from app.domain.ports.image_segmenter import ImageSegmenter
from app.domain.ports.image_storage import ImageStorage
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.database.engine import make_engine
from app.infrastructure.progress.in_memory_edit_progress_tracker import InMemoryEditProgressTracker
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
    # Imported lazily so the app still boots without ultralytics/torch/
    # mediapipe installed (e.g. before Phase 3's ML deps are set up) — only
    # hitting /analyze requires them. Loading the YOLO + MediaPipe models is
    # expensive, hence the process-wide singleton via lru_cache.
    from app.adapters.vision.composite_image_detector import CompositeImageDetector
    from app.adapters.vision.mediapipe_region_detector import MediaPipeRegionDetector
    from app.adapters.vision.yolo_sam2_image_detector import YoloImageDetector
    from app.infrastructure.vision.device import resolve_device
    from app.infrastructure.vision.mediapipe_landmarker import MediaPipeLandmarker
    from app.infrastructure.vision.model_registry import resolve_weights_file
    from app.infrastructure.vision.yolo_detector import YoloDetector

    settings = get_settings()
    device = resolve_device(settings.detection_device)
    face_weights = resolve_weights_file(
        settings.yolo_face_model_path,
        what="Face YOLO weights",
        hf_repo_id=settings.yolo_face_hf_repo_id,
        hf_filename=settings.yolo_face_hf_filename,
        cache_dir=settings.models_cache_dir,
    )
    hand_weights = resolve_weights_file(
        settings.yolo_hand_model_path,
        what="Hand YOLO weights",
        hf_repo_id=settings.yolo_hand_hf_repo_id,
        hf_filename=settings.yolo_hand_hf_filename,
        cache_dir=settings.models_cache_dir,
    )
    face_detector = YoloDetector(face_weights, device=device, label="face")
    hand_detector = YoloDetector(hand_weights, device=device, label="hand")
    yolo_detector = YoloImageDetector(face_detector, hand_detector)

    landmarker = MediaPipeLandmarker(
        face_model_path=settings.models_cache_dir / "mediapipe" / "face_landmarker.task",
        face_model_url=settings.mediapipe_face_landmarker_url,
        pose_model_path=settings.models_cache_dir / "mediapipe" / "pose_landmarker.task",
        pose_model_url=settings.mediapipe_pose_landmarker_url,
    )
    mediapipe_detector = MediaPipeRegionDetector(
        landmarker, face_crop_margin_px=settings.face_landmark_crop_margin_px
    )

    return CompositeImageDetector(yolo_detector, mediapipe_detector)


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
    # Segmentation is lazy (only EditRegionUseCase needs it, and only once
    # per region — see _get_or_create_mask), but the model is loaded once
    # per process either way.
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


@lru_cache
def get_image_editor() -> ImageEditor:
    from app.adapters.image_editing.comfyui_image_editor import ComfyUIImageEditor
    from app.infrastructure.image_editing.comfyui.client import ComfyUIClient

    settings = get_settings()
    client = ComfyUIClient(
        settings.comfyui_base_url, timeout_seconds=settings.comfyui_timeout_seconds
    )
    return ComfyUIImageEditor(
        client,
        crop_context_margin_px=settings.edit_crop_context_margin_px,
        unet_name=settings.qwen_unet_name,
        clip_name=settings.qwen_clip_name,
        vae_name=settings.qwen_vae_name,
        lora_name=settings.qwen_lora_name,
        lora_strength=settings.qwen_lora_strength,
        model_shift=settings.qwen_model_shift,
        cfg_norm_strength=settings.qwen_cfg_norm_strength,
        steps=settings.qwen_steps,
        cfg=settings.qwen_cfg,
        sampler_name=settings.qwen_sampler_name,
        scheduler=settings.qwen_scheduler,
    )


@lru_cache
def get_image_compositor() -> ImageCompositor:
    from app.adapters.imaging.pillow_image_compositor import PillowImageCompositor

    return PillowImageCompositor()


@lru_cache
def get_edit_progress_tracker() -> EditProgressTracker:
    # One per process: the request running an edit and the requests polling
    # its progress must see the same store.
    return InMemoryEditProgressTracker()


def get_edit_region_use_case(
    repo: ImageRepository = Depends(get_image_repository),
    storage: ImageStorage = Depends(get_image_storage),
    segmenter: ImageSegmenter = Depends(get_image_segmenter),
    editor: ImageEditor = Depends(get_image_editor),
    compositor: ImageCompositor = Depends(get_image_compositor),
    progress_tracker: EditProgressTracker = Depends(get_edit_progress_tracker),
) -> EditRegionUseCase:
    return EditRegionUseCase(
        repo, storage, segmenter, editor, compositor, progress_tracker=progress_tracker
    )


def get_confirm_edit_use_case(
    repo: ImageRepository = Depends(get_image_repository),
    storage: ImageStorage = Depends(get_image_storage),
) -> ConfirmEditUseCase:
    return ConfirmEditUseCase(repo, storage)


def get_discard_edit_use_case(
    repo: ImageRepository = Depends(get_image_repository),
) -> DiscardEditUseCase:
    return DiscardEditUseCase(repo)
