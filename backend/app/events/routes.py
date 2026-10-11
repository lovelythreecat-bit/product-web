"""Cookie-only native EventSource. MySQL polling remains authoritative without Redis."""

import asyncio
from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Cookie, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse

from app.auth.service import AuthService
from app.common.errors import ErrorResponse
from app.events.models import DurableEvent
from app.events.schemas import DurableEventView, ResetEvent
from app.events.service import prune_events

router = APIRouter(prefix="/api/v1")


def same_origin(request):
    """Native same-origin GET may omit Origin. Fetch Metadata is sufficient in that case."""
    origin = request.headers.get("origin")
    site = request.headers.get("sec-fetch-site")
    expected = str(request.base_url).rstrip("/")
    if expected not in request.app.state.settings.auth_origins:
        raise HTTPException(403)
    if origin is not None and origin != expected:
        raise HTTPException(403)
    if site and site != "same-origin":
        raise HTTPException(403)
    if not origin and site != "same-origin":
        raise HTTPException(403)
    if any(key != "after" for key in request.query_params):
        # Credentials are never accepted in query strings.
        raise HTTPException(422)


def authenticate(engine, cookie):
    with Session(engine) as session, session.begin():
        return AuthService(session).require_active_principal(cookie)


def frame(kind, data, cursor=None):
    return (f"id: {cursor}\n" if cursor else "") + f"event: {kind}\ndata: {data}\n\n"


def read_next(engine, cookie, principal, cursor, retention, hub, subscription):
    # One event per batch: no queued private batch survives a subsequent revocation.
    # All synchronous SQL (including lock waits) runs in a worker thread. The Session
    # is committed/closed before this string crosses any ASGI network boundary.
    with Session(engine) as session, session.begin():
        current = AuthService(session).require_active_principal(cookie)
        if current != principal:
            raise HTTPException(401)
        uid = str(current.user_id)
        head = prune_events(session, uid, retention)
        seq = 0
        try:
            if cursor is not None:
                owner, raw_seq = cursor.split(":")
                if owner != uid or not raw_seq.isascii() or not raw_seq.isdecimal():
                    raise ValueError
                seq = int(raw_seq)
            if not head.pruned_through <= seq <= head.last_seq:
                raise ValueError
        except (ValueError, OverflowError):
            latest = f"{uid}:{head.last_seq}"
            return latest, frame("reset", ResetEvent().model_dump_json(), latest), True
        row = session.scalar(
            select(DurableEvent)
            .where(
                DurableEvent.user_id == uid,
                DurableEvent.event_seq > seq,
            )
            .order_by(DurableEvent.event_seq)
            .limit(1)
        )
        if row:
            latest = f"{uid}:{row.event_seq}"
            data = DurableEventView(
                event_seq=row.event_seq,
                payload=row.payload,
                created_at=row.created_at.replace(tzinfo=UTC),
            )
            return latest, frame("task.updated", data.model_dump_json(), latest), False
        fragment = hub.pop(subscription, uid) if hub is not None else None
        return cursor, frame("transient_fragment", fragment) if fragment else None, False


async def stream_events(request, principal, cookie, after):
    engine = request.app.state.engine
    hub = request.app.state.event_fragments
    subscription = hub.subscribe(principal.user_id) if hub else None
    try:
        while True:
            try:
                after, output, reset = await run_in_threadpool(
                    read_next,
                    engine,
                    cookie,
                    principal,
                    after,
                    request.app.state.settings.event_retention_seconds,
                    hub,
                    subscription,
                )
            except (HTTPException, SQLAlchemyError):
                return  # Fail closed; reconnect performs ordinary HTTP authentication.
            if output:
                yield output
                if reset:
                    return
            else:
                yield ": keep-alive\n\n"
                await asyncio.sleep(0.25)
    finally:
        if hub:
            hub.unsubscribe(subscription)


@router.get(
    "/events",
    operation_id="events_stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Native SSE: task.updated, reset, TEST_ONLY transient_fragment.",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        },
        **{status: {"model": ErrorResponse} for status in (401, 403, 503)},
    },
    description=(
        "Same-origin Secure HttpOnly cookie EventSource. Origin may be absent when "
        "Sec-Fetch-Site is same-origin; no custom CSRF or X-Requested-With header. "
        "Cursor is the opaque SSE id (user UUID:sequence); Last-Event-ID takes precedence "
        "over after. Invalid, foreign, ahead or expired cursors receive a generic reset "
        "with this user's current cursor and the stream closes. GET original persisted "
        "resources after reset; never POST a replacement task. Default transport retention "
        "is 7 days; permanent sequence and deduplication receipts are retained. "
        "Unstored fragments have no id and cannot be replayed. Real upstream streaming "
        "is disabled pending D-01. Redis is unnecessary for correctness."
    ),
)
async def events(
    request: Request,
    cookie: Annotated[str | None, Cookie(alias="session")] = None,
    after: Annotated[str | None, Query(max_length=128)] = None,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID", max_length=128)] = None,
):
    same_origin(request)
    if request.app.state.engine is None:
        raise HTTPException(503)
    principal = await run_in_threadpool(authenticate, request.app.state.engine, cookie)
    return StreamingResponse(
        stream_events(request, principal, cookie, last_event_id or after),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
