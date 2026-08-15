"""In-memory fake adapters implementing every Domain Port.

These exist so Application use cases can be exercised without any real
database, filesystem, GPU model, or ComfyUI server — and they double as
living documentation of what each Port contract actually requires from a
real adapter.
"""

from __future__ import annotations

from itertools import count
from uuid import UUID

from app.domain.entities.edit import Edit
from app.domain.entities.edit_session import EditSession
from app.domain.entities.image import Image
from app.domain.entities.mask import Mask
from app.domain.entities.region import DetectedRegion
from app.domain.ports.image_compositor import ImageCompositor
from app.domain.ports.image_detector import ImageDetector
from app.domain.ports.image_editor import EditResult, ImageEditor
from app.domain.ports.image_repository import ImageRepository
from app.domain.ports.image_segmenter import ImageSegmenter, SegmentationResult
from app.domain.ports.image_storage import ImageStorage
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.edit_operation import EditOperation


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


class FakeImageSegmenter(ImageSegmenter):
    def __init__(self, mask_bytes: bytes = b"FAKE-MASK") -> None:
        self._mask_bytes = mask_bytes

    def segment(self, image_bytes: bytes, region: DetectedRegion) -> SegmentationResult:
        return SegmentationResult(mask_png_bytes=self._mask_bytes, width=200, height=200)


class FakeImageEditor(ImageEditor):
    """By default echoes back a fixed "edited" crop. Pass should_fail=True to
    exercise the EditRegionUseCase's failure path."""

    def __init__(self, should_fail: bool = False) -> None:
        self._should_fail = should_fail

    def edit(
        self,
        *,
        image_png_bytes: bytes,
        mask_png_bytes: bytes,
        region_box: BoundingBox,
        operation: EditOperation,
        reference_image_png_bytes: bytes | None = None,
    ) -> EditResult:
        if self._should_fail:
            raise RuntimeError("fake editor failure")
        return EditResult(
            edited_region_png_bytes=b"FAKE-EDITED-REGION",
            region_box_used=region_box,
            seed=42,
            model_metadata={"operation": operation.value},
        )


class FakeImageCompositor(ImageCompositor):
    def composite(
        self,
        *,
        original_png_bytes: bytes,
        edited_region_png_bytes: bytes,
        region_box: BoundingBox,
        mask_png_bytes: bytes,
        feather_px: int,
    ) -> bytes:
        return b"COMPOSITED:" + original_png_bytes + b"+" + edited_region_png_bytes
