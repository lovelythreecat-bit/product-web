"""Database leases authorize work; Redis messages are replaceable wake-up hints."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from redis.exceptions import RedisError, ResponseError
from sqlalchemy import select, text, update

from app.dispatch.models import OutboxEvent
from app.dispatch.recovery import TERMINAL_STATES, database_now, recovery_action
from app.tasks.models import GenerationTask


@dataclass(frozen=True)
class Lease:
    task_id: str
    worker_id: str
    fencing_token: int
    expires_at: datetime


class LeaseManager:
    def __init__(self, session_factory, *, lease_seconds=60):
        if not 1 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 1 and 3600")
        self.session_factory, self.lease_seconds = session_factory, lease_seconds

    def claim_task(self, task_id, worker_id):
        if not worker_id or len(worker_id) > 128:
            raise ValueError("Invalid worker identity")
        with self.session_factory() as session, session.begin():
            task = session.scalar(
                select(GenerationTask).where(GenerationTask.id == str(task_id)).with_for_update()
            )
            current = database_now(session)
            if (
                task is None
                or task.state in TERMINAL_STATES
                or (task.lease_expires_at is not None and task.lease_expires_at > current)
            ):
                return None
            task.fencing_token += 1
            task.lease_owner = worker_id
            task.lease_expires_at = current + timedelta(seconds=self.lease_seconds)
            return Lease(task.id, worker_id, task.fencing_token, task.lease_expires_at)

    def renew(self, lease):
        with self.session_factory() as session, session.begin():
            task = session.scalar(
                select(GenerationTask).where(GenerationTask.id == lease.task_id).with_for_update()
            )
            current = database_now(session)
            if not lease_matches(task, lease, current) or task.state in TERMINAL_STATES:
                return None
            task.lease_expires_at = current + timedelta(seconds=self.lease_seconds)
            return Lease(task.id, lease.worker_id, lease.fencing_token, task.lease_expires_at)

    def release(self, lease, *, retry_seconds=30):
        if retry_seconds <= 0:
            raise ValueError("retry_seconds must be positive")
        with self.session_factory() as session, session.begin():
            result = session.execute(
                update(GenerationTask)
                .where(
                    GenerationTask.id == lease.task_id,
                    GenerationTask.lease_owner == lease.worker_id,
                    GenerationTask.fencing_token == lease.fencing_token,
                    GenerationTask.lease_expires_at > text("UTC_TIMESTAMP(6)"),
                )
                .values(
                    lease_owner=None,
                    lease_expires_at=None,
                    recovery_due_at=database_now(session) + timedelta(seconds=retry_seconds),
                )
            )
            return result.rowcount == 1


def lease_matches(task, lease, current):
    return (
        task is not None
        and isinstance(lease, Lease)
        and task.id == lease.task_id
        and task.lease_owner == lease.worker_id
        and task.fencing_token == lease.fencing_token
        and task.lease_expires_at is not None
        and task.lease_expires_at > current
    )


@dataclass(frozen=True)
class HandlerContext:
    """Immutable routing facts, not an authorization to perform an upstream submit.

    T09 persists its attempt and SUBMITTING before I/O, then rechecks the lease on
    writeback. T10/T11/T13 query/save/investigate the original identity. Handlers
    open their own short transactions, renew leases as needed and use transition_task.
    Never hold a DB transaction while invoking an adapter or downloading files.
    """

    task_id: str
    state: str
    state_version: int
    agent_id: str
    agent_version: str
    external_submission_id: str
    upstream_id: str | None
    action: str
    lease: Lease


StageHandler = Callable[[HandlerContext], None]


@dataclass
class ConsumeReport:
    handled: int = 0
    unhandled: int = 0
    busy: int = 0
    rejected: int = 0
    failed: int = 0


class TaskConsumer:
    def __init__(
        self,
        session_factory,
        redis,
        stream,
        group,
        worker_id,
        *,
        handlers: Mapping[str, StageHandler] | None = None,
        lease_seconds=60,
    ):
        self.session_factory = session_factory
        self.redis, self.stream, self.group, self.worker_id = redis, stream, group, worker_id
        self.handlers = dict(handlers or {})
        self.leases = LeaseManager(session_factory, lease_seconds=lease_seconds)

    def ensure_group(self):
        try:
            self.redis.xgroup_create(self.stream, self.group, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def consume_once(self, batch_size=100):
        if not 1 <= batch_size <= 1000:
            raise ValueError("batch_size must be between 1 and 1000")
        report = ConsumeReport()
        try:
            self.ensure_group()
            messages = self.redis.xreadgroup(
                self.group, self.worker_id, {self.stream: ">"}, count=batch_size
            )
        except RedisError:
            report.failed += 1
            return report
        for _, entries in messages:
            for message_id, fields in entries:
                outcome = self.process_message(fields)
                setattr(report, outcome, getattr(report, outcome) + 1)
                try:
                    self.redis.xack(self.stream, self.group, message_id)
                except RedisError:
                    report.failed += 1
        return report

    def process_message(self, fields):
        try:
            fields = {
                (k.decode() if isinstance(k, bytes) else k): (
                    v.decode() if isinstance(v, bytes) else v
                )
                for k, v in fields.items()
            }
            event_id, task_id = fields["event_id"], fields["task_id"]
            version = int(fields["state_version"])
        except (KeyError, ValueError, UnicodeError, AttributeError):
            return "rejected"
        with self.session_factory() as session:
            event = session.get(OutboxEvent, event_id)
            if event is None or (event.task_id, event.state_version) != (task_id, version):
                return "rejected"
        lease = self.leases.claim_task(task_id, self.worker_id)
        if lease is None:
            return "busy"
        try:
            with self.session_factory() as session:
                task = session.get(GenerationTask, task_id)
                action = recovery_action(task)
                context = HandlerContext(
                    task.id,
                    task.state,
                    task.state_version,
                    task.agent_id,
                    task.agent_version,
                    task.external_submission_id,
                    task.upstream_id,
                    action,
                    lease,
                )
            handler = self.handlers.get(action)
            if handler is None:
                return "unhandled"
            handler(context)
            return "handled"
        except Exception:
            # Never disclose adapter errors/input/credentials or infer generation failure.
            return "failed"
        finally:
            self.leases.release(lease)
