"""User-serialized durable event writer; no commit and no streaming transport.

Internal callers must acquire user before credit/capacity/task locks. Re-locking
that already-held user here is safe. T14 supplies authenticated delivery/replay.
"""

from datetime import timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import delete, func, select

from app.auth.models import User
from app.common.types import DTO, PositiveInt, TaskState
from app.events.models import DurableEvent, EventHead, EventReceipt
from app.ledger.service import LedgerError, now
from app.tasks.models import GenerationTask


class TaskEventPayload(DTO):
    task_id: UUID
    state: TaskState
    state_version: PositiveInt
    media_revision: PositiveInt | None = None
    conversation_id: UUID | None = None


def payload_digest(event_type, payload):
    value = f"{event_type}|{payload['task_id']}|{payload['state']}|{payload['state_version']}"
    # Permanent receipts predate media notifications: preserve their original digest.
    if payload.get("media_revision") is not None:
        value += f"|media:{payload['media_revision']}"
    return sha256(value.encode()).hexdigest()


def event_head(session, user_id):
    # Caller holds the user lock, including for first use; there is only one sequence writer.
    head = session.scalar(
        select(EventHead)
        .where(EventHead.user_id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if head is None:
        head = EventHead(user_id=user_id, last_seq=0, pruned_through=0)
        session.add(head)
        session.flush()
    return head


def prune_events(session, user_id, retention_seconds):
    """Caller owns transaction; preserve receipts, tasks, audits and all credit records."""
    session.scalar(select(User).where(User.id == user_id).with_for_update())
    head = event_head(session, user_id)
    cutoff = now() - timedelta(seconds=retention_seconds)
    expired = session.scalar(
        select(func.max(DurableEvent.event_seq)).where(
            DurableEvent.user_id == user_id,
            DurableEvent.created_at < cutoff,
        )
    )
    if expired is not None:
        head.pruned_through = max(head.pruned_through, expired)
        session.flush()
        session.execute(
            delete(DurableEvent).where(
                DurableEvent.user_id == user_id,
                DurableEvent.event_seq <= expired,
            )
        )
    return head


def append_durable_event(session, user_id, event_type, payload, *, event_key):
    payload = TaskEventPayload.model_validate(payload).model_dump(mode="json", exclude_none=True)
    if not event_key or len(event_key) > 160 or event_type != "task.updated":
        raise HTTPException(422)
    user_id = str(user_id)
    user = session.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(404)
    task = session.scalar(
        select(GenerationTask)
        .where(GenerationTask.id == payload["task_id"], GenerationTask.user_id == user_id)
        .with_for_update()
    )
    if task is None:
        raise HTTPException(404)
    # Scope notifications without exposing input or forcing unrelated detail requests.
    payload["conversation_id"] = task.conversation_id
    previous = session.scalar(
        select(EventReceipt)
        .where(EventReceipt.user_id == user_id, EventReceipt.event_key == event_key)
        .with_for_update()
    )
    if previous:
        if previous.payload_digest != payload_digest(event_type, payload):
            raise LedgerError()
        existing = session.get(DurableEvent, previous.id)
        return (
            existing
            if existing is not None
            else DurableEvent(
                id=previous.id,
                user_id=user_id,
                task_id=previous.task_id,
                event_seq=previous.event_seq,
                event_key=event_key,
                event_type=event_type,
                payload=payload,
                created_at=previous.created_at,
            )
        )
    if (payload["state"], payload["state_version"]) != (task.state, task.state_version):
        raise LedgerError()
    head = event_head(session, user_id)
    head.last_seq += 1
    row = DurableEvent(
        id=str(uuid4()),
        user_id=user_id,
        task_id=task.id,
        event_seq=head.last_seq,
        event_key=event_key,
        event_type=event_type,
        payload=payload,
        created_at=now(),
    )
    session.add(row)
    session.add(
        EventReceipt(
            id=row.id,
            user_id=user_id,
            task_id=row.task_id,
            event_seq=row.event_seq,
            event_key=event_key,
            event_type=event_type,
            payload_digest=payload_digest(event_type, payload),
            created_at=row.created_at,
        )
    )
    session.flush()
    return row
