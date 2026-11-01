"""Implements ImageRepository on top of SQLModel/SQLAlchemy. This is the
translation boundary between Domain entities and the SQL schema
(infrastructure/database/models.py) — the mapping functions at the bottom
are the whole point of this module living in adapters/ rather than
infrastructure/.
"""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.domain.entities.edit import Edit, EditStatus
from app.domain.entities.edit_session import EditSession
from app.domain.entities.image import Image
from app.domain.entities.mask import Mask
from app.domain.entities.region import DetectedRegion
from app.domain.ports.image_repository import ImageRepository
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor
from app.domain.value_objects.mask_scope import MaskScope
from app.domain.value_objects.region_type import RegionType
from app.infrastructure.database.models import EditRow, EditSessionRow, ImageRow, MaskRow, RegionRow


class SqlAlchemyImageRepository(ImageRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Image ---

    def save_image(self, image: Image) -> None:
        self._session.merge(_image_to_row(image))
        self._session.commit()

    def get_image(self, image_id: UUID) -> Image | None:
        row = self._session.get(ImageRow, image_id)
        return _row_to_image(row) if row else None

    # --- Regions ---

    def save_regions(self, regions: list[DetectedRegion]) -> None:
        for region in regions:
            self._session.merge(_region_to_row(region))
        self._session.commit()

    def get_regions_for_image(self, image_id: UUID) -> list[DetectedRegion]:
        rows = self._session.exec(select(RegionRow).where(RegionRow.image_id == image_id)).all()
        return [_row_to_region(row) for row in rows]

    def get_region(self, region_id: UUID) -> DetectedRegion | None:
        row = self._session.get(RegionRow, region_id)
        return _row_to_region(row) if row else None

    def update_region(self, region: DetectedRegion) -> None:
        self._session.merge(_region_to_row(region))
        self._session.commit()

    # --- Masks ---

    def save_mask(self, mask: Mask) -> None:
        self._session.merge(_mask_to_row(mask))
        self._session.commit()

    def get_mask(self, mask_id: UUID) -> Mask | None:
        row = self._session.get(MaskRow, mask_id)
        return _row_to_mask(row) if row else None

    def get_masks_for_region(self, region_id: UUID) -> list[Mask]:
        rows = self._session.exec(select(MaskRow).where(MaskRow.region_id == region_id)).all()
        return [_row_to_mask(row) for row in rows]

    # --- Edit sessions ---

    def save_edit_session(self, session: EditSession) -> None:
        self._session.merge(_edit_session_to_row(session))
        self._session.commit()

    def get_edit_session(self, session_id: UUID) -> EditSession | None:
        row = self._session.get(EditSessionRow, session_id)
        return _row_to_edit_session(row) if row else None

    def get_edit_session_for_image(self, image_id: UUID) -> EditSession | None:
        row = self._session.exec(
            select(EditSessionRow).where(EditSessionRow.image_id == image_id)
        ).first()
        return _row_to_edit_session(row) if row else None

    # --- Edits ---

    def save_edit(self, edit: Edit) -> None:
        self._session.merge(_edit_to_row(edit))
        self._session.commit()

    def get_edit(self, edit_id: UUID) -> Edit | None:
        row = self._session.get(EditRow, edit_id)
        return _row_to_edit(row) if row else None

    def get_edits_for_session(self, session_id: UUID) -> list[Edit]:
        rows = self._session.exec(select(EditRow).where(EditRow.session_id == session_id)).all()
        return [_row_to_edit(row) for row in rows]


# --- Mappers: Domain entity <-> SQLModel row. Kept private and colocated so
# the schema and its translation stay in lockstep. ---


def _image_to_row(image: Image) -> ImageRow:
    return ImageRow(
        id=image.id,
        storage_ref=image.storage_ref,
        original_filename=image.original_filename,
        content_type=image.content_type,
        width=image.width,
        height=image.height,
        created_at=image.created_at,
    )


def _row_to_image(row: ImageRow) -> Image:
    return Image(
        id=row.id,
        storage_ref=row.storage_ref,
        original_filename=row.original_filename,
        content_type=row.content_type,
        width=row.width,
        height=row.height,
        created_at=row.created_at,
    )


def _region_to_row(region: DetectedRegion) -> RegionRow:
    box = region.bounding_box
    return RegionRow(
        id=region.id,
        image_id=region.image_id,
        region_type=region.region_type.value,
        x_min=box.x_min,
        y_min=box.y_min,
        x_max=box.x_max,
        y_max=box.y_max,
        confidence=region.confidence,
        mask_id=region.mask_id,
    )


def _row_to_region(row: RegionRow) -> DetectedRegion:
    return DetectedRegion(
        id=row.id,
        image_id=row.image_id,
        region_type=RegionType(row.region_type),
        bounding_box=BoundingBox(x_min=row.x_min, y_min=row.y_min, x_max=row.x_max, y_max=row.y_max),
        confidence=row.confidence,
        mask_id=row.mask_id,
    )


def _mask_to_row(mask: Mask) -> MaskRow:
    return MaskRow(
        id=mask.id,
        region_id=mask.region_id,
        storage_ref=mask.storage_ref,
        width=mask.width,
        height=mask.height,
        feather_px=mask.feather_px,
        grow_px=mask.grow_px,
        scope=mask.scope.value,
    )


def _row_to_mask(row: MaskRow) -> Mask:
    return Mask(
        id=row.id,
        region_id=row.region_id,
        storage_ref=row.storage_ref,
        width=row.width,
        height=row.height,
        feather_px=row.feather_px,
        grow_px=row.grow_px,
        scope=MaskScope(row.scope) if row.scope else MaskScope.WHOLE_REGION,
    )


def _edit_session_to_row(session: EditSession) -> EditSessionRow:
    return EditSessionRow(
        id=session.id,
        image_id=session.image_id,
        current_image_ref=session.current_image_ref,
        edit_ids=[str(edit_id) for edit_id in session.edit_ids],
    )


def _row_to_edit_session(row: EditSessionRow) -> EditSession:
    return EditSession(
        id=row.id,
        image_id=row.image_id,
        current_image_ref=row.current_image_ref,
        edit_ids=[UUID(edit_id) for edit_id in row.edit_ids],
    )


def _edit_to_row(edit: Edit) -> EditRow:
    return EditRow(
        id=edit.id,
        session_id=edit.session_id,
        region_id=edit.region_id,
        operation=edit.operation.value,
        color=edit.color.value if edit.color else None,
        source_image_ref=edit.source_image_ref,
        status=edit.status.value,
        preview_ref=edit.preview_ref,
        final_ref=edit.final_ref,
        seed=edit.seed,
        model_metadata=edit.model_metadata,
        error_message=edit.error_message,
        created_at=edit.created_at,
        updated_at=edit.updated_at,
    )


def _row_to_edit(row: EditRow) -> Edit:
    return Edit(
        id=row.id,
        session_id=row.session_id,
        region_id=row.region_id,
        operation=EditOperation(row.operation),
        color=GarmentColor(row.color) if row.color else None,
        source_image_ref=row.source_image_ref,
        status=EditStatus(row.status),
        preview_ref=row.preview_ref,
        final_ref=row.final_ref,
        seed=row.seed,
        model_metadata=row.model_metadata,
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
