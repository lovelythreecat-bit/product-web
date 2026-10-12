"""Administrative financial and diagnostic reads with bounded safe projections."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, or_, select

from app.admin.permissions import authorize_admin
from app.admin.schemas import AdminUserView, TaskDiagnosticView
from app.audit.models import AuditEvent
from app.audit.service import audit_admin
from app.auth.models import User
from app.common.types import CursorPage
from app.investigations.models import Investigation
from app.ledger.reads import AccountReads
from app.ledger.service import grant_credits
from app.tasks.models import GenerationTask, TaskStateEvent


def _admin_page_rows(session, model, scope, filters, cursor, limit):
    """Caller requires live admin access; anchors retain immutable target scope.

    State/status may change between requests, so they only filter the result set.
    This helper is local to these administrative lists; owner-scoped pagination
    elsewhere keeps its existing authorization and cursor rules.
    """
    if type(limit) is not int or not 1 <= limit <= 100:
        raise HTTPException(422)
    query = select(model).where(*scope, *filters)
    if cursor:
        try:
            identity = str(UUID(str(cursor)))
        except ValueError:
            raise HTTPException(422) from None
        anchor = session.execute(
            select(model.id, model.created_at).where(*scope, model.id == identity)
        ).one_or_none()
        if anchor is None:
            raise HTTPException(422)
        query = query.where(
            or_(
                model.created_at < anchor.created_at,
                and_(model.created_at == anchor.created_at, model.id < anchor.id),
            )
        )
    rows = session.scalars(
        query.order_by(model.created_at.desc(), model.id.desc()).limit(limit + 1)
    ).all()
    return rows[:limit], rows[limit - 1].id if len(rows) > limit else None


def list_users(session, actor, cursor, limit, status=None):
    authorize_admin(session, actor)
    predicates = [User.status == status] if status else []
    rows, next_cursor = _admin_page_rows(session, User, [], predicates, cursor, limit)
    return CursorPage[AdminUserView](items=rows, next_cursor=next_cursor)


def user_account(session, actor, user_id, *, ledger=False, cursor=None, limit=20):
    authorize_admin(session, actor)
    if session.get(User, str(user_id)) is None:
        raise HTTPException(404)
    reads = AccountReads(session)
    if ledger:
        return reads._ledger_for_user(user_id, cursor, limit)
    return reads._account_for_user(user_id)


def admin_credit_grant(session, actor, dto):
    authorize_admin(session, actor, user_ids=[dto.user_id])
    grant = grant_credits(
        session, dto.user_id, "admin", dto.business_key, dto.amount, dto.reason, actor
    )
    # Account locks serialize replay with the first transaction, including its audit.
    if (
        session.scalar(
            select(AuditEvent.id).where(
                AuditEvent.action == "admin_credit_grant", AuditEvent.object_id == grant.id
            )
        )
        is None
    ):
        audit_admin(
            session,
            actor.user_id,
            "admin_credit_grant",
            grant.id,
            dto.reason,
            {"user_id": str(dto.user_id), "amount": dto.amount},
        )
    return grant


def diagnostic(session, task):
    case = session.get(Investigation, task.id)
    terminal = task.state in {"SUCCEEDED", "FAILED", "MANUALLY_CLOSED"}
    finished = (
        session.scalar(
            select(TaskStateEvent.created_at)
            .where(TaskStateEvent.task_id == task.id, TaskStateEvent.to_state == task.state)
            .order_by(TaskStateEvent.state_version.desc())
            .limit(1)
        )
        if terminal
        else None
    )
    end = finished or datetime.now(UTC).replace(tzinfo=None)
    # Raw provider errors, evidence and task snapshots are deliberately absent.
    code = {
        "INVESTIGATING": "UPSTREAM_REVIEW_REQUIRED",
        "SAVE_RECOVERY": "SAVE_RETRY_REQUIRED",
        "FAILED": "VERIFIED_FAILURE",
        "MANUALLY_CLOSED": "MANUAL_CLOSE",
    }.get(task.state)
    return TaskDiagnosticView(
        id=task.id,
        user_id=task.user_id,
        agent_id=task.agent_id,
        agent_version=task.agent_version,
        state=task.state,
        state_version=task.state_version,
        settlement_state=task.settlement_state,
        created_at=task.created_at,
        elapsed_seconds=max(0, (end - task.created_at).total_seconds()),
        diagnostic_code=code,
        investigation_status=case.status if case else None,
        investigation_owner=case.owner if case else None,
        investigation_deadline=case.deadline_at if case else None,
    )


def list_tasks(session, actor, cursor, limit, state=None, user_id=None):
    authorize_admin(session, actor)
    scope = [GenerationTask.user_id == str(user_id)] if user_id else []
    filters = [GenerationTask.state == state] if state else []
    rows, next_cursor = _admin_page_rows(session, GenerationTask, scope, filters, cursor, limit)
    return CursorPage[TaskDiagnosticView](
        items=[diagnostic(session, row) for row in rows], next_cursor=next_cursor
    )
