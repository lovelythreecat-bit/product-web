"""Shared session boundary: service code must not commit independently."""

from collections.abc import Iterator
from pathlib import Path

from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import Request
from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session

from app.config import Settings


class Base(DeclarativeBase):
    pass


def database_schema_current(connection: Connection) -> bool:
    """A reachable database is usable only after all bundled migrations ran."""
    migrations = ScriptDirectory(str(Path(__file__).resolve().parents[1] / "migrations"))
    expected = set(migrations.get_heads())
    current = set(MigrationContext.configure(connection).get_current_heads())
    return bool(expected) and current == expected


def create_db_engine(settings: Settings) -> Engine | None:
    if settings.database_url is None:
        return None
    url = make_url(settings.database_url.get_secret_value())
    if url.drivername != "mysql+pymysql":
        raise ValueError("The platform requires mysql+pymysql (MySQL 8.4)")
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={"connect_timeout": 3, "read_timeout": 3, "write_timeout": 3},
        hide_parameters=True,
    )


def get_session(request: Request) -> Iterator[Session]:
    """One request, one shared session; caller owns commit, close rolls back otherwise."""
    engine = request.app.state.engine
    if engine is None:
        raise RuntimeError("Database is not configured")
    with Session(
        engine,
        expire_on_commit=False,
        info={"read_only_request": request.method in {"GET", "HEAD", "OPTIONS"}},
    ) as session:
        yield session
