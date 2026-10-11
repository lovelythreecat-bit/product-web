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
