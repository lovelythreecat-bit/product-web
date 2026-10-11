"""Transactional enqueue and at-least-once Redis delivery outside DB transactions."""

from dataclasses import dataclass
from uuid import uuid4

from fastapi import HTTPException
from redis.exceptions import RedisError
from sqlalchemy import select, text, update

from app.dispatch.models import OutboxEvent
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
            ready_at=text("UTC_TIMESTAMP(6)"),
            attempts=0,
        )
        session.add(row)
        session.flush()
    return row


@dataclass(frozen=True)
class DispatchReport:
    dispatched: int = 0
    failed: int = 0


class OutboxDispatcher:
    def __init__(self, session_factory, redis, stream, *, task_ids=None):
        self.session_factory, self.redis, self.stream = session_factory, redis, stream
        self.task_ids = task_ids

    def dispatch_pending(self, batch_size=100):
        if not 1 <= batch_size <= 1000:
            raise ValueError("batch_size must be between 1 and 1000")
        with self.session_factory() as session, session.begin():
            query = select(OutboxEvent).where(
                OutboxEvent.dispatched_at.is_(None),
                OutboxEvent.ready_at <= text("UTC_TIMESTAMP(6)"),
            )
            if self.task_ids is not None:
                query = query.where(OutboxEvent.task_id.in_(self.task_ids))
            rows = session.scalars(
                query.order_by(OutboxEvent.ready_at, OutboxEvent.event_id)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            ).all()
            messages = []
            for row in rows:
                row.attempts += 1
                messages.append((row.event_id, row.task_id, row.state_version, row.ready_at))
        dispatched = failed = 0
        for event_id, task_id, version, ready_at in messages:
            try:
                # No DB lock or transaction spans Redis/network I/O. Duplicates are intentional.
                self.redis.xadd(
                    self.stream,
                    {"event_id": event_id, "task_id": task_id, "state_version": str(version)},
                )
            except RedisError:
                failed += 1
                continue
            with self.session_factory() as session, session.begin():
                session.execute(
                    update(OutboxEvent)
                    .where(
                        OutboxEvent.event_id == event_id,
                        OutboxEvent.ready_at == ready_at,
                        OutboxEvent.dispatched_at.is_(None),
                    )
                    .values(dispatched_at=text("UTC_TIMESTAMP(6)"))
                )
            dispatched += 1
        return DispatchReport(dispatched, failed)
