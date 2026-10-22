"""Dashboard aggregation tests replace SQL transport without executing DDL."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects.mysql import dialect
from test_admin_safe_queries import QuerySession

from app.admin import statistics
from app.ledger.models import CreditLedger

AGENT = str(uuid4())


def dashboard_session():
    return QuerySession(rows=[
        [("SUCCEEDED", 2), ("FAILED", 1), ("MANUALLY_CLOSED", 1), ("RUNNING", 1)],
        [("signup", 200), ("admin", 50)],
        [(AGENT, "SUCCEEDED", "CONSUMED", 2), (AGENT, "FAILED", "RELEASED", 1),
         (AGENT, "MANUALLY_CLOSED", "RELEASED", 1), (AGENT, "RUNNING", "FROZEN", 1)],
        [(AGENT, 8)],
        [(AGENT, 12)],
        [(AGENT, 20)],
        [("2026-10-16", 3), ("2026-10-17", 2)],
        [("2026-10-16", 8)],
        [("2026-10-16", 3), ("2026-10-17", 1)],
        [("2026-10-16", 2), ("2026-10-17", 2)],
        [(12, 1, 4)],
        [(2, 3)],
    ])


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 17, 3, tzinfo=UTC)
    monkeypatch.setattr(statistics, "datetime", FixedDateTime)


def test_agent_success_rate_counts_manual_closure_and_finance_uses_real_balances():
    session = dashboard_session()
    result = statistics.get_statistics(session, session.actor)
    row = result.by_agent[0]
    assert result.generated_count == row.task_count == 5
    assert row.terminal_count == 4
    assert row.manually_closed_count == 1
    assert row.success_rate == result.success_rate == 0.5
    assert row.unsettled_count == result.unsettled_count == 1
    assert row.credits_consumed == result.credits_consumed == 8
    assert row.credits_frozen == result.credits_frozen == 12
    assert row.credits_released == result.credits_released == 20
    assert result.supplier_cost is None
    assert result.supplier_usage_status == "unavailable"
    sql = [str(q.compile(dialect=dialect())) for q in session.queries]
    assert any("credit_reservations" in q and "generation_tasks.user_id" in q for q in sql)
    assert any("credit_ledger" in q and "generation_tasks.user_id" in q for q in sql)
    assert not session.rows


def test_daily_trend_fills_real_zero_days_and_keeps_task_and_settlement_dates_separate():
    session = dashboard_session()
    result = statistics.get_statistics(session, session.actor)
    assert result.trend_timezone == "UTC"
    assert result.trend_days == 14
    assert len(result.daily_trend) == 14
    assert result.daily_trend[0].date.isoformat() == "2026-10-04"
    assert result.daily_trend[-1].date.isoformat() == "2026-10-17"
    assert result.daily_trend[0].task_count == result.daily_trend[0].credits_consumed == 0
    assert result.daily_trend[-2].task_count == 3
    assert result.daily_trend[-2].credits_consumed == 8
    assert result.daily_trend[-1].task_count == 2
    assert result.daily_trend[-1].credits_consumed == 0
    trend_queries = session.queries[-6:-4]
    assert all("GROUP BY" in str(q) and "WHERE" in str(q) for q in trend_queries)
    assert "generation_tasks.created_at" in str(trend_queries[0])
    assert "credit_ledger.created_at" in str(trend_queries[1])


def test_zero_samples_are_null_rates_not_zero_and_do_not_invent_supplier_data():
    session = QuerySession(rows=[[], [], [], [], [], [], [], [], [], [], [(0, 0, 0)], [(0, 0)]])
    original_scalar = session.scalar
    session.scalar = lambda statement: (
        0 if statement.column_descriptions[0].get("entity") is CreditLedger
        else original_scalar(statement)
    )
    result = statistics.get_statistics(session, session.actor)
    assert result.credits_consumed == 0
    assert result.generated_count == result.terminal_count == 0
    assert result.success_rate is None
    assert result.credits_frozen == result.credits_released == 0
    assert result.by_agent == []
    assert all(day.task_count == day.credits_consumed == 0 for day in result.daily_trend)
    assert result.payment_revenue_status == "not_supported"
    assert result.supplier_cost_status == result.supplier_usage_status == "unavailable"


def test_non_admin_cannot_run_dashboard_queries():
    session = QuerySession(role="user")
    with pytest.raises(HTTPException) as caught:
        statistics.get_statistics(session, session.actor)
    assert caught.value.status_code == 403
    assert len(session.rows) == 0
    assert not any("GROUP BY" in str(q) for q in session.queries)


def test_zero_price_frozen_task_has_no_terminal_rate_and_zero_frozen_credits():
    session = QuerySession(rows=[
        [("RUNNING", 1)], [], [(AGENT, "RUNNING", "FROZEN", 1)], [],
        [(AGENT, 0)], [], [], [],
        [], [], [(0, 0, 0)], [(0, 0)],
    ])
    original_scalar = session.scalar
    session.scalar = lambda statement: (
        0 if statement.column_descriptions[0].get("entity") is CreditLedger
        else original_scalar(statement)
    )
    result = statistics.get_statistics(session, session.actor)
    row = result.by_agent[0]
    assert row.task_count == row.unsettled_count == 1
    assert row.terminal_count == row.credits_frozen == row.credits_consumed == 0
    assert row.success_rate is result.success_rate is None
    assert result.unsettled_count == 1
    assert result.credits_frozen == 0


def test_user_growth_and_activity_use_independent_period_distinct_counts():
    session = dashboard_session()
    result = statistics.get_statistics(session, session.actor)
    assert result.total_users == 12
    assert result.registered_today == 1
    assert result.registered_in_trend == 4
    assert result.active_today == 2
    # One user appeared on both days: summing daily active counts would be wrong.
    assert result.active_in_trend == 3
    assert result.active_user_basis == "generation_task_created"
    assert result.daily_trend[-2].registered_count == 3
    assert result.daily_trend[-1].registered_count == 1
    assert result.daily_trend[-2].active_user_count == 2
    assert result.daily_trend[-1].active_user_count == 2
    assert result.daily_trend[0].registered_count == 0
    assert result.daily_trend[0].active_user_count == 0
    queries = session.queries[-4:]
    compiled = [query.compile(dialect=dialect()) for query in queries]
    assert all("user" in query.params.values() for query in compiled)
    assert "count(DISTINCT" in str(compiled[1])
    assert "count(DISTINCT" in str(compiled[3])
    assert "generation_tasks.user_id = users.id" in str(compiled[1])
    assert "generation_tasks.user_id = users.id" in str(compiled[3])
    assert datetime(2026, 10, 4) in compiled[3].params.values()
    assert datetime(2026, 10, 18) in compiled[3].params.values()
