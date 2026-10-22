"""Redis-independent recovery of the same persisted task and generation intent."""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import and_, case, or_, select, text

from app.dispatch.models import OutboxEvent
from app.dispatch.outbox import rearm_outbox
from app.tasks.models import GenerationTask

TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED", "MANUALLY_CLOSED"})
AUTOMATIC_RECOVERY_BLOCKERS = frozenset({"UPSTREAM_NEEDS_INPUT", "CALLBACK_EVENT_CONFLICT"})


def automatic_recovery_blocked(task):
    return getattr(task, "investigation_reason", None) in AUTOMATIC_RECOVERY_BLOCKERS


def database_now(session):
    return session.scalar(text("SELECT UTC_TIMESTAMP(6)"))


def recovery_action(task):
    if task.state in TERMINAL_STATES:
        return None
    if task.state in {"SAVING", "SAVE_RECOVERY"}:
        return "save_original"
    if task.upstream_id:
        return "query_original"
    return {
        "SUBMITTED": "prepare_submission",
        "QUEUED": "prepare_submission",
        "SUBMITTING": "reconcile_submission",
        "RUNNING": "reconcile_submission",
        "INVESTIGATING": "investigate",
    }.get(task.state)


@dataclass(frozen=True)
class RecoveryReport:
    scheduled: tuple[str, ...]


class RecoveryScheduler:
    def __init__(self, session_factory, *, retry_seconds=30, task_ids=None):
        if retry_seconds <= 0:
            raise ValueError("retry_seconds must be positive")
        self.session_factory = session_factory
        self.retry_seconds, self.task_ids = retry_seconds, task_ids

    def recover_due_tasks(self, now=None, batch_size=100):
        """`now` is a compatibility hint only; DB time controls all eligibility."""
        if not 1 <= batch_size <= 1000:
            raise ValueError("batch_size must be between 1 and 1000")
        with self.session_factory() as session, session.begin():
            current = database_now(session)
            query = select(GenerationTask).where(
                GenerationTask.state.not_in(TERMINAL_STATES),
                GenerationTask.recovery_due_at <= current,
                ~select(OutboxEvent.event_id).where(
                    OutboxEvent.task_id == GenerationTask.id,
                    OutboxEvent.state_version == GenerationTask.state_version,
                    OutboxEvent.claimed_generation < OutboxEvent.dispatch_generation,
                    OutboxEvent.ready_at > current,
                    or_(
                        OutboxEvent.operation == case(
                            (GenerationTask.state.in_({"SAVING", "SAVE_RECOVERY"}), "save"),
                            else_="recover",
                        ),
                        and_(OutboxEvent.operation == "submit",
                             GenerationTask.state.in_({"SUBMITTED", "QUEUED"}),
                             GenerationTask.upstream_id.is_(None)),
                    ),
                ).exists(),
                or_(GenerationTask.investigation_reason.is_(None),
                    GenerationTask.investigation_reason.not_in(AUTOMATIC_RECOVERY_BLOCKERS)),
                or_(
                    GenerationTask.lease_expires_at.is_(None),
                    GenerationTask.lease_expires_at <= current,
                ),
            )
            if self.task_ids is not None:
                query = query.where(GenerationTask.id.in_(self.task_ids))
            tasks = session.scalars(
                query.order_by(GenerationTask.recovery_due_at, GenerationTask.id)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            ).all()
            scheduled = []
            for task in tasks:
                action = recovery_action(task)
                if action is None:
                    continue
                rearm_outbox(
                    session, task.id, "save" if action == "save_original" else "recover",
                    ready_at=current,
                )
                # This is a watchdog deadline, not the generation's execution not-before.
                task.recovery_due_at = current + timedelta(seconds=self.retry_seconds)
                scheduled.append(task.id)
            return RecoveryReport(tuple(scheduled))
