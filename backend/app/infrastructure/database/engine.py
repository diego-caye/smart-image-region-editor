from __future__ import annotations

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.infrastructure.config.settings import Settings


def make_engine(settings: Settings):
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, connect_args=connect_args)


# Operations that became one colored operation (operation_options.py):
# old name -> (new name, color). Rewritten in place so existing histories
# still load.
_LEGACY_OPERATIONS = {
    "red_shirt": ("shirt_color", "red"),
    "black_jacket": ("jacket", "black"),
    "white_tshirt": ("t_shirt", "white"),
}


def init_db(engine) -> None:
    """Create tables that don't exist yet, then apply the only kind of
    schema change made so far: new nullable columns. No Alembic for the
    MVP on purpose — see docs/architecture.md for when to introduce it."""
    from app.infrastructure.database import models  # noqa: F401 - registers tables with SQLModel

    SQLModel.metadata.create_all(engine)
    _add_missing_nullable_columns(engine)
    _migrate_legacy_operations(engine)


def _add_missing_nullable_columns(engine) -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            existing = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing or not column.nullable:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}'))


def _migrate_legacy_operations(engine) -> None:
    with engine.begin() as conn:
        for old, (new, color) in _LEGACY_OPERATIONS.items():
            conn.execute(
                text("UPDATE edits SET operation = :new, color = :color WHERE operation = :old"),
                {"new": new, "color": color, "old": old},
            )


def make_session(engine) -> Session:
    return Session(engine)
