from datetime import UTC

from fastapi import HTTPException
from sqlalchemy import func, select

from app.common.pagination import page_rows
from app.common.types import CursorPage, TaskView
from app.conversations.service import authenticate, owned_conversation
from app.ledger.service import now
from app.quick_generation.models import QuickGenerationRun
from app.tasks.models import GenerationTask, TaskSnapshot, TaskStateEvent
from app.tasks.schemas import TaskDetail
from app.works.models import Work


def task_view(session, row):
    snapshot = session.scalar(
        select(TaskSnapshot).where(TaskSnapshot.task_id == row.id).with_for_update(read=True)
    )
    updated_at = session.scalar(
        select(func.max(TaskStateEvent.created_at)).where(TaskStateEvent.task_id == row.id)
    ) or row.created_at
    return TaskView(
        task_id=row.id,
        display_number=row.display_number,
        state=row.state,
        state_version=row.state_version,
        settlement_state=row.settlement_state,
        quote=snapshot.quote,
        work_ids=list(
            session.scalars(
                select(Work.id)
                .where(Work.task_id == row.id)
                .order_by(Work.id)
                .with_for_update(read=True)
            )
        ),
        investigation_reason=row.investigation_reason,
        created_at=row.created_at.replace(tzinfo=UTC),
        updated_at=updated_at.replace(tzinfo=UTC),
    )


class TaskRepository:
    def __init__(self, session):
        self.session = session

    def delete_history(self, principal, id):
        authenticate(self.session, principal)
        row = self.session.scalar(
            select(GenerationTask).where(
                GenerationTask.id == str(id), GenerationTask.user_id == str(principal.user_id)
            ).with_for_update()
        )
        if row is None:
            raise HTTPException(404)
        if row.history_deleted_at is None:
            row.history_deleted_at = now()

    def read_task(self, principal, id, *, include_regeneration=True):
        from app.tasks.regeneration import RegenerationService

        authenticate(self.session, principal)
        row = self.session.scalar(
            select(GenerationTask).where(
                GenerationTask.id == str(id), GenerationTask.user_id == str(principal.user_id)
            )
        )
        if row is None:
            raise HTTPException(404)
        conversation = owned_conversation(self.session, principal.user_id, row.conversation_id)
        snapshot = self.session.get(TaskSnapshot, row.id)
        media = None
        if (snapshot.routing_snapshot or {}).get("protocol_version") in {
            "image-agent-v1", "video-agent-v1"
        }:
            from app.agents.media_execution import MediaExecution, public_media_state

            execution = self.session.get(MediaExecution, row.id)
            if execution is not None:
                media = public_media_state(execution.kind, execution.state,
                                           revision=execution.revision)
        return TaskDetail(
            task=task_view(self.session, row),
            conversation_id=row.conversation_id,
            conversation_display_number=conversation.display_number,
            agent_id=row.agent_id,
            input=snapshot.input_snapshot,
            policy_versions=snapshot.policy_versions,
            media=media,
            regeneration=RegenerationService(self.session).state(row, snapshot)
            if include_regeneration else None,
        )

    def list_tasks(self, principal, conversation_id=None, cursor=None, limit=20, *, task_type=None):
        authenticate(self.session, principal)
        scope = [GenerationTask.user_id == str(principal.user_id)]
        if conversation_id:
            owned_conversation(self.session, principal.user_id, conversation_id)
            scope.append(GenerationTask.conversation_id == str(conversation_id))
        if task_type == "ordinary":
            scope.append(~select(QuickGenerationRun.id).where(
                QuickGenerationRun.conversation_id == GenerationTask.conversation_id,
                QuickGenerationRun.user_id == GenerationTask.user_id,
            ).exists())
        rows, next_cursor = page_rows(
            self.session, GenerationTask, [*scope, GenerationTask.history_deleted_at.is_(None)],
            cursor, limit, cursor_predicates=scope,
        )
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
    result = {
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
    if snapshot.routing_snapshot is not None:
        result["routing_snapshot"] = snapshot.routing_snapshot
    return result
