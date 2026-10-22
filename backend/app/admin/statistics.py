"""Database usage totals; free credits never imply payment revenue or supplier cost."""

from datetime import UTC, datetime, time, timedelta

from sqlalchemy import case, func, select

from app.admin.permissions import authorize_admin
from app.admin.schemas import AgentUsageView, DailyUsageView, StatisticsView
from app.auth.models import User
from app.ledger.models import CreditGrant, CreditLedger, CreditReservation
from app.tasks.models import GenerationTask

TERMINAL_STATES = ("SUCCEEDED", "FAILED", "MANUALLY_CLOSED")
TREND_DAYS = 14


def _agent_ledger_totals(session, kind):
    return dict(
        session.execute(
            select(GenerationTask.agent_id, func.sum(CreditLedger.amount))
            .join(
                CreditLedger,
                (CreditLedger.task_id == GenerationTask.id)
                & (CreditLedger.user_id == GenerationTask.user_id),
            )
            .where(CreditLedger.kind == kind)
            .group_by(GenerationTask.agent_id)
        ).all()
    )


def _daily_trend(session, today):
    # Database timestamps are stored in UTC. Use UTC boundaries explicitly,
    # rather than relying on the database server's session timezone.
    first_day = today - timedelta(days=TREND_DAYS - 1)
    start = datetime.combine(first_day, time.min)
    end = datetime.combine(today + timedelta(days=1), time.min)
    task_day = func.date(GenerationTask.created_at)
    ledger_day = func.date(CreditLedger.created_at)
    tasks = {
        str(day): count
        for day, count in session.execute(
            select(task_day, func.count())
            .where(GenerationTask.created_at >= start, GenerationTask.created_at < end)
            .group_by(task_day)
        ).all()
    }
    credits = {
        str(day): int(amount)
        for day, amount in session.execute(
            select(ledger_day, func.sum(CreditLedger.amount))
            .where(
                CreditLedger.kind == "consume",
                CreditLedger.created_at >= start,
                CreditLedger.created_at < end,
            )
            .group_by(ledger_day)
        ).all()
    }
    user_day = func.date(User.created_at)
    registrations = {
        str(day): count
        for day, count in session.execute(
            select(user_day, func.count())
            .where(User.role == "user", User.created_at >= start, User.created_at < end)
            .group_by(user_day)
        ).all()
    }
    active_users = {
        str(day): count
        for day, count in session.execute(
            select(task_day, func.count(GenerationTask.user_id.distinct()))
            .join(User, GenerationTask.user_id == User.id)
            .where(
                User.role == "user",
                GenerationTask.created_at >= start,
                GenerationTask.created_at < end,
            )
            .group_by(task_day)
        ).all()
    }
    return [
        DailyUsageView(
            date=day,
            task_count=tasks.get(day.isoformat(), 0),
            credits_consumed=credits.get(day.isoformat(), 0),
            registered_count=registrations.get(day.isoformat(), 0),
            active_user_count=active_users.get(day.isoformat(), 0),
        )
        for offset in range(TREND_DAYS)
        for day in [first_day + timedelta(days=offset)]
    ]


def _user_statistics(session, today):
    start = datetime.combine(today - timedelta(days=TREND_DAYS - 1), time.min)
    today_start = datetime.combine(today, time.min)
    end = datetime.combine(today + timedelta(days=1), time.min)
    total, registered_today, registered_in_trend = session.execute(
        select(
            func.count(User.id),
            func.count(case((
                (User.created_at >= today_start) & (User.created_at < end), User.id,
            ))),
            func.count(case((
                (User.created_at >= start) & (User.created_at < end), User.id,
            ))),
        ).where(User.role == "user")
    ).one()
    # Count unique creators over the complete period, never sum daily uniques.
    # last_login_at is overwritten at each login and cannot reconstruct DAU.
    active_today, active_in_trend = session.execute(
        select(
            func.count(case((
                GenerationTask.created_at >= today_start, GenerationTask.user_id,
            )).distinct()),
            func.count(GenerationTask.user_id.distinct()),
        )
        .join(User, GenerationTask.user_id == User.id)
        .where(
            User.role == "user",
            GenerationTask.created_at >= start,
            GenerationTask.created_at < end,
        )
    ).one()
    return {
        "total_users": total,
        "registered_today": registered_today,
        "registered_in_trend": registered_in_trend,
        "active_today": active_today,
        "active_in_trend": active_in_trend,
        "active_user_basis": "generation_task_created",
    }


def get_statistics(session, actor):
    authorize_admin(session, actor)
    today = datetime.now(UTC).date()
    states = dict(
        session.execute(
            select(GenerationTask.state, func.count()).group_by(GenerationTask.state)
        ).all()
    )
    terminal = sum(states.get(key, 0) for key in TERMINAL_STATES)
    grants = dict(
        session.execute(
            select(CreditGrant.kind, func.sum(CreditGrant.amount)).group_by(CreditGrant.kind)
        ).all()
    )
    consumed = session.scalar(
        select(func.coalesce(func.sum(CreditLedger.amount), 0)).where(
            CreditLedger.kind == "consume"
        )
    )
    agent_rows = session.execute(
        select(
            GenerationTask.agent_id,
            GenerationTask.state,
            GenerationTask.settlement_state,
            func.count(),
        ).group_by(GenerationTask.agent_id, GenerationTask.state, GenerationTask.settlement_state)
    ).all()
    agent_consumed = _agent_ledger_totals(session, "consume")
    agent_frozen = dict(
        session.execute(
            select(GenerationTask.agent_id, func.sum(CreditReservation.amount))
            .join(
                CreditReservation,
                (CreditReservation.task_id == GenerationTask.id)
                & (CreditReservation.user_id == GenerationTask.user_id),
            )
            .where(CreditReservation.state == "frozen")
            .group_by(GenerationTask.agent_id)
        ).all()
    )
    agent_released = _agent_ledger_totals(session, "release")
    agents = {}
    for identity, state, settlement, count in agent_rows:
        row = agents.setdefault(
            identity,
            dict(
                agent_id=identity,
                task_count=0,
                succeeded_count=0,
                failed_count=0,
                manually_closed_count=0,
                terminal_count=0,
                success_rate=None,
                unsettled_count=0,
                credits_consumed=int(agent_consumed.get(identity, 0)),
                credits_frozen=int(agent_frozen.get(identity, 0)),
                credits_released=int(agent_released.get(identity, 0)),
            ),
        )
        row["task_count"] += count
        row["succeeded_count"] += count if state == "SUCCEEDED" else 0
        row["failed_count"] += count if state == "FAILED" else 0
        row["manually_closed_count"] += count if state == "MANUALLY_CLOSED" else 0
        row["terminal_count"] += count if state in TERMINAL_STATES else 0
        row["unsettled_count"] += count if settlement == "FROZEN" else 0
    for row in agents.values():
        if row["terminal_count"]:
            row["success_rate"] = row["succeeded_count"] / row["terminal_count"]
    return StatisticsView(
        generated_count=sum(states.values()),
        succeeded_count=states.get("SUCCEEDED", 0),
        terminal_count=terminal,
        success_rate=states.get("SUCCEEDED", 0) / terminal if terminal else None,
        success_rate_basis="succeeded / (succeeded + failed + manually_closed)",
        credits_consumed=int(consumed),
        credits_frozen=sum(int(amount) for amount in agent_frozen.values()),
        credits_released=sum(int(amount) for amount in agent_released.values()),
        signup_credits=int(grants.get("signup", 0)),
        admin_granted_credits=int(grants.get("admin", 0)),
        payment_revenue_status="not_supported",
        supplier_cost_status="unavailable",
        supplier_cost=None,
        supplier_usage_status="unavailable",
        state_counts=states,
        by_agent=[AgentUsageView(**agents[key]) for key in sorted(agents)],
        unsettled_count=sum(row["unsettled_count"] for row in agents.values()),
        daily_trend=_daily_trend(session, today),
        trend_days=TREND_DAYS,
        trend_timezone="UTC",
        **_user_statistics(session, today),
    )
