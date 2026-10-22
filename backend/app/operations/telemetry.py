"""Allowlisted structured telemetry. Never log requests, credentials or adapter errors."""

import json
import logging
from time import monotonic
from uuid import UUID, uuid4

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse

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


def stage_diagnostic(*, stage, task_id=None, event_id=None, state_version=None,
                     action=None, lease=None, error=None, code=None, http_status=None,
                     outcome=None):
    """Fixed vocabulary only: exception strings and arbitrary codes are never emitted."""
    payload = {"event": "task_stage_diagnostic"}
    if stage in {"dispatch", "consume", "upstream", "reducer", "publish",
                 "investigation", "worker"}:
        payload["stage"] = stage
    for key, value in (("task_id", task_id), ("event_id", event_id)):
        if identity(value):
            payload[key] = identity(value)
    for key, value in (("state_version", state_version),
                       ("fencing_token", getattr(lease, "fencing_token", None))):
        if type(value) is int and value >= 0:
            payload[key] = value
    if action in {"prepare_submission", "reconcile_submission", "query_original",
                  "investigate", "save_original"}:
        payload["action"] = action
    if code in {"LEASE_LOST", "UPSTREAM_NEEDS_INPUT", "UPSTREAM_ACCEPTANCE_UNCONFIRMED",
                "UPSTREAM_BINDING_UNAVAILABLE", "UPSTREAM_IDENTITY_CONFLICT",
                "CALLBACK_EVENT_CONFLICT", "NO_PROGRESS", "STAGE_EXCEPTION",
                "DEADLINE_EXCEEDED", "POLICY_BLOCKED", "EVIDENCE_MISMATCH",
                "RESULT_MANIFEST_MISMATCH", "RESULT_POLICY_UNAVAILABLE", "EVENT_REPLAY_CONFLICT",
                "OBSERVATION_IDENTITY", "IDENTITY_MISMATCH", "TERMINAL_LATE"}:
        payload["code"] = code
    if outcome in {"ok", "error", "handled", "unhandled", "failed", "wait", "no_progress"}:
        payload["outcome"] = outcome
    if type(http_status) is int and 100 <= http_status <= 599:
        payload["http_status"] = http_status
    if error is not None:
        name = type(error).__name__
        payload["error_type"] = name if name in {
            "ValueError", "LookupError", "KeyError", "TypeError", "OSError", "TimeoutError",
            "IntegrityError", "OperationalError", "SQLAlchemyError", "TransitionError",
            "MediaServiceError", "ConnectionError", "HTTPError", "ValidationError",
        } else "Exception"
    logger.info(json.dumps(payload, separators=(",", ":")))


def install_http_logging(application):
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())
        logger.propagate = False

    class OperationalLog:
        """Observe ASGI sends directly, without prefetching authorized file blocks."""

        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                return await self.app(scope, receive, send)
            trace, start = str(uuid4()), monotonic()
            outcome = "error"

            async def send_response(message):
                nonlocal trace, outcome
                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    # Preserve the application's error trace for support correlation.
                    trace = identity(headers.get("X-Trace-ID")) or trace
                    headers["X-Trace-ID"] = trace
                    outcome = "ok" if message["status"] < 500 else "error"
                await send(message)

            try:
                root = application.state.settings.storage_root
                if root is not None and (root / ".restore-isolated.json").exists():
                    response = JSONResponse(
                        status_code=503,
                        content={"code": "RESTORE_ISOLATED"},
                        headers={"Cache-Control": "no-store", "X-Trace-ID": trace},
                    )
                    await response(scope, receive, send_response)
                else:
                    await self.app(scope, receive, send_response)
            finally:
                event(
                    "http", trace_id=trace, elapsed_ms=(monotonic() - start) * 1000, outcome=outcome
                )

    application.add_middleware(OperationalLog)
