"""Safe public errors; never serialize exception text, SQL, credentials or request input."""

from enum import StrEnum
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.common.types import DTO, Quote


class ErrorCode(StrEnum):
    INPUT_INVALID = "INPUT_INVALID"
    SPEC_DISABLED = "SPEC_DISABLED"
    QUOTE_STALE = "QUOTE_STALE"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    INSUFFICIENT_CREDITS = "INSUFFICIENT_CREDITS"
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


class ErrorResponse(DTO):
    error: ErrorDetail
    trace_id: UUID


def error_response(status: int, code: ErrorCode, message: str) -> JSONResponse:
    trace_id = uuid4()
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message), trace_id=trace_id)
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
        except Exception:
            return error_response(500, ErrorCode.INTERNAL_ERROR, "服务暂时不可用，请稍后重试。")
