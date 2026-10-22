"""Safe public errors; never serialize exception text, SQL, credentials or request input."""

import logging
from enum import StrEnum
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.catalog.schemas import SpecVersion
from app.common.types import DTO, Quote

logger = logging.getLogger(__name__)


class ErrorCode(StrEnum):
    COMMAND_REJECTED = "COMMAND_REJECTED"
    MATERIAL_UNAVAILABLE = "MATERIAL_UNAVAILABLE"
    INPUT_INVALID = "INPUT_INVALID"
    SPEC_DISABLED = "SPEC_DISABLED"
    QUOTE_STALE = "QUOTE_STALE"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    INSUFFICIENT_CREDITS = "INSUFFICIENT_CREDITS"
    ADJUSTMENT_TARGET_DELETED = "ADJUSTMENT_TARGET_DELETED"
    CAPACITY_INSUFFICIENT = "CAPACITY_INSUFFICIENT"
    FEATURE_NOT_ENABLED = "FEATURE_NOT_ENABLED"
    RATE_LIMITED = "RATE_LIMITED"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorDetail(DTO):
    code: ErrorCode
    message: str
    current_quotes: list[Quote] | None = None
    current_specs: list[SpecVersion] | None = None


class ErrorResponse(DTO):
    error: ErrorDetail
    trace_id: UUID


def error_response(
    status: int, code: ErrorCode, message: str, *, current_quotes=None, current_specs=None
) -> JSONResponse:
    trace_id = uuid4()
    payload = ErrorResponse(
        error=ErrorDetail(
            code=code, message=message, current_quotes=current_quotes, current_specs=current_specs
        ),
        trace_id=trace_id,
    )
    return JSONResponse(
        status_code=status,
        content=payload.model_dump(mode="json"),
        headers={"X-Trace-ID": str(trace_id)},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return error_response(422, ErrorCode.INPUT_INVALID, "请求参数无效，请检查后重试。")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        if request.url.path == "/api/v1/assist/prompts" and exc.status_code in (503, 504):
            message = {
                503: "AI 辅助服务暂时不可用，请稍后重试；若持续失败，请联系管理员检查模型配置。",
                504: "AI 辅助响应超时，请稍后重试。原创作指令已保留。",
            }[exc.status_code]
            return error_response(exc.status_code, ErrorCode.INTERNAL_ERROR, message)
        code = {
            401: ErrorCode.UNAUTHENTICATED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            405: ErrorCode.METHOD_NOT_ALLOWED,
            429: ErrorCode.RATE_LIMITED,
        }.get(exc.status_code, ErrorCode.INPUT_INVALID)
        return error_response(exc.status_code, code, "请求无法完成。")

    # Middleware handles ordinary runtime errors before the ASGI server can log private text.
    @app.middleware("http")
    async def sanitize_unexpected_errors(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            response = error_response(500, ErrorCode.INTERNAL_ERROR, "服务暂时不可用，请稍后重试。")
            details = getattr(getattr(exc, "orig", None), "args", ())
            code = details[0] if details and type(details[0]) is int else "unknown"
            logger.error(
                "request_failed trace_id=%s error_type=%s database_code=%s",
                response.headers["X-Trace-ID"], type(exc).__name__, code,
            )
            return response
