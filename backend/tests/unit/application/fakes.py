"""In-memory fake adapters implementing every Domain Port.

These exist so Application use cases can be exercised without any real
database, filesystem, GPU model, or ComfyUI server — and they double as
living documentation of what each Port contract actually requires from a
real adapter.
"""

from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
from itertools import count
from uuid import UUID

from PIL import Image as PILImage

from app.application.dto.edit_progress import EditProgress
from app.application.ports.edit_progress_tracker import EditProgressTracker
from app.domain.entities.edit import Edit
from app.domain.entities.edit_session import EditSession
from app.domain.entities.image import Image
from app.domain.entities.mask import Mask
from app.domain.entities.region import DetectedRegion
from app.domain.ports.image_compositor import ImageCompositor
from app.domain.ports.image_detector import ImageDetector
from app.domain.ports.image_editor import EditorProgress, EditorStage, EditResult, ImageEditor
from app.domain.ports.image_repository import ImageRepository
from app.domain.ports.image_segmenter import ImageSegmenter, SegmentationResult
from app.domain.ports.image_storage import ImageStorage
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor


class FakeImageStorage(ImageStorage):
    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}
        self._counter = count(1)

    def save(self, data: bytes, *, kind: str, suggested_name: str | None = None) -> str:
        ref = f"{kind}/{next(self._counter)}.png"
        self._data[ref] = data
        return ref

    def load(self, storage_ref: str) -> bytes:
        return self._data[storage_ref]

    def url_for(self, storage_ref: str) -> str:
        return f"memory://{storage_ref}"


class FakeImageRepository(ImageRepository):
    def __init__(self) -> None:
        self.images: dict[UUID, Image] = {}
        self.regions: dict[UUID, DetectedRegion] = {}
        self.masks: dict[UUID, Mask] = {}
        self.edit_sessions: dict[UUID, EditSession] = {}
        self.edits: dict[UUID, Edit] = {}

    def save_image(self, image: Image) -> None:
        self.images[image.id] = image

    def get_image(self, image_id: UUID) -> Image | None:
        return self.images.get(image_id)

    def save_regions(self, regions: list[DetectedRegion]) -> None:
        for region in regions:
            self.regions[region.id] = region

    def get_regions_for_image(self, image_id: UUID) -> list[DetectedRegion]:
        return [r for r in self.regions.values() if r.image_id == image_id]

    def get_region(self, region_id: UUID) -> DetectedRegion | None:
        return self.regions.get(region_id)

    def update_region(self, region: DetectedRegion) -> None:
        self.regions[region.id] = region

    def save_mask(self, mask: Mask) -> None:
        self.masks[mask.id] = mask

    def get_mask(self, mask_id: UUID) -> Mask | None:
        return self.masks.get(mask_id)

    def save_edit_session(self, session: EditSession) -> None:
        self.edit_sessions[session.id] = session

    def get_edit_session(self, session_id: UUID) -> EditSession | None:
        return self.edit_sessions.get(session_id)

    def get_edit_session_for_image(self, image_id: UUID) -> EditSession | None:
        for session in self.edit_sessions.values():
            if session.image_id == image_id:
                return session
        return None

    def save_edit(self, edit: Edit) -> None:
        self.edits[edit.id] = edit

    def get_edit(self, edit_id: UUID) -> Edit | None:
        return self.edits.get(edit_id)

    def get_edits_for_session(self, session_id: UUID) -> list[Edit]:
        return [e for e in self.edits.values() if e.session_id == session_id]


class FakeImageDetector(ImageDetector):
    """Returns a fixed, caller-supplied list of regions regardless of the
    image bytes given — the point of a fake is to be predictable."""

    def __init__(self, regions_to_return: list[DetectedRegion] | None = None) -> None:
        self._regions_to_return = regions_to_return or []

    def detect(self, image_bytes: bytes, *, image_id: UUID) -> list[DetectedRegion]:
        return [
            DetectedRegion.new(
                image_id=image_id,
                region_type=r.region_type,
                bounding_box=r.bounding_box,
                confidence=r.confidence,
            )
            for r in self._regions_to_return
        ]


def _solid_png(size: tuple[int, int], value: int | tuple[int, int, int] = 255) -> bytes:
    """A real, valid PNG (not a placeholder string) so fakes can be used
    interchangeably with the real Pillow-based adapters (e.g.
    PillowImageCompositor in integration tests), not just FakeImageCompositor."""
    mode = "L" if isinstance(value, int) else "RGB"
    buffer = BytesIO()
    PILImage.new(mode, size, color=value).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeImageSegmenter(ImageSegmenter):
    def __init__(self, mask_bytes: bytes | None = None) -> None:
        self._mask_bytes = mask_bytes if mask_bytes is not None else _solid_png((200, 200), 255)

    def segment(self, image_bytes: bytes, region: DetectedRegion) -> SegmentationResult:
        return SegmentationResult(mask_png_bytes=self._mask_bytes, width=200, height=200)


class FakeImageEditor(ImageEditor):
    """By default echoes back a fixed "edited" crop (a real PNG, sized to
    region_box, so it works with the real PillowImageCompositor too — not
    just FakeImageCompositor). Pass should_fail=True to exercise
    EditRegionUseCase's failure path. Reports the same stage sequence a
    real Qwen edit goes through, if given on_progress."""

    PROGRESS = (
        EditorProgress(EditorStage.READING_INSTRUCTION),
        EditorProgress(EditorStage.LOADING_MODEL),
        EditorProgress(EditorStage.GENERATING, 1, 2),
        EditorProgress(EditorStage.GENERATING, 2, 2),
        EditorProgress(EditorStage.DECODING),
    )

    def __init__(self, should_fail: bool = False) -> None:
        self._should_fail = should_fail

    def edit(
        self,
        *,
        image_png_bytes: bytes,
        mask_png_bytes: bytes,
        region_box: BoundingBox,
        operation: EditOperation,
        color: GarmentColor | None = None,
        reference_image_png_bytes: bytes | None = None,
        on_progress: Callable[[EditorProgress], None] | None = None,
    ) -> EditResult:
        if self._should_fail:
            raise RuntimeError("fake editor failure")
        for progress in self.PROGRESS if on_progress else ():
            on_progress(progress)
        return EditResult(
            edited_region_png_bytes=_solid_png((region_box.width, region_box.height), (0, 255, 0)),
            region_box_used=region_box,
            seed=42,
            model_metadata={"operation": operation.value, "color": color},
        )


class RecordingProgressTracker(EditProgressTracker):
    def __init__(self) -> None:
        self.reports: list[tuple[str, EditProgress]] = []

    def report(self, progress_id: str, progress: EditProgress) -> None:
        self.reports.append((progress_id, progress))

    def get(self, progress_id: str) -> EditProgress | None:
        matching = [p for pid, p in self.reports if pid == progress_id]
        return matching[-1] if matching else None


class FakeImageCompositor(ImageCompositor):
    def composite(
        self,
        *,
        original_png_bytes: bytes,
        edited_region_png_bytes: bytes,
        region_box: BoundingBox,
        mask_png_bytes: bytes,
        grow_px: int,
        feather_px: int,
    ) -> bytes:
        return b"COMPOSITED:" + original_png_bytes + b"+" + edited_region_png_bytes
