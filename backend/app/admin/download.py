"""Controlled admin binary access; each chunk rechecks the exact content grant."""

import hashlib
from urllib.parse import quote

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.admin.content_access import audit_content_read, authorize_content
from app.storage.local_store import LocalStore
from app.storage.routes import parse_range


def download_content(request, session, actor, kind, identity, reason, range_header):
    settings = request.app.state.settings
    grant, file = authorize_content(session, settings, actor, kind, identity)
    start, end, status = parse_range(range_header, file.actual_bytes)
    if settings.storage_root is None or not settings.storage_persistent:
        raise HTTPException(503)
    try:
        source = LocalStore(settings.storage_root).read(file.internal_path)
    except OSError:
        raise HTTPException(404) from None
    try:
        digest, size = hashlib.sha256(), 0
        while chunk := source.read(65536):
            digest.update(chunk)
            size += len(chunk)
        if size != file.actual_bytes or digest.hexdigest() != file.sha256:
            raise HTTPException(404)
        source.seek(start)
        version = file.version
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
        media_type = file.actual_mime
        audit_content_read(session, actor, grant, reason)
        session.commit()  # No bytes are disclosed unless the access audit is durable.
    except BaseException:
        source.close()
        raise

    def body():
        try:
            remaining = end - start + 1
            while remaining:
                chunk = source.read(min(remaining, 65536))
                if not chunk:
                    return
                try:
                    with Session(request.app.state.engine) as current, current.begin():
                        _, live = authorize_content(current, settings, actor, kind, identity)
                        if live.version != version:
                            return
                except (HTTPException, SQLAlchemyError):
                    return
                remaining -= len(chunk)
                yield chunk
        finally:
            source.close()

    return StreamingResponse(
        body(),
        status_code=status,
        media_type=media_type,
        headers=headers,
        background=BackgroundTask(source.close),
    )
