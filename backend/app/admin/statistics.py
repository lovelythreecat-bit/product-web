"""Database usage totals; free credits never imply payment revenue or supplier cost."""

from sqlalchemy import func, select

from app.admin.permissions import authorize_admin
from app.admin.schemas import StatisticsView
from app.ledger.models import CreditGrant, CreditLedger
from app.tasks.models import GenerationTask


def get_statistics(session, actor):
    authorize_admin(session, actor)
    states = dict(
        session.execute(
            select(GenerationTask.state, func.count()).group_by(GenerationTask.state)
        ).all()
    )
    terminal = sum(states.get(key, 0) for key in ("SUCCEEDED", "FAILED", "MANUALLY_CLOSED"))
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
    return StatisticsView(
        generated_count=sum(states.values()),
        succeeded_count=states.get("SUCCEEDED", 0),
        terminal_count=terminal,
        success_rate=states.get("SUCCEEDED", 0) / terminal if terminal else None,
        success_rate_basis="succeeded / (succeeded + failed + manually_closed)",
        credits_consumed=int(consumed),
        signup_credits=int(grants.get("signup", 0)),
        admin_granted_credits=int(grants.get("admin", 0)),
        payment_revenue_status="not_supported",
        supplier_cost_status="unavailable",
        supplier_cost=None,
        supplier_usage_status="unavailable",
    )
