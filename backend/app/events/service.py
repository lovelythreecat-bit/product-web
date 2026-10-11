"""User-serialized durable event writer; no commit and no streaming transport.

Internal callers must acquire user before credit/capacity/task locks. Re-locking
that already-held user here is safe. T14 supplies authenticated delivery/replay.
"""

from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.auth.models import User
from app.common.types import DTO, PositiveInt, TaskState
from app.events.models import DurableEvent
from app.ledger.service import LedgerError, now
from app.tasks.models import GenerationTask


class TaskEventPayload(DTO):
    task_id: UUID
    state: TaskState
    state_version: PositiveInt


def append_durable_event(session, user_id, event_type, payload, *, event_key):
    payload = TaskEventPayload.model_validate(payload).model_dump(mode="json")
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
    previous = session.scalar(
        select(DurableEvent)
        .where(DurableEvent.user_id == user_id, DurableEvent.event_key == event_key)
        .with_for_update()
    )
    if previous:
        if previous.payload != payload or previous.event_type != event_type:
            raise LedgerError()
        return previous
    if (payload["state"], payload["state_version"]) != (task.state, task.state_version):
        raise LedgerError()
    last = session.scalar(
        select(DurableEvent.event_seq)
        .where(DurableEvent.user_id == user_id)
        .order_by(DurableEvent.event_seq.desc())
        .limit(1)
        .with_for_update()
    )
    row = DurableEvent(
        id=str(uuid4()),
        user_id=user_id,
        task_id=task.id,
        event_seq=(last or 0) + 1,
        event_key=event_key,
        event_type=event_type,
        payload=payload,
        created_at=now(),
    )
    session.add(row)
    session.flush()
    return row
