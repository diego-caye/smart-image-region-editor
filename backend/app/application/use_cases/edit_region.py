from __future__ import annotations

from typing import TYPE_CHECKING

from app.application.dto.edit_region import EditRegionRequest, EditRegionResult
from app.domain.entities.edit import Edit
from app.domain.entities.mask import Mask
from app.domain.ports.image_compositor import ImageCompositor
from app.domain.ports.image_editor import ImageEditor
from app.domain.ports.image_repository import ImageRepository
from app.domain.ports.image_segmenter import ImageSegmenter
from app.domain.ports.image_storage import ImageStorage
from app.domain.services.region_operation_rules import ensure_operation_allowed

if TYPE_CHECKING:
    from app.domain.entities.region import DetectedRegion

# Generous on purpose: an edit can change a region's silhouette (a closed
# fist opening into a spread-finger peace sign extends well past the
# fist's own outline) — a tight mask would clip the new shape. See
# PillowImageCompositor.
DEFAULT_MASK_GROW_PX = 40
DEFAULT_MASK_FEATHER_PX = 12


class ImageNotFound(ValueError):
    pass


class RegionNotFound(ValueError):
    pass


class EditSessionNotFound(ValueError):
    pass


class EditRegionUseCase:
    """The core localized-edit pipeline: ensure a precise mask exists for the
    region -> call the ImageEditor -> composite the result back onto the
    session's *current* image (the original, or the last confirmed edit) ->
    persist a PREVIEW_READY Edit. Nothing is applied to the "official" image
    until it's confirmed (see ConfirmEditUseCase).
    """

    def __init__(
        self,
        image_repository: ImageRepository,
        image_storage: ImageStorage,
        image_segmenter: ImageSegmenter,
        image_editor: ImageEditor,
        image_compositor: ImageCompositor,
        mask_grow_px: int = DEFAULT_MASK_GROW_PX,
        mask_feather_px: int = DEFAULT_MASK_FEATHER_PX,
    ) -> None:
        self._repo = image_repository
        self._storage = image_storage
        self._segmenter = image_segmenter
        self._editor = image_editor
        self._compositor = image_compositor
        self._mask_grow_px = mask_grow_px
        self._mask_feather_px = mask_feather_px

    def execute(self, request: EditRegionRequest) -> EditRegionResult:
        image = self._repo.get_image(request.image_id)
        if image is None:
            raise ImageNotFound(str(request.image_id))

        region = self._repo.get_region(request.region_id)
        if region is None or region.image_id != image.id:
            raise RegionNotFound(str(request.region_id))

        ensure_operation_allowed(region.region_type, request.operation)

        session = self._repo.get_edit_session_for_image(image.id)
        if session is None:
            raise EditSessionNotFound(str(image.id))

        edit = Edit.new(
            session_id=session.id,
            region_id=region.id,
            operation=request.operation,
            source_image_ref=session.current_image_ref,
        )
        self._repo.save_edit(edit)
        session.record_edit(edit.id)
        self._repo.save_edit_session(session)
        edit.mark_processing()
        self._repo.save_edit(edit)

        try:
            current_image_bytes = self._storage.load(session.current_image_ref)
            mask = self._get_or_create_mask(current_image_bytes, region)
            mask_bytes = self._storage.load(mask.storage_ref)

            editor_result = self._editor.edit(
                image_png_bytes=current_image_bytes,
                mask_png_bytes=mask_bytes,
                region_box=region.bounding_box,
                operation=request.operation,
            )

            composited_bytes = self._compositor.composite(
                original_png_bytes=current_image_bytes,
                edited_region_png_bytes=editor_result.edited_region_png_bytes,
                region_box=editor_result.region_box_used,
                mask_png_bytes=mask_bytes,
                grow_px=mask.grow_px,
                feather_px=self._mask_feather_px,
            )

            preview_ref = self._storage.save(composited_bytes, kind="preview")
            edit.mark_preview_ready(
                preview_ref, seed=editor_result.seed, model_metadata=editor_result.model_metadata
            )
            self._repo.save_edit(edit)

            return EditRegionResult(
                edit_id=edit.id, status=edit.status, preview_url=self._storage.url_for(preview_ref)
            )
        except Exception as exc:
            # Contained on purpose: a failed edit is a normal, expected outcome
            # (a flaky ComfyUI call, an OOM, ...) that must be recorded on the
            # Edit and reported to the caller, not surfaced as a bare 500.
            edit.mark_failed(str(exc))
            self._repo.save_edit(edit)
            return EditRegionResult(
                edit_id=edit.id, status=edit.status, preview_url=None, error_message=str(exc)
            )

    def _get_or_create_mask(self, image_bytes: bytes, region: DetectedRegion) -> Mask:
        if region.mask_id is not None:
            mask = self._repo.get_mask(region.mask_id)
            if mask is not None:
                return mask

        segmentation = self._segmenter.segment(image_bytes, region)
        mask_ref = self._storage.save(segmentation.mask_png_bytes, kind="mask")
        mask = Mask.new(
            region_id=region.id,
            storage_ref=mask_ref,
            width=segmentation.width,
            height=segmentation.height,
            feather_px=self._mask_feather_px,
            grow_px=self._mask_grow_px,
        )
        self._repo.save_mask(mask)
        self._repo.update_region(region.with_mask(mask.id))
        return mask
