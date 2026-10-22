"""Administrative read/projection tests without an engine or DDL fixtures."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.admin import service, statistics
from app.admin.queries import search_terms
from app.auth.models import AuthSession, User
from app.common.types import Principal
from app.ledger.models import CreditAccount, CreditLedger
from app.tasks.models import TaskSnapshot


class Result:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def one(self):
        return self.rows[0]


class QuerySession:
    """External SQL transport is replaced; real authorization and projections run."""

    def __init__(self, rows=(), role="admin"):
        self.rows, self.queries = list(rows), []
        self.user = SimpleNamespace(id=str(uuid4()), role=role, status="active", auth_version=0)
        self.credential = SimpleNamespace(
            user_id=self.user.id,
            auth_version=0,
            revoked_at=None,
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        )
        self.actor = Principal(user_id=self.user.id, session_id=uuid4(), role=role, auth_version=0)
        self.quote = {
            "credits": 60,
            "spec_version": "s1",
            "price_version": "p1",
            "input_digest": "private-digest",
            "secret": "DO_NOT_PROJECT",
        }

    def scalar(self, statement):
        self.queries.append(statement)
        item = statement.column_descriptions[0]
        model = item.get("entity")
        if model is User:
            return "test-account" if item["name"] == "account_normalized" else self.user
        if model is AuthSession:
            return self.credential
        if model is TaskSnapshot:
            return self.quote
        if model is CreditLedger:
            return 8
        return None

    def execute(self, statement):
        self.queries.append(statement)
        return Result(self.rows.pop(0))

    def get(self, model, identity):
        return None

    def scalars(self, statement):
        self.queries.append(statement)
        return Result([])


def task(session):
    return SimpleNamespace(
        id=str(uuid4()),
        user_id=session.user.id,
        agent_id=str(uuid4()),
        agent_version="v1",
        state="INVESTIGATING",
        state_version=2,
        settlement_state="FROZEN",
        created_at=datetime(2026, 10, 13, 1),
        conversation_id=str(uuid4()),
        external_submission_id=str(uuid4()),
        upstream_id="https://private.invalid/?token=SECRET",
        investigation_reason="DO_NOT_PROJECT",
    )


def test_diagnostic_projects_quote_and_timeline_without_private_evidence_or_urls():
    session = QuerySession(
        rows=[
            [
                (1, None, "SUBMITTED", datetime(2026, 10, 13, 1)),
                (2, "SUBMITTED", "INVESTIGATING", datetime(2026, 10, 13, 2)),
            ]
        ]
    )
    row = task(session)
    result = service.diagnostic(session, row).model_dump(mode="json")
    assert result.get("conversation_id") == row.conversation_id
    assert result["fixed_credits"] == 60
    assert result["spec_version"] == "s1"
    assert result["price_version"] == "p1"
    assert result["upstream_id"] is None
    assert result["timeline"][1] == {
        "state_version": 2,
        "from_state": "SUBMITTED",
        "to_state": "INVESTIGATING",
        "created_at": "2026-10-13T02:00:00Z",
    }
    assert "DO_NOT_PROJECT" not in str(result) and "private-digest" not in str(result)


def test_global_users_summary_uses_database_totals_and_conserved_balances():
    function = getattr(service, "users_summary", None)
    assert callable(function), "Global user summary is missing"
    session = QuerySession(rows=[[(3, 2, 1, 1)], [(100, 20, 30, 150)]])
    result = function(session, session.actor).model_dump()
    assert result == {
        "total": 3,
        "active": 2,
        "disabled": 1,
        "admin_count": 1,
        "available": 100,
        "frozen": 20,
        "consumed": 30,
        "credited_total": 150,
    }


def test_new_summary_denies_non_admin_before_aggregate_queries():
    function = getattr(service, "users_summary", None)
    assert callable(function), "Global user summary is missing"
    session = QuerySession(role="user")
    with pytest.raises(HTTPException) as caught:
        function(session, session.actor)
    assert caught.value.status_code == 403
    assert session.rows == []
    assert not any("sum(" in str(query).lower() for query in session.queries)


def test_statistics_keeps_terminal_denominator_and_uses_consumed_ledger_by_agent():
    agent = str(uuid4())
    session = QuerySession(
        rows=[
            [("SUCCEEDED", 1), ("FAILED", 1), ("INVESTIGATING", 1), ("SAVE_RECOVERY", 1)],
            [("signup", 200), ("admin", 50)],
            [
                (agent, "SUCCEEDED", "CONSUMED", 1),
                (agent, "FAILED", "RELEASED", 1),
                (agent, "INVESTIGATING", "FROZEN", 1),
                (agent, "SAVE_RECOVERY", "FROZEN", 1),
            ],
            [(agent, 8)],
            [(agent, 12)],
            [(agent, 5)],
            [],
            [],
            [],
            [],
            [(0, 0, 0)],
            [(0, 0)],
        ]
    )
    result = statistics.get_statistics(session, session.actor).model_dump(mode="json")
    assert result["success_rate"] == 0.5
    assert result.get("unsettled_count") == 2
    assert result["by_agent"] == [
        {
            "agent_id": agent,
            "task_count": 4,
            "succeeded_count": 1,
            "failed_count": 1,
            "unsettled_count": 2,
            "credits_consumed": 8,
            "terminal_count": 2,
            "manually_closed_count": 0,
            "success_rate": 0.5,
            "credits_frozen": 12,
            "credits_released": 5,
        }
    ]
    assert result["supplier_cost"] is None


@pytest.mark.parametrize(
    "name", ["users_summary", "ledger_summary", "tasks_summary", "audit_summary"]
)
def test_every_new_summary_rechecks_live_admin_authority(name):
    session = QuerySession(role="user")
    with pytest.raises(HTTPException) as caught:
        getattr(service, name)(session, session.actor)
    assert caught.value.status_code == 403
    assert not any("group by" in str(query).lower() for query in session.queries)


def test_search_treats_wildcards_as_literal_characters_and_uses_bound_parameters():
    from sqlalchemy import select
    from sqlalchemy.dialects.mysql import dialect

    predicate = search_terms("a%_!b", [User.account_normalized])[0]
    compiled = select(User.id).where(predicate).compile(dialect=dialect())
    assert list(compiled.params.values()) == ["%a!%!_!!b%"]
    assert "a%_!b" not in str(compiled)
    assert "ESCAPE '!'" in str(compiled)
    assert search_terms("  ", [User.id]) == []


def test_audit_summary_counts_only_recorded_actions():
    session = QuerySession(rows=[[("admin_credit_grant", 2), ("catalog_price", 1)]])
    result = service.audit_summary(session, session.actor).model_dump()
    assert result == {"total": 3, "action_counts": {"admin_credit_grant": 2, "catalog_price": 1}}
    assert "password_reset" not in result["action_counts"]


def test_summary_http_route_returns_contract_without_uuid_capture_or_database():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.admin.routes import router
    from app.auth.routes import require_active_principal
    from app.db import get_session

    session = QuerySession(rows=[[(3, 2, 1, 1)], [(100, 20, 30, 150)]])
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[require_active_principal] = lambda: session.actor
    with TestClient(app) as client:
        response = client.get("/api/v1/admin/users/summary")
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert response.json()["credited_total"] == 150


def test_platform_ledger_projects_real_operator_and_complete_balance_transition():
    session = QuerySession()
    operator, grant_id = str(uuid4()), str(uuid4())
    entry = CreditLedger(
        id=str(uuid4()),
        user_id=session.user.id,
        grant_id=grant_id,
        reservation_id=None,
        task_id=None,
        kind="admin",
        amount=50,
        balances_before={"available": 100, "frozen": 20, "consumed": 30},
        balances_after={"available": 150, "frozen": 20, "consumed": 30},
        reason="Trial grant",
        created_at=datetime(2026, 10, 13, 1),
    )
    session.rows = [[(session.user.id, "target-shop")], [(grant_id, operator)]]

    def scalars(statement):
        session.queries.append(statement)
        return Result([entry])

    session.scalars = scalars
    result = service.list_ledger(session, session.actor, None, 20).model_dump(mode="json")
    assert result["items"][0]["operator"] == operator
    assert result["items"][0]["account"] == "target-shop"
    assert result["items"][0]["balances_after"] == {
        "available": 150,
        "frozen": 20,
        "consumed": 30,
    }
    assert result["next_cursor"] is None


def test_user_projection_adds_database_usage_without_password_or_biography():
    session = QuerySession()
    target = User(
        id=str(uuid4()),
        account_normalized="target-shop",
        nickname="Shop",
        role="user",
        status="active",
        auth_version=0,
        created_at=datetime(2026, 10, 13, 1),
        password_hash="DO_NOT_PROJECT",
        bio="PRIVATE_BIO",
        shop_name="Shop name",
    )
    balance = CreditAccount(
        user_id=target.id, available=100, frozen=20, consumed=30, credited_total=150
    )
    session.rows = [[(target.id, 12)]]

    def scalars(statement):
        session.queries.append(statement)
        model = statement.column_descriptions[0]["entity"]
        return Result([target] if model is User else [balance])

    session.scalars = scalars
    result = service.list_users(session, session.actor, None, 20).model_dump(mode="json")
    assert result["items"][0]["task_count"] == 12
    assert result["items"][0]["available"] == 100
    assert result["items"][0]["shop_name"] == "Shop name"
    assert "DO_NOT_PROJECT" not in str(result) and "PRIVATE_BIO" not in str(result)


def test_admin_ledger_resolves_task_name_from_its_owner_snapshot_only():
    session = QuerySession()
    task_id = str(uuid4())
    entry = CreditLedger(
        id=str(uuid4()), user_id=session.user.id, grant_id=None,
        reservation_id=str(uuid4()), task_id=task_id, kind="consume", amount=8,
        balances_before={"available": 100, "frozen": 8, "consumed": 0},
        balances_after={"available": 100, "frozen": 0, "consumed": 8},
        reason="Do not use this as title", created_at=datetime(2026, 10, 13, 1),
    )
    snapshot = TaskSnapshot(
        task_id=task_id, user_id=session.user.id,
        input_snapshot={"product": {"name": " 陶瓷杯 "}, "instructions": "PRIVATE_INSTRUCTION"},
        agent_snapshot={"kind": "image"},
    )
    session.rows = [[(session.user.id, "target-shop")]]

    def scalars(statement):
        session.queries.append(statement)
        model = statement.column_descriptions[0]["entity"]
        return Result([entry] if model is CreditLedger else [snapshot])

    session.scalars = scalars
    result = service.list_ledger(session, session.actor, None, 20).model_dump(mode="json")
    assert result["items"][0]["task_name"] == "陶瓷杯图片"
    assert "PRIVATE_INSTRUCTION" not in str(result)
    snapshot_query = session.queries[-1]
    assert "task_snapshots.user_id" in str(snapshot_query)
    assert (task_id, session.user.id) in next(iter(snapshot_query.compile().params.values()))

    # Even an incorrect transport result must not attach another owner's task name.
    snapshot.user_id = str(uuid4())
    session.rows = [[(session.user.id, "target-shop")]]
    result = service.list_ledger(session, session.actor, None, 20)
    assert result.items[0].task_name is None
