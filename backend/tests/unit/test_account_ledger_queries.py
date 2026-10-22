"""Owner ledger filters and summaries use mocked SQL transport only."""
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects.mysql import dialect

from app.ledger import reads
from app.ledger.models import CreditLedger
from app.tasks.models import TaskSnapshot


class Result:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class Session:
    def __init__(self):
        self.owner = str(uuid4())
        self.task_id = str(uuid4())
        self.principal = SimpleNamespace(user_id=self.owner)
        self.queries = []
        self.row = SimpleNamespace(
            id=str(uuid4()), user_id=self.owner, task_id=self.task_id, grant_id=None,
            reservation_id=None, kind="consume", amount=8, reason="完成结算",
            balances_before={"available": 20, "frozen": 8, "consumed": 0},
            balances_after={"available": 20, "frozen": 0, "consumed": 8},
            created_at=datetime(2026, 10, 20, 8),
        )

    def scalar(self, query):
        self.queries.append(query)
        return None

    def scalars(self, query):
        self.queries.append(query)
        model = query.column_descriptions[0]["entity"]
        if model is CreditLedger:
            return Result([self.row])
        if model is TaskSnapshot:
            return Result([SimpleNamespace(
                task_id=self.task_id, agent_snapshot={"kind": "image"},
                input_snapshot={"product": {"name": "原始陶瓷杯"}},
            )])
        raise AssertionError(model)

    def execute(self, query):
        self.queries.append(query)
        return Result([("copy", 24), ("image", 8), ("video", 60), (None, 2)])


@pytest.fixture(autouse=True)
def no_auth_transport(monkeypatch):
    monkeypatch.setattr(reads, "authenticate", lambda session, principal: None)


def test_dates_filter_owner_ledger_and_totals_ignore_pagination():
    session = Session()
    tz = timezone(timedelta(hours=8))
    start = datetime(2026, 10, 20, tzinfo=tz)
    end = datetime(2026, 10, 21, tzinfo=tz)
    page = reads.AccountReads(session).ledger(
        session.principal, limit=1, start_time=start, end_time=end,
    )
    assert page.items[0].task_name == "原始陶瓷杯图片"
    assert page.consumption.model_dump(by_alias=True) == {
        "copy": 24, "image": 8, "video": 60, "other": 2,
    }
    queries = [query.compile(dialect=dialect()) for query in session.queries]
    ledger = next(q for q in queries if "credit_ledger.id" in str(q) and "LIMIT" in str(q))
    assert "credit_ledger.user_id" in str(ledger)
    assert "credit_ledger.created_at >=" in str(ledger)
    assert "credit_ledger.created_at <" in str(ledger)
    assert datetime(2026, 10, 19, 16) in ledger.params.values()
    assert datetime(2026, 10, 20, 16) in ledger.params.values()
    summary = next(q for q in queries if "sum(" in str(q))
    assert "LIMIT" not in str(summary)
    assert "consume" in summary.params.values()
    assert session.owner in summary.params.values()
    assert "task_snapshots.user_id = credit_ledger.user_id" in str(summary)
    assert "credit_ledger.created_at >=" in str(summary)
    assert "credit_ledger.created_at <" in str(summary)
    snapshots = next(q for q in queries if "task_snapshots.input_snapshot" in str(q))
    assert session.owner in snapshots.params.values()


@pytest.mark.parametrize("start,end", [
    (datetime(2026, 10, 21, tzinfo=UTC), datetime(2026, 10, 20, tzinfo=UTC)),
    (datetime(2026, 10, 20, tzinfo=UTC), datetime(2026, 10, 20, tzinfo=UTC)),
    (datetime(2026, 10, 20), None),
])
def test_invalid_ranges_do_not_run_ledger_queries(start, end):
    session = Session()
    with pytest.raises(HTTPException) as caught:
        reads.AccountReads(session).ledger(session.principal, start_time=start, end_time=end)
    assert caught.value.status_code == 422
    assert not session.queries


def test_foreign_cursor_remains_not_found():
    session = Session()
    with pytest.raises(HTTPException) as caught:
        reads.AccountReads(session).ledger(session.principal, cursor=str(uuid4()))
    assert caught.value.status_code == 404
    assert len(session.queries) == 1
    assert session.owner in session.queries[0].compile().params.values()


def test_zero_consume_rows_and_missing_snapshot_do_not_invent_usage_or_task_name():
    session = Session()
    original = session.scalars
    session.scalars = lambda query: (
        Result([]) if query.column_descriptions[0]["entity"] is TaskSnapshot else original(query)
    )
    session.execute = lambda query: Result([])
    page = reads.AccountReads(session).ledger(session.principal)
    assert page.items[0].task_name is None
    assert page.consumption.model_dump(by_alias=True) == {
        "copy": 0, "image": 0, "video": 0, "other": 0,
    }
