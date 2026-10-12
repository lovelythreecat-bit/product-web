"""Exact-resource access with independent approval and transaction-bound auditing."""

from datetime import UTC
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.admin.models import ContentAccessGrant
from app.admin.permissions import authorize_admin
from app.admin.schemas import AuditedContent
from app.audit.service import audit_admin
from app.auth.models import User
from app.conversations.models import Conversation, Message, ProductVersion
from app.dispatch.recovery import database_now
from app.storage.models import File
from app.tasks.models import GenerationTask, TaskSnapshot
from app.works.models import Work, WorkItem

MODELS = {
    "message": Message,
    "work": Work,
    "file": File,
    "material": File,
    "conversation": Conversation,
    "task": GenerationTask,
    "product_version": ProductVersion,
}


def approval_allowed(settings, actor_id):
    return (
        settings.mode == "mock"
        and settings.test_only
        and str(actor_id) in {str(value) for value in settings.test_only_content_approver_ids}
    )


def resource(session, kind, identity):
    model = MODELS.get(kind)
    if model is None:
        raise HTTPException(404)
    key = model.version if model is ProductVersion else model.id
    predicates = [key == str(identity)]
    if model in (File, Work):
        predicates.append(model.deleted_at.is_(None))
    if model is File:
        predicates.append(File.state == "durable")
    row = session.scalar(
        select(model)
        .where(*predicates)
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise HTTPException(404)
    return row


def grant_content_access(session, settings, approver, dto):
    authorize_admin(session, approver, user_ids=[dto.actor_id, dto.scope.user_id])
    if not approval_allowed(settings, approver.user_id) or dto.actor_id == approver.user_id:
        raise HTTPException(403)
    recipient = session.get(User, str(dto.actor_id))
    if recipient is None or recipient.status != "active" or recipient.role != "admin":
        raise HTTPException(403)
    row = resource(session, dto.scope.resource_type, dto.scope.resource_id)
    if row.user_id != str(dto.scope.user_id):
        raise HTTPException(404)
    current = database_now(session)
    expiry = dto.expires_at.astimezone(UTC).replace(tzinfo=None)
    if expiry <= current:
        raise HTTPException(422)
    grant = ContentAccessGrant(
        id=str(uuid4()),
        actor_id=str(dto.actor_id),
        approver_id=str(approver.user_id),
        user_id=row.user_id,
        resource_type=dto.scope.resource_type,
        resource_id=str(dto.scope.resource_id),
        reason=dto.reason,
        expires_at=expiry,
        created_at=current,
        mode=settings.mode,
        test_only=settings.test_only,
        authority_source="TEST_ONLY:configured_content_approvers",
    )
    session.add(grant)
    audit_admin(
        session,
        approver.user_id,
        "content_access_grant",
        grant.id,
        dto.reason,
        {
            "actor_id": grant.actor_id,
            "user_id": grant.user_id,
            "resource_type": grant.resource_type,
            "resource_id": grant.resource_id,
            "expires_at": expiry.replace(tzinfo=UTC).isoformat(),
            "authority_source": grant.authority_source,
        },
    )
    session.flush()
    return grant


def revoke_content_access(session, settings, actor, grant_id, reason):
    authorize_admin(session, actor)
    grant = session.scalar(
        select(ContentAccessGrant)
        .where(ContentAccessGrant.id == str(grant_id))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if grant is None:
        raise HTTPException(404)
    if grant.approver_id != str(actor.user_id) and not approval_allowed(settings, actor.user_id):
        raise HTTPException(403)
    if grant.mode != settings.mode or grant.test_only != settings.test_only:
        raise HTTPException(403)
    if grant.revoked_at is None:
        grant.revoked_at = database_now(session)
        grant.revoked_by = str(actor.user_id)
        grant.revoke_reason = reason
        audit_admin(
            session,
            actor.user_id,
            "content_access_revoke",
            grant.id,
            reason,
            {"resource_type": grant.resource_type, "resource_id": grant.resource_id},
        )
        session.flush()
    return grant


def authorize_content(session, settings, actor, kind, identity):
    authorize_admin(session, actor)
    # Locks serialize a read with revocation. Every request/chunk uses fresh authority.
    grant = session.scalar(
        select(ContentAccessGrant)
        .where(
            ContentAccessGrant.actor_id == str(actor.user_id),
            ContentAccessGrant.resource_type == kind,
            ContentAccessGrant.resource_id == str(identity),
            ContentAccessGrant.mode == settings.mode,
            ContentAccessGrant.test_only == settings.test_only,
            ContentAccessGrant.revoked_at.is_(None),
            ContentAccessGrant.expires_at > database_now(session),
        )
        .order_by(ContentAccessGrant.expires_at.desc(), ContentAccessGrant.id)
        .limit(1)
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    )
    if grant is None or not approval_allowed(settings, grant.approver_id):
        raise HTTPException(403)
    row = resource(session, kind, identity)
    if row.user_id != grant.user_id:
        raise HTTPException(403)
    return grant, row


def audit_content_read(session, actor, grant, reason):
    if not reason.strip() or len(reason) > 500:
        raise HTTPException(422)
    return audit_admin(
        session,
        actor.user_id,
        "content_access_read",
        grant.resource_id,
        reason,
        {"grant_id": grant.id, "resource_type": grant.resource_type, "user_id": grant.user_id},
    )


def read_user_content(session, settings, actor, kind, identity, reason):
    grant, row = authorize_content(session, settings, actor, kind, identity)
    if kind == "message":
        data = {"role": row.role, "content": row.content}
    elif kind == "conversation":
        messages = session.scalars(
            select(Message)
            .where(Message.conversation_id == row.id, Message.user_id == row.user_id)
            .order_by(Message.created_at, Message.id)
        ).all()
        data = {
            "title": row.title,
            "messages": [
                {"id": message.id, "role": message.role, "content": message.content}
                for message in messages
            ],
        }
    elif kind == "product_version":
        data = {"product": row.product, "version": row.version}
    elif kind == "task":
        snapshot = session.get(TaskSnapshot, row.id)
        if snapshot is None:
            raise HTTPException(404)
        # The input contains user-authored fields; agent/credential snapshots never leave.
        data = {
            "input": {
                key: snapshot.input_snapshot.get(key)
                for key in (
                    "product_version",
                    "product",
                    "instruction",
                    "material_versions",
                    "parameters",
                )
            }
        }
    elif kind == "work":
        message = session.scalar(
            select(Message).where(Message.id == row.message_id, Message.user_id == row.user_id)
        )
        items = session.scalars(
            select(WorkItem)
            .where(WorkItem.work_id == row.id, WorkItem.user_id == row.user_id)
            .order_by(WorkItem.item_key)
        ).all()
        data = {
            "message": message.content if message else None,
            "files": [{"file_id": item.file_id, "version": item.file_version} for item in items],
        }
    else:
        data = {
            "file_id": row.id,
            "version": row.version,
            "display_name": row.display_name,
            "media_type": row.actual_mime,
            "bytes": row.actual_bytes,
        }
    audit = audit_content_read(session, actor, grant, reason)
    session.flush()
    return AuditedContent(
        resource_type=kind,
        resource_id=identity,
        user_id=row.user_id,
        grant_id=grant.id,
        audit_id=audit.id,
        content=data,
    )
