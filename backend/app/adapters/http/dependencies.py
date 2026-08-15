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
from app.application.use_cases.list_operations_for_region import ListOperationsForRegionUseCase
from app.application.use_cases.upload_image import UploadImageUseCase
from app.domain.ports.image_repository import ImageRepository
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
