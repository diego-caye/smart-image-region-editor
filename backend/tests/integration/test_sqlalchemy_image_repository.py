"""Integration test for the real persistence adapter against a real (temp
file) SQLite database — proves the SQLModel<->Domain mapping round-trips
correctly, which the in-memory fakes used elsewhere can't verify.
"""

from __future__ import annotations

from app.adapters.persistence.sqlalchemy_image_repository import SqlAlchemyImageRepository
from app.domain.entities.edit import Edit
from app.domain.entities.edit_session import EditSession
from app.domain.entities.image import Image
from app.domain.entities.mask import Mask
from app.domain.entities.region import DetectedRegion
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.region_type import RegionType
from app.infrastructure.config.settings import Settings
from app.infrastructure.database.engine import init_db, make_engine, make_session


def _repo_for(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}")
    engine = make_engine(settings)
    init_db(engine)
    session = make_session(engine)
    return SqlAlchemyImageRepository(session)


def test_image_round_trips(tmp_path):
    repo = _repo_for(tmp_path)
    image = Image.new(
        storage_ref="original/abc.png",
        original_filename="selfie.png",
        content_type="image/png",
        width=800,
        height=600,
    )
    repo.save_image(image)

    loaded = repo.get_image(image.id)
    assert loaded is not None
    assert loaded.storage_ref == "original/abc.png"
    assert loaded.width == 800


def test_region_with_bounding_box_round_trips(tmp_path):
    repo = _repo_for(tmp_path)
    region = DetectedRegion.new(
        image_id=Image.new(
            storage_ref="x", original_filename="x", content_type="image/png", width=1, height=1
        ).id,
        region_type=RegionType.RIGHT_HAND,
        bounding_box=BoundingBox(x_min=10, y_min=20, x_max=110, y_max=220),
        confidence=0.87,
    )
    repo.save_regions([region])

    loaded = repo.get_region(region.id)
    assert loaded is not None
    assert loaded.region_type == RegionType.RIGHT_HAND
    assert loaded.bounding_box.as_xyxy() == (10, 20, 110, 220)
    assert loaded.confidence == 0.87
    assert loaded.mask_id is None


def test_region_mask_link_updates(tmp_path):
    repo = _repo_for(tmp_path)
    region = DetectedRegion.new(
        image_id=Image.new(
            storage_ref="x", original_filename="x", content_type="image/png", width=1, height=1
        ).id,
        region_type=RegionType.FACE,
        bounding_box=BoundingBox(x_min=0, y_min=0, x_max=10, y_max=10),
        confidence=0.5,
    )
    repo.save_regions([region])

    mask = Mask.new(region_id=region.id, storage_ref="mask/1.png", width=800, height=600)
    repo.save_mask(mask)
    repo.update_region(region.with_mask(mask.id))

    loaded_region = repo.get_region(region.id)
    assert loaded_region.mask_id == mask.id
    loaded_mask = repo.get_mask(mask.id)
    assert loaded_mask.storage_ref == "mask/1.png"


def test_edit_session_and_edit_round_trip(tmp_path):
    repo = _repo_for(tmp_path)
    image = Image.new(
        storage_ref="original/1.png",
        original_filename="x.png",
        content_type="image/png",
        width=1,
        height=1,
    )
    repo.save_image(image)

    session = EditSession.new(image_id=image.id, original_image_ref=image.storage_ref)
    repo.save_edit_session(session)

    edit = Edit.new(
        session_id=session.id,
        region_id=image.id,  # any uuid works for this round-trip test
        operation=EditOperation.PEACE_SIGN,
        source_image_ref=image.storage_ref,
    )
    edit.mark_processing()
    edit.mark_preview_ready("preview/1.png", seed=99, model_metadata={"steps": 4})
    repo.save_edit(edit)

    session.record_edit(edit.id)
    session.advance_after_confirm("preview/1.png")
    repo.save_edit_session(session)

    loaded_session = repo.get_edit_session_for_image(image.id)
    assert loaded_session.current_image_ref == "preview/1.png"
    assert loaded_session.edit_ids == [edit.id]

    loaded_edit = repo.get_edit(edit.id)
    assert loaded_edit.status.value == "preview_ready"
    assert loaded_edit.seed == 99
    assert loaded_edit.model_metadata == {"steps": 4}
