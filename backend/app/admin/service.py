"""Administrative financial and diagnostic reads with bounded safe projections."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, case, exists, func, or_, select, tuple_

from app.admin.permissions import authorize_admin
from app.admin.queries import balance_totals, safe_identity, search_terms
from app.admin.schemas import (
    AdminAuditSummary,
    AdminLedgerEntryView,
    AdminLedgerSummary,
    AdminTasksSummary,
    AdminUsersSummary,
    AdminUserView,
    TaskDiagnosticView,
    TaskTimelineEvent,
)
from app.audit.models import AuditEvent
from app.audit.service import audit_admin
from app.auth.models import User
from app.common.pagination import numbered_page_rows
from app.common.types import CursorPage, NumberedPage
from app.investigations.models import Investigation
from app.ledger.models import CreditAccount, CreditGrant, CreditLedger, CreditReservation
from app.ledger.reads import AccountReads, _task_name
from app.ledger.service import grant_credits
from app.tasks.models import GenerationTask, TaskSnapshot, TaskStateEvent
from app.works.models import Work


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


def list_users(session, actor, cursor, limit, status=None, q=None):
    authorize_admin(session, actor)
    predicates = [User.status == status] if status else []
    predicates += search_terms(q, [User.account_normalized, User.nickname, User.id])
    deleted = exists(
        select(AuditEvent.id).where(
            AuditEvent.action == "admin_user_delete", AuditEvent.object_id == User.id
        )
    )
    rows, next_cursor = _admin_page_rows(session, User, [~deleted], predicates, cursor, limit)
    ids = [row.id for row in rows]
    counts = (
        dict(
            session.execute(
                select(GenerationTask.user_id, func.count())
                .where(GenerationTask.user_id.in_(ids))
                .group_by(GenerationTask.user_id)
            ).all()
        )
        if ids
        else {}
    )
    accounts = (
        {
            row.user_id: row
            for row in session.scalars(
                select(CreditAccount).where(CreditAccount.user_id.in_(ids))
            ).all()
        }
        if ids
        else {}
    )
    result = []
    for row in rows:
        view = AdminUserView.model_validate(row)
        account = accounts.get(row.id)
        result.append(
            view.model_copy(
                update={
                    "task_count": int(counts.get(row.id, 0)),
                    **{
                        key: int(getattr(account, key)) if account else 0
                        for key in ("available", "frozen", "consumed")
                    },
                }
            )
        )
    return CursorPage[AdminUserView](items=result, next_cursor=next_cursor)


def users_summary(session, actor):
    authorize_admin(session, actor)
    total, active, disabled, admins = session.execute(
        select(
            func.count(User.id),
            func.coalesce(func.sum(case((User.status == "active", 1), else_=0)), 0),
            func.coalesce(func.sum(case((User.status == "disabled", 1), else_=0)), 0),
            func.coalesce(func.sum(case((User.role == "admin", 1), else_=0)), 0),
        )
    ).one()
    return AdminUsersSummary(
        total=total, active=active, disabled=disabled, admin_count=admins, **balance_totals(session)
    )


def list_ledger(session, actor, cursor, limit, q=None, *, page=None):
    authorize_admin(session, actor)
    predicates = search_terms(q, [CreditLedger.reason])
    account_search = search_terms(q, [User.account_normalized])
    if predicates:
        predicates = [
            or_(predicates[0], CreditLedger.user_id.in_(select(User.id).where(*account_search)))
        ]
    rows, next_cursor, metadata = numbered_page_rows(
        session,
        CreditLedger,
        predicates,
        cursor,
        limit,
        page=page,
        cursor_reader=lambda: _admin_page_rows(
            session, CreditLedger, [], predicates, cursor, limit
        ),
    )
    ids = {row.user_id for row in rows}
    accounts = (
        dict(
            session.execute(select(User.id, User.account_normalized).where(User.id.in_(ids))).all()
        )
        if ids
        else {}
    )
    grant_ids = {row.grant_id for row in rows if row.grant_id}
    operators = (
        dict(
            session.execute(
                select(CreditGrant.id, CreditGrant.actor_id).where(CreditGrant.id.in_(grant_ids))
            ).all()
        )
        if grant_ids
        else {}
    )
    task_owners = {(row.task_id, row.user_id) for row in rows if row.task_id}
    names = (
        {
            (snapshot.task_id, snapshot.user_id): _task_name(snapshot)
            for snapshot in session.scalars(
                select(TaskSnapshot).where(
                    tuple_(TaskSnapshot.task_id, TaskSnapshot.user_id).in_(task_owners),
                )
            ).all()
        }
        if task_owners
        else {}
    )
    return NumberedPage[AdminLedgerEntryView](
        **metadata,
        items=[
            AdminLedgerEntryView(
                ledger_id=row.id,
                grant_id=row.grant_id,
                reservation_id=row.reservation_id,
                task_id=row.task_id,
                task_name=names.get((row.task_id, row.user_id)),
                kind=row.kind,
                amount=row.amount,
                balances_before=row.balances_before,
                balances_after=row.balances_after,
                reason=row.reason,
                created_at=row.created_at.replace(tzinfo=UTC),
                user_id=row.user_id,
                account=accounts[row.user_id],
                operator=operators.get(row.grant_id),
            )
            for row in rows
        ],
        next_cursor=next_cursor,
    )


def ledger_summary(session, actor):
    authorize_admin(session, actor)
    return AdminLedgerSummary(
        **balance_totals(session), ledger_count=session.scalar(select(func.count(CreditLedger.id)))
    )


def tasks_summary(session, actor):
    authorize_admin(session, actor)
    counts = dict(
        session.execute(
            select(GenerationTask.state, func.count()).group_by(GenerationTask.state)
        ).all()
    )
    frozen = session.scalar(
        select(func.coalesce(func.sum(CreditReservation.amount), 0)).where(
            CreditReservation.state == "frozen"
        )
    )
    return AdminTasksSummary(
        total=sum(counts.values()),
        investigating=counts.get("INVESTIGATING", 0),
        save_recovery=counts.get("SAVE_RECOVERY", 0),
        frozen_credits=int(frozen),
    )


def audit_summary(session, actor):
    authorize_admin(session, actor)
    counts = dict(
        session.execute(select(AuditEvent.action, func.count()).group_by(AuditEvent.action)).all()
    )
    return AdminAuditSummary(total=sum(counts.values()), action_counts=counts)


def user_account(session, actor, user_id, *, ledger=False, cursor=None, limit=20, page=None):
    authorize_admin(session, actor)
    if session.get(User, str(user_id)) is None:
        raise HTTPException(404)
    reads = AccountReads(session)
    if ledger:
        return reads._ledger_for_user(user_id, cursor, limit, page=page)
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
    timeline = [
        TaskTimelineEvent(state_version=version, from_state=before, to_state=after, created_at=at)
        for version, before, after, at in session.execute(
            select(
                TaskStateEvent.state_version,
                TaskStateEvent.from_state,
                TaskStateEvent.to_state,
                TaskStateEvent.created_at,
            )
            .where(TaskStateEvent.task_id == task.id, TaskStateEvent.user_id == task.user_id)
            .order_by(TaskStateEvent.state_version)
        ).all()
    ]
    finished = (
        next(
            (
                event.created_at.replace(tzinfo=None)
                for event in reversed(timeline)
                if event.to_state == task.state
            ),
            None,
        )
        if terminal
        else None
    )
    end = finished or datetime.now(UTC).replace(tzinfo=None)
    quote = (
        session.scalar(
            select(TaskSnapshot.quote).where(
                TaskSnapshot.task_id == task.id,
                TaskSnapshot.user_id == task.user_id,
            )
        )
        or {}
    )
    # Only this explicit quote allowlist crosses the diagnostic response.
    credits = quote.get("credits") if isinstance(quote, dict) else None
    credits = credits if type(credits) is int and credits >= 0 else None
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
        conversation_id=task.conversation_id,
        account=session.scalar(select(User.account_normalized).where(User.id == task.user_id)),
        fixed_credits=credits,
        spec_version=safe_identity(quote.get("spec_version")) if isinstance(quote, dict) else None,
        price_version=safe_identity(quote.get("price_version"))
        if isinstance(quote, dict)
        else None,
        external_submission_id=safe_identity(task.external_submission_id),
        upstream_id=safe_identity(task.upstream_id),
        updated_at=timeline[-1].created_at if timeline else task.created_at,
        work_ids=session.scalars(
            select(Work.id).where(
                Work.task_id == task.id,
                Work.user_id == task.user_id,
            )
        ).all(),
        timeline=timeline,
    )


def list_tasks(
    session, actor, cursor, limit, state=None, user_id=None, q=None, agent_id=None, *, page=None
):
    authorize_admin(session, actor)
    scope = [GenerationTask.user_id == str(user_id)] if user_id else []
    if agent_id:
        scope.append(GenerationTask.agent_id == str(agent_id))
    filters = [GenerationTask.state == state] if state else []
    terms = search_terms(q, [GenerationTask.id, GenerationTask.user_id])
    if terms:
        filters.append(
            or_(
                terms[0],
                GenerationTask.user_id.in_(
                    select(User.id).where(*search_terms(q, [User.account_normalized]))
                ),
            )
        )
    rows, next_cursor, metadata = numbered_page_rows(
        session,
        GenerationTask,
        [*scope, *filters],
        cursor,
        limit,
        page=page,
        cursor_reader=lambda: _admin_page_rows(
            session, GenerationTask, scope, filters, cursor, limit
        ),
    )
    return NumberedPage[TaskDiagnosticView](
        **metadata, items=[diagnostic(session, row) for row in rows], next_cursor=next_cursor
    )
