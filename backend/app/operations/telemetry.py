"""Allowlisted structured telemetry. Never log requests, credentials or adapter errors."""

import json
import logging
from time import monotonic
from uuid import UUID, uuid4

logger = logging.getLogger("operations")
logger.setLevel(logging.INFO)


def identity(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def event(kind, *, trace_id=None, task_id=None, elapsed_ms=None, outcome=None):
    if kind not in {"http", "task_stage"}:
        raise ValueError("Unknown telemetry event")
    payload = {"event": kind, "trace_id": identity(trace_id) or str(uuid4())}
    if identity(task_id):
        payload["task_id"] = identity(task_id)
    if elapsed_ms is not None:
        payload["elapsed_ms"] = round(max(0, elapsed_ms), 2)
    if outcome in {"ok", "error", "handled", "unhandled", "failed"}:
        payload["outcome"] = outcome
    logger.info(json.dumps(payload, separators=(",", ":")))


def install_http_logging(application):
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())
        logger.propagate = False

    @application.middleware("http")
    async def operational_log(request, call_next):
        trace, start = str(uuid4()), monotonic()
        outcome = "error"
        try:
            root = application.state.settings.storage_root
            if root is not None and (root / ".restore-isolated.json").exists():
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=503,
                    content={"code": "RESTORE_ISOLATED"},
                    headers={"Cache-Control": "no-store", "X-Trace-ID": trace},
                )
            response = await call_next(request)
            # Preserve the application's error trace so support can correlate it.
            trace = identity(response.headers.get("X-Trace-ID")) or trace
            response.headers["X-Trace-ID"] = trace
            outcome = "ok" if response.status_code < 500 else "error"
            return response
        finally:
            event("http", trace_id=trace, elapsed_ms=(monotonic() - start) * 1000, outcome=outcome)
