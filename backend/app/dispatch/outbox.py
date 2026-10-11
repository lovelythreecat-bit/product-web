"""Transactional writer only; caller holds canonical user/credit/capacity/task locks.

T08 owns dispatch, leases and recovery. This module never contacts Redis or agents.
"""

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.dispatch.models import OutboxEvent
from app.ledger.service import now
from app.tasks.models import GenerationTask


def enqueue_outbox(session, task_id, operation):
    if operation not in ("submit", "recover", "save"):
        raise HTTPException(422)
    task = session.scalar(
        select(GenerationTask).where(GenerationTask.id == str(task_id)).with_for_update()
    )
    if task is None:
        raise HTTPException(404)
    row = session.scalar(
        select(OutboxEvent)
        .where(
            OutboxEvent.task_id == task.id,
            OutboxEvent.state_version == task.state_version,
            OutboxEvent.operation == operation,
        )
        .with_for_update()
    )
    if row is None:
        row = OutboxEvent(
            event_id=str(uuid4()),
            task_id=task.id,
            user_id=task.user_id,
            state_version=task.state_version,
            operation=operation,
            ready_at=now(),
            attempts=0,
        )
        session.add(row)
        session.flush()
    return row
