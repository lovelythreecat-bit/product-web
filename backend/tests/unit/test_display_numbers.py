"""Readable identifiers without database access or schema-changing test fixtures."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects.mysql import dialect
from sqlalchemy.schema import CreateTable

from app.common.display_numbers import (
    DisplayNumberCounter,
    allocate_display_number,
    display_number_default,
)
from app.conversations.service import conversation_view, owned_conversation
from app.tasks.repository import TaskRepository, task_view


class CounterConnection:
    def __init__(self, sequence):
        self.sequence = sequence
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)

    def scalar(self, statement):
        self.statements.append(statement)
        return self.sequence


def test_counter_constraint_quotes_mysql_reserved_last_value_identifier():
    ddl = str(CreateTable(DisplayNumberCounter.__table__).compile(dialect=dialect()))
    assert 'CHECK (`last_value` > 0)' in ddl


@pytest.mark.parametrize("kind", ["H", "T"])
def test_number_uses_shanghai_creation_date_and_six_digit_sequence(kind):
    connection = CounterConnection(12)
    result = allocate_display_number(connection, kind, datetime(2026, 10, 15, 16, tzinfo=UTC))
    assert result == f"{kind}20261016-000012"
    insert, read = [statement.compile(dialect=dialect()) for statement in connection.statements]
    assert "ON DUPLICATE KEY UPDATE" in str(insert)
    assert "last_value +" in str(insert).replace("`", "")
    assert "FOR UPDATE" in str(read)
    assert "20261016" in insert.params.values()
    assert not any("user" in str(statement).lower() for statement in connection.statements)


def test_numbers_keep_growing_beyond_six_digits_without_reuse():
    assert allocate_display_number(
        CounterConnection(1000000), "T", datetime(2026, 10, 16)
    ) == "T20261016-1000000"


def test_orm_default_allocates_in_the_insert_transaction_from_original_created_at():
    context = SimpleNamespace(
        connection=CounterConnection(2),
        get_current_parameters=lambda: {"created_at": datetime(2026, 10, 15, 15, 59)},
    )
    assert display_number_default("H")(context) == "H20261015-000002"


def test_conversation_projection_keeps_persisted_number_and_internal_id():
    row = SimpleNamespace(
        id=str(uuid4()), display_number="H20261001-000045", title="商品资料",
        created_at=datetime(2026, 10, 1),
    )
    value = conversation_view(row).model_dump(mode="json")
    assert value["display_number"] == row.display_number
    assert value["conversation_id"] == row.id


def test_task_projection_preserves_number_across_state_changes_and_replay():
    identity = str(uuid4())
    row = SimpleNamespace(
        id=identity, display_number="T20261001-000007", state="QUEUED", state_version=1,
        settlement_state="FROZEN", investigation_reason=None,
        created_at=datetime(2026, 10, 1),
    )
    snapshot = SimpleNamespace(quote={
        "spec_id": str(uuid4()), "spec_version": "v1", "price_version": "v1",
        "agent_version": "v1", "policy_versions": {}, "credits": 1, "input_digest": "x",
    })
    session = SimpleNamespace(scalar=Mock(side_effect=[
        snapshot, row.created_at, snapshot, row.created_at,
    ]), scalars=lambda _: [])
    first = task_view(session, row).model_dump(mode="json")
    row.state, row.state_version = "RUNNING", 2
    second = task_view(session, row).model_dump(mode="json")
    assert first["display_number"] == second["display_number"] == row.display_number
    assert first["task_id"] == second["task_id"] == identity


def test_readable_number_does_not_add_an_owner_check_bypass(monkeypatch):
    from app.tasks import repository

    owner, foreign = str(uuid4()), str(uuid4())
    queries = []

    def no_owned_row(statement):
        queries.append(statement)
        return None

    session = SimpleNamespace(scalar=no_owned_row)
    monkeypatch.setattr(repository, "authenticate", lambda *_: None)
    with pytest.raises(HTTPException) as conversation_error:
        owned_conversation(session, owner, foreign)
    with pytest.raises(HTTPException) as task_error:
        TaskRepository(session).read_task(SimpleNamespace(user_id=owner), foreign)
    assert conversation_error.value.status_code == task_error.value.status_code == 404
    for query in queries:
        compiled = query.compile(dialect=dialect())
        assert owner in compiled.params.values()
        assert foreign in compiled.params.values()
        assert "user_id" in str(compiled)


def test_task_detail_contains_persisted_owned_conversation_number(monkeypatch):
    from app.tasks import repository

    owner, conversation_id = str(uuid4()), str(uuid4())
    row = SimpleNamespace(
        id=str(uuid4()), user_id=owner, conversation_id=conversation_id,
        agent_id=str(uuid4()),
    )
    snapshot = SimpleNamespace(
        routing_snapshot=None, agent_snapshot={}, input_snapshot={
            "product_version": "v1", "product": {}, "instruction": "商品文案",
            "material_versions": [], "parameters": {},
        }, policy_versions={},
    )
    owned_lookups = []

    def owned(session, user_id, identity):
        owned_lookups.append((user_id, identity))
        return SimpleNamespace(display_number="H20261001-000003")

    task = dict(
        task_id=row.id, display_number="T20261001-000007", state="QUEUED", state_version=1,
        settlement_state="FROZEN", work_ids=[], investigation_reason=None,
        created_at=datetime(2026, 10, 1, tzinfo=UTC),
        updated_at=datetime(2026, 10, 1, tzinfo=UTC),
        quote=dict(spec_id=str(uuid4()), spec_version="v1", price_version="v1",
                   agent_version="v1", policy_versions={}, credits=1, input_digest="x"),
    )
    monkeypatch.setattr(repository, "authenticate", lambda *_: None)
    monkeypatch.setattr(repository, "owned_conversation", owned)
    monkeypatch.setattr(repository, "task_view", lambda *_: task)
    session = SimpleNamespace(scalar=lambda _: row, get=lambda *_: snapshot)
    detail = TaskRepository(session).read_task(SimpleNamespace(user_id=owner), row.id)
    assert detail.model_dump(mode="json")["conversation_display_number"] == "H20261001-000003"
    assert owned_lookups == [(owner, conversation_id)]


def test_historical_migration_keeps_stable_order_and_seeds_daily_counters(monkeypatch):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "migrations/versions/0029_readable_numbers.py"
    spec = importlib.util.spec_from_file_location("readable_numbers_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    records = [
        {"id": "a", "created_at": datetime(2026, 10, 15, 15, 59)},
        {"id": "b", "created_at": datetime(2026, 10, 15, 16)},
        {"id": "c", "created_at": datetime(2026, 10, 15, 16)},
    ]
    updates, selections, seeds = [], [], []

    def execute(statement):
        if statement.is_select:
            selections.append(str(statement))
            return SimpleNamespace(mappings=lambda: records)
        updates.append(statement.compile().params)

    operation = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(execute=execute),
        bulk_insert=lambda _, values: seeds.extend(values),
        create_table=lambda *_, **__: None, add_column=lambda *_, **__: None,
        alter_column=lambda *_, **__: None, create_unique_constraint=lambda *_, **__: None,
        execute=lambda *_: None,
    )
    monkeypatch.setattr(migration, "op", operation)
    migration.upgrade()
    assert [item["display_number"] for item in updates] == [
        "H20261015-000001", "H20261016-000001", "H20261016-000002",
        "T20261015-000001", "T20261016-000001", "T20261016-000002",
    ]
    assert seeds == [
        {"kind": kind, "day": day, "last_value": count}
        for kind in ("H", "T") for day, count in (("20261015", 1), ("20261016", 2))
    ]
    assert all("created_at" in sql.split("ORDER BY")[1] for sql in selections)
    assert all(".id" in sql.split("ORDER BY")[1] for sql in selections)
