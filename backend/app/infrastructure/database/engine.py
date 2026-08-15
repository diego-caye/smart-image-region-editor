from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

from app.infrastructure.config.settings import Settings


def make_engine(settings: Settings):
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, connect_args=connect_args)


def init_db(engine) -> None:
    """Create tables that don't exist yet. No Alembic for the MVP on
    purpose — see docs/architecture.md for when to introduce it."""
    from app.infrastructure.database import models  # noqa: F401 - registers tables with SQLModel

    SQLModel.metadata.create_all(engine)


def make_session(engine) -> Session:
    return Session(engine)
