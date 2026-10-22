"""Application factory. Importing this module never opens a database connection."""

import os
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from redis import Redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.admin.media_agents import router as media_agents_router
from app.admin.routes import router as admin_router
from app.admin.text_models import default_router as text_default_router
from app.admin.text_models import router as text_models_router
from app.admin.text_models import service_router as text_service_router
from app.admin.user_management import router as user_management_router
from app.agents.callbacks import router as callbacks_router
from app.agents.media_http import MediaServiceError
from app.agents.model_configs import TextModelError
from app.assist.routes import router as assist_router
from app.auth.routes import router as auth_router
from app.catalog.routes import router as catalog_router
from app.catalog.service import CatalogError
from app.common.errors import ErrorCode, ErrorResponse, error_response, register_error_handlers
from app.common.health import LiveResponse, ReadyResponse
from app.common.openapi import install_openapi
from app.config import Settings, load_runtime_settings
from app.conversations.routes import router as conversations_router
from app.db import create_db_engine, database_schema_current
from app.events.fragments import TestFragmentHub
from app.events.routes import router as events_router
from app.investigations.routes import router as investigations_router
from app.ledger.routes import router as ledger_router
from app.ledger.service import LedgerError
from app.policies.service import PolicyGateError
from app.quick_generation.errors import QuickGenerationError
from app.quick_generation.routes import router as quick_generation_router
from app.site.routes import router as site_router
from app.storage.capacity import StorageError
from app.storage.routes import router as storage_router
from app.storage.validation import FileValidationError
from app.tasks.admission import MaterialUnavailable
from app.tasks.media_routes import router as media_tasks_router
from app.tasks.routes import router as tasks_router
from app.tasks.state_machine import TransitionError
from app.works.lifecycle_routes import router as lifecycle_router
from app.works.routes import router as works_router


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
    application.include_router(quick_generation_router)

    @application.exception_handler(QuickGenerationError)
    async def quick_generation_error(request, exc):
        return error_response(exc.status_code, ErrorCode.INPUT_INVALID,
                              exc.detail if isinstance(exc.detail, str) else "请求无法完成。")
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
    application.state.event_fragments = (
        TestFragmentHub() if settings.mode == "mock" and settings.test_only else None
    )
    application.include_router(callbacks_router)
    application.include_router(auth_router)
    application.include_router(admin_router)
    application.include_router(user_management_router)
    application.include_router(text_models_router)
    application.include_router(text_service_router)
    application.include_router(text_default_router)
    application.include_router(media_agents_router)
    application.include_router(site_router)
    application.include_router(assist_router)
    application.include_router(catalog_router)
    application.include_router(storage_router)
    application.include_router(conversations_router)
    application.include_router(tasks_router)
    application.include_router(media_tasks_router)
    application.include_router(works_router)
    application.include_router(lifecycle_router)
    application.include_router(ledger_router)
    application.include_router(investigations_router)
    application.include_router(events_router)
    register_error_handlers(application)

    @application.exception_handler(MediaServiceError)
    async def media_service_error(request, exc):
        status = exc.status_code if exc.status_code in {404, 409, 413, 422, 429} else 503
        code = (ErrorCode.COMMAND_REJECTED if getattr(exc, "command_rejected", False)
                else ErrorCode.INPUT_INVALID)
        return error_response(status, code, exc.public_message or {
            404: "服务配置或原任务不存在，请刷新后重试。",
            409: "配置或任务状态已更新，当前输入已保留，请重新打开编辑或核对原操作。",
            413: "内容超过服务允许的大小。",
            422: "服务拒绝了参数，请检查必填字段与配置关系。",
            429: "服务繁忙，请稍后重试。",
        }.get(status, "图片或视频服务暂不可用，请检查服务连接与访问权限。"))

    @application.exception_handler(TextModelError)
    async def text_model_error(request, exc):
        messages = {
            409: "模型配置版本已更新，草稿已保留。请刷新并核对最新配置后重试。",
            422: "文本服务拒绝了配置，请检查模型地址、名称和参数。",
            404: "文本模型配置不存在，请刷新列表。",
            429: "文本服务请求过于频繁，请稍后重试。",
        }
        return error_response(
            exc.status_code,
            ErrorCode.INPUT_INVALID,
            exc.public_message or messages.get(
                exc.status_code,
                "文本模型服务未配置或暂时不可用，请检查后端服务配置与访问权限。",
            ),
        )

    from app.operations.telemetry import install_http_logging

    install_http_logging(application)

    @application.exception_handler(MaterialUnavailable)
    async def material_unavailable(request, exc):
        return error_response(
            exc.status_code,
            ErrorCode.MATERIAL_UNAVAILABLE,
            "原素材已不可用，请重新上传并确认新报价。",
        )

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
            "当前价格未配置或报价已更新，请核对费用后重新确认。",
            current_quotes=exc.current_quotes,
            current_specs=exc.current_specs,
        )

    @application.exception_handler(LedgerError)
    async def ledger_error(request, exc):
        return error_response(exc.status_code, ErrorCode(exc.code), "请求无法完成。")

    @application.exception_handler(PolicyGateError)
    async def policy_error(request, exc):
        return error_response(403, ErrorCode.FEATURE_NOT_ENABLED, "当前功能尚未启用。")

    @application.exception_handler(TransitionError)
    async def transition_error(request, exc):
        return error_response(409, ErrorCode.IDEMPOTENCY_CONFLICT, "当前状态或证据不允许此操作。")

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
                    database_ok = (
                        connection.execute(text("SELECT 1")).scalar_one() == 1
                        and database_schema_current(connection)
                    )
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
    return create_app(load_runtime_settings())
