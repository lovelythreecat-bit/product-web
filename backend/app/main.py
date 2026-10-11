"""Application factory. Importing this module never opens a database connection."""

import os
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from redis import Redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.agents.callbacks import router as callbacks_router
from app.auth.routes import router as auth_router
from app.catalog.routes import router as catalog_router
from app.catalog.service import CatalogError
from app.common.errors import ErrorCode, ErrorResponse, error_response, register_error_handlers
from app.common.health import LiveResponse, ReadyResponse
from app.common.openapi import install_openapi
from app.config import Settings
from app.conversations.routes import router as conversations_router
from app.db import create_db_engine
from app.ledger.service import LedgerError
from app.policies.service import PolicyGateError
from app.storage.capacity import StorageError
from app.storage.routes import router as storage_router
from app.storage.validation import FileValidationError
from app.tasks.routes import router as tasks_router


def create_app(settings: Settings) -> FastAPI:
    engine = create_db_engine(settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        yield
        if application.state.auth_redis is not None:
            application.state.auth_redis.close()
        if engine is not None:
            engine.dispose()

    application = FastAPI(
        title="Ecommerce AI Platform",
        version="0.1.0",
        lifespan=lifespan,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    )
    application.state.settings = settings
    application.state.engine = engine
    application.state.auth_redis = (
        Redis.from_url(
            settings.redis_url.get_secret_value(), socket_timeout=3, socket_connect_timeout=3
        )
        if settings.redis_url
        else None
    )
    application.state.auth_rate_prefix = "auth-rate:"
    application.include_router(callbacks_router)
    application.include_router(auth_router)
    application.include_router(catalog_router)
    application.include_router(storage_router)
    application.include_router(conversations_router)
    application.include_router(tasks_router)
    register_error_handlers(application)

    @application.exception_handler(FileValidationError)
    async def upload_validation_error(request, exc):
        return error_response(422, ErrorCode.INPUT_INVALID, exc.public_message)

    @application.exception_handler(StorageError)
    async def storage_error(request, exc):
        return error_response(exc.status_code, ErrorCode(exc.code), "存储请求无法完成。")

    @application.exception_handler(CatalogError)
    async def catalog_error(request, exc):
        return error_response(
            exc.status_code,
            ErrorCode(exc.code),
            "请检查规格并重新确认当前报价。",
            current_quotes=exc.current_quotes,
            current_specs=exc.current_specs,
        )

    @application.exception_handler(LedgerError)
    async def ledger_error(request, exc):
        return error_response(exc.status_code, ErrorCode(exc.code), "请求无法完成。")

    @application.exception_handler(PolicyGateError)
    async def policy_error(request, exc):
        return error_response(403, ErrorCode.FEATURE_NOT_ENABLED, "当前功能尚未启用。")

    install_openapi(application)

    @application.get("/api/v1/health/live", response_model=LiveResponse, operation_id="health_live")
    def live() -> dict:
        return {"live": True, "mode": settings.mode, "test_only": settings.test_only}

    @application.get(
        "/api/v1/health/ready",
        response_model=ReadyResponse,
        responses={503: {"model": ReadyResponse}},
        operation_id="health_ready",
    )
    def ready(response: Response) -> dict:
        storage_ok = False
        root = settings.storage_root
        if (
            settings.storage_persistent
            and root is not None
            and root.is_absolute()
            and root.is_dir()
        ):
            try:
                with tempfile.TemporaryFile(dir=root) as probe:
                    probe.write(b"readiness")
                    probe.flush()
                    os.fsync(probe.fileno())
                storage_ok = True
            except OSError:
                pass
        database_ok = False
        if engine is not None:
            try:
                with engine.connect() as connection:
                    database_ok = connection.execute(text("SELECT 1")).scalar_one() == 1
            except SQLAlchemyError:
                pass
        is_ready = storage_ok and database_ok
        response.status_code = 200 if is_ready else 503
        return {
            "ready": is_ready,
            "checks": {"storage": storage_ok, "database": database_ok},
            "mode": settings.mode,
            "test_only": settings.test_only,
        }

    return application


def application() -> FastAPI:
    """uvicorn app.main:application --factory"""
    return create_app(Settings())
