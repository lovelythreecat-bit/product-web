"""Migration CLI takes APP_DATABASE_URL; tests supply an isolated connection."""

from alembic import context

from app.agents import media_connection, media_execution  # noqa: F401
from app.config import load_runtime_settings
from app.db import Base, create_db_engine
from app.quick_generation import models as quick_generation_models  # noqa: F401

config = context.config
target_metadata = Base.metadata


def run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    settings = load_runtime_settings()
    if settings.database_url is None:
        raise RuntimeError("APP_DATABASE_URL is required for migrations")
    context.configure(
        url=settings.database_url.get_secret_value(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    run_migrations(config.attributes["connection"])
else:
    engine = create_db_engine(load_runtime_settings())
    if engine is None:
        raise RuntimeError("APP_DATABASE_URL is required for migrations")
    try:
        with engine.connect() as connection:
            run_migrations(connection)
    finally:
        engine.dispose()
