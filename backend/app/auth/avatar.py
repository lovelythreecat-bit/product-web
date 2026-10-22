"""Private avatar identity changes in the caller's authenticated transaction.

The caller locks the owner before files, matching deletion/collector lock order.
Binding reserves no capacity, unlinks no bytes and never removes other uses.
"""

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.ledger.service import now
from app.storage.models import File, FileRef

IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}


def update_avatar(session, user, reference):
    identities = {user.avatar_file_id} if user.avatar_file_id else set()
    if reference is not None:
        identities.add(str(reference.file_id))
    files = (
        session.scalars(
            select(File)
            .where(File.user_id == user.id, File.id.in_(sorted(identities)))
            .order_by(File.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).all()
        if identities
        else []
    )
    if reference is not None:
        file = next((row for row in files if row.id == str(reference.file_id)), None)
        if file is None or file.user_id != user.id or file.version != reference.version:
            raise HTTPException(404)
        if file.state != "durable" or file.deleted_at is not None:
            raise HTTPException(409)
        if file.actual_mime not in IMAGE_TYPES:
            raise HTTPException(422)

    refs = session.scalars(
        select(FileRef)
        .where(FileRef.user_id == user.id, FileRef.ref_type == "avatar", FileRef.ref_id == user.id)
        .with_for_update()
    ).all()
    kept = False
    for ref in refs:
        if ref.ref_type != "avatar" or ref.user_id != user.id or ref.ref_id != user.id:
            continue
        if reference is not None and (
            ref.file_id == str(reference.file_id) and ref.version == reference.version
        ):
            kept = True
        else:
            session.delete(ref)
    if reference is None:
        user.avatar_file_id, user.avatar_file_version = None, None
    else:
        user.avatar_file_id, user.avatar_file_version = str(reference.file_id), reference.version
        if not kept:
            session.add(
                FileRef(
                    id=str(uuid4()), file_id=str(reference.file_id), version=reference.version,
                    user_id=user.id, ref_type="avatar", ref_id=user.id, created_at=now(),
                )
            )
