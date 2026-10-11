from fastapi import HTTPException
from sqlalchemy import select

from app.common.pagination import page_rows
from app.common.types import CursorPage, TaskView
from app.conversations.service import authenticate, owned_conversation
from app.tasks.models import GenerationTask, TaskSnapshot
from app.tasks.schemas import TaskDetail


def task_view(session, row):
    snapshot = session.scalar(
        select(TaskSnapshot).where(TaskSnapshot.task_id == row.id).with_for_update(read=True)
    )
    return TaskView(
        task_id=row.id,
        state=row.state,
        state_version=row.state_version,
        settlement_state=row.settlement_state,
        quote=snapshot.quote,
        work_ids=[],
        investigation_reason=row.investigation_reason,
    )


class TaskRepository:
    def __init__(self, session):
        self.session = session

    def read_task(self, principal, id):
        authenticate(self.session, principal)
        row = self.session.scalar(
            select(GenerationTask).where(
                GenerationTask.id == str(id), GenerationTask.user_id == str(principal.user_id)
            )
        )
        if row is None:
            raise HTTPException(404)
        snapshot = self.session.get(TaskSnapshot, row.id)
        return TaskDetail(
            task=task_view(self.session, row),
            conversation_id=row.conversation_id,
            agent_id=row.agent_id,
            input=snapshot.input_snapshot,
            policy_versions=snapshot.policy_versions,
        )

    def list_tasks(self, principal, conversation_id=None, cursor=None, limit=20):
        authenticate(self.session, principal)
        predicates = [GenerationTask.user_id == str(principal.user_id)]
        if conversation_id:
            owned_conversation(self.session, principal.user_id, conversation_id)
            predicates.append(GenerationTask.conversation_id == str(conversation_id))
        rows, next_cursor = page_rows(self.session, GenerationTask, predicates, cursor, limit)
        return CursorPage[TaskView](
            items=[task_view(self.session, r) for r in rows], next_cursor=next_cursor
        )


def locked_execution(session, task_id, lease):
    """Common T09 user→task ownership lock, with database-time fencing."""
    from app.auth.models import User
    from app.dispatch.consumer import lease_matches
    from app.dispatch.recovery import database_now
    from app.tasks.state_machine import TransitionError

    user_id = session.scalar(select(GenerationTask.user_id).where(GenerationTask.id == task_id))
    if user_id is None:
        raise TransitionError("TASK_NOT_FOUND")
    session.scalar(select(User).where(User.id == user_id).with_for_update())
    task = session.scalar(
        select(GenerationTask)
        .where(GenerationTask.id == task_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not lease_matches(task, lease, database_now(session)):
        raise TransitionError("LEASE_LOST")
    return task


def original_submission_snapshot(session, task_id):
    snapshot = session.get(TaskSnapshot, task_id)
    return {
        field: getattr(snapshot, field)
        for field in (
            "input_snapshot",
            "agent_snapshot",
            "spec_snapshot",
            "price_snapshot",
            "quote",
            "policy_versions",
            "capacity_estimate",
        )
    }
