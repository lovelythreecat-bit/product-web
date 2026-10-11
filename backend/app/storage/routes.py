"""Authenticated binary streaming, with ownership checked before Range semantics."""

import hashlib
import re
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from anyio import CancelScope
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from redis import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from app.auth.models import User
from app.auth.routes import DB, PrincipalDep, require_csrf
from app.auth.service import AuthService
from app.common.errors import ErrorResponse
from app.common.types import FileVersionRef
from app.storage.capacity import release_capacity
from app.storage.local_store import LocalStore
from app.storage.models import CapacityReservation, File
from app.storage.service import UploadService

router = APIRouter(
    prefix="/api/v1",
    responses={
        status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 416, 422, 429, 503)
    },
)


def upload_limit(request, user_id):
    client = request.app.state.auth_redis
    if client is None:
        raise HTTPException(503)
    key = request.app.state.auth_rate_prefix + "upload:" + str(user_id)
    try:
        count = client.eval(
            "local n=redis.call('INCR',KEYS[1]); "
            "if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n",
            1,
            key,
        )
        if count > 20:
            raise HTTPException(429)
    except RedisError:
        raise HTTPException(503) from None


@router.post(
    "/files",
    response_model=FileVersionRef,
    status_code=201,
    operation_id="upload_file",
    dependencies=[Depends(require_csrf)],
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                **{
                    mime: {"schema": {"type": "string", "format": "binary"}}
                    for mime in ("image/png", "image/jpeg", "image/webp", "video/mp4")
                },
            },
        }
    },
)
async def upload(
    request: Request,
    session: DB,
    principal: PrincipalDep,
    display_name: Annotated[str, Query(min_length=1, max_length=200)],
    content_type: Annotated[str, Header(alias="Content-Type")],
):
    settings = request.app.state.settings
    if not settings.storage_persistent or settings.storage_policy_version is None:
        from app.policies.service import PolicyGateError

        raise PolicyGateError()
    store = await run_in_threadpool(LocalStore, settings.storage_root)
    service = UploadService(session, store, settings.storage_policy_version, mode=settings.mode)
    completion_commit_attempted = False

    def reserve_phase():
        upload_limit(request, principal.user_id)
        service.prepare_upload(principal, display_name)
        session.commit()

    def complete_phase():
        nonlocal completion_commit_attempted
        # A slow stream must not retain access after logout/account disable.
        AuthService(session, mode=settings.mode).require_active_principal(
            request.cookies.get("session")
        )
        service.finalize_upload()
        completion_commit_attempted = True
        session.commit()

    def abort_before_completion():
        if service.staged is not None:
            store.mark_aborted(service.staged)
        if service.reservation_id is not None:
            # This upload has never attempted a completion commit. A reservation
            # commit may be uncertain, but releasing its unused budget is safe.
            with Session(request.app.state.engine) as recovery:
                # Serialize with any still-finishing reservation transaction before
                # treating an absent row as proof that nothing was committed.
                recovery.scalar(
                    select(User.id).where(User.id == str(principal.user_id)).with_for_update()
                )
                found = recovery.scalar(
                    select(CapacityReservation.id).where(
                        CapacityReservation.id == service.reservation_id
                    )
                )
                if found is not None:
                    release_capacity(recovery, service.reservation_id)
                    recovery.commit()
        if service.staged is not None:
            store.discard(service.staged)

    try:
        # Each call finishes before another thread can touch this Session.
        await run_in_threadpool(reserve_phase)
        result = await service.upload_file(
            principal, request.stream(), display_name, declared_mime=content_type
        )
        await run_in_threadpool(complete_phase)
    except BaseException:
        with CancelScope(shield=True):
            await run_in_threadpool(session.rollback)
            if not completion_commit_attempted:
                try:
                    await run_in_threadpool(abort_before_completion)
                except Exception:
                    # Keep the durable reservation/journal for reconciliation if
                    # release cannot be confirmed; never invent success or expiry.
                    pass
        raise
    # No ambiguous completion is allowed to discard a possibly DB-owned blob.
    await run_in_threadpool(store.acknowledge, service.staged)
    return result


def parse_range(value, size):
    if value is None:
        return 0, size - 1, 200
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", value)
    if not match or not any(match.groups()) or len(value) > 80:
        raise HTTPException(416)
    left, right = match.groups()
    if not left:
        suffix = int(right)
        if suffix == 0:
            raise HTTPException(416)
        return max(0, size - suffix), size - 1, 206
    start, end = int(left), min(int(right), size - 1) if right else size - 1
    if start >= size or end < start:
        raise HTTPException(416)
    return start, end, 206


def authorize_download_chunk(engine, cookie, principal, file_id, version):
    """Fresh database authority; the transaction ends before the chunk is yielded."""
    with Session(engine) as current, current.begin():
        if AuthService(current).require_active_principal(cookie) != principal:
            raise HTTPException(401)
        available = current.scalar(
            select(File.id)
            .where(
                File.id == file_id,
                File.version == version,
                File.user_id == str(principal.user_id),
                File.deleted_at.is_(None),
                File.state == "durable",
            )
            .with_for_update(read=True)
        )
        if available is None:
            raise HTTPException(404)


@router.get(
    "/files/{file_id}/content",
    operation_id="read_file_content",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            }
        },
        206: {
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            }
        },
    },
)
def content(
    file_id: UUID,
    request: Request,
    session: DB,
    principal: PrincipalDep,
    range_header: Annotated[str | None, Header(alias="Range")] = None,
):
    file = session.scalar(
        select(File).where(
            File.id == str(file_id),
            File.user_id == str(principal.user_id),
            File.deleted_at.is_(None),
            File.state == "durable",
        )
    )
    if file is None:
        raise HTTPException(404)
    start, end, status = parse_range(range_header, file.actual_bytes)
    store = LocalStore(request.app.state.settings.storage_root)
    try:
        source = store.read(file.internal_path)
    except OSError:
        raise HTTPException(404) from None
    # Verify on the same opened handle that is served (including partial reads).
    digest = hashlib.sha256()
    size = 0
    try:
        while chunk := source.read(65536):
            digest.update(chunk)
            size += len(chunk)
        if size != file.actual_bytes or digest.hexdigest() != file.sha256:
            raise HTTPException(404)
        source.seek(start)
    except BaseException:
        source.close()
        raise
    headers = {
        "Content-Length": str(end - start + 1),
        "Accept-Ranges": "bytes",
        "ETag": '"' + file.sha256 + '"',
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": "inline; filename*=UTF-8''" + quote(file.display_name, safe=""),
    }
    if status == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{file.actual_bytes}"

    # Capture immutable values before rolling back the request Session. Never
    # reuse its ORM identities or transaction while iterating the response.
    identity, version = file.id, file.version
    engine, cookie = request.app.state.engine, request.cookies.get("session")

    def body():
        try:
            remaining = end - start + 1
            while remaining:
                chunk = source.read(min(65536, remaining))
                if not chunk:
                    return
                try:
                    authorize_download_chunk(engine, cookie, principal, identity, version)
                except (HTTPException, SQLAlchemyError):
                    return  # Headers may already be sent; fail closed and close the source.
                remaining -= len(chunk)
                yield chunk
        finally:
            source.close()

    # Release initial locks. Each chunk reauthorizes in a separate short Session;
    # neither that Session nor its locks cross a slow client's send boundary.
    media_type = file.actual_mime
    session.rollback()
    return StreamingResponse(
        body(),
        status_code=status,
        media_type=media_type,
        headers=headers,
        background=BackgroundTask(source.close),
    )
