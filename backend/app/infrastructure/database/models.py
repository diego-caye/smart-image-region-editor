"""SQLModel table definitions. These are storage schema, not Domain
entities — adapters/persistence/sqlalchemy_image_repository.py maps between
the two. Nothing outside adapters/persistence and this module should import
from here.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class ImageRow(SQLModel, table=True):
    __tablename__ = "images"

    id: UUID = Field(primary_key=True)
    storage_ref: str
    original_filename: str
    content_type: str
    width: int
    height: int
    created_at: datetime


class RegionRow(SQLModel, table=True):
    __tablename__ = "regions"

    id: UUID = Field(primary_key=True)
    image_id: UUID = Field(index=True)
    region_type: str
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    confidence: float
    mask_id: UUID | None = None


class MaskRow(SQLModel, table=True):
    __tablename__ = "masks"

    id: UUID = Field(primary_key=True)
    region_id: UUID = Field(index=True)
    storage_ref: str
    width: int
    height: int
    feather_px: int
    grow_px: int


class EditSessionRow(SQLModel, table=True):
    __tablename__ = "edit_sessions"

    id: UUID = Field(primary_key=True)
    image_id: UUID = Field(index=True, unique=True)
    current_image_ref: str
    edit_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))


class EditRow(SQLModel, table=True):
    __tablename__ = "edits"

    id: UUID = Field(primary_key=True)
    session_id: UUID = Field(index=True)
    region_id: UUID
    operation: str
    color: str | None = None
    source_image_ref: str
    status: str
    preview_ref: str | None = None
    final_ref: str | None = None
    seed: int | None = None
    model_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
