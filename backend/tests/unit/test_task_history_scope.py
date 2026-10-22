"""Inspect emitted history queries without opening or changing a database."""

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import mysql

from app.tasks import repository, routes

OWNER = "11111111-1111-4111-8111-111111111111"
CURSOR = "22222222-2222-4222-8222-222222222222"
CONVERSATION = "33333333-3333-4333-8333-333333333333"


def compiled(statement):
    return str(statement.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))


class QueryCapture:
    def __init__(self, anchor=True):
        self.statements = []
        self.anchor = anchor

    def scalar(self, statement):
        self.statements.append(compiled(statement))
        if self.anchor:
            return SimpleNamespace(id=CURSOR, created_at=datetime(2026, 10, 20))

    def scalars(self, statement):
        self.statements.append(compiled(statement))
        return SimpleNamespace(all=lambda: [])


@pytest.fixture
def principal(monkeypatch):
    # Identity and conversation reads are external to the query contract under test.
    monkeypatch.setattr(repository, "authenticate", lambda *_: None)
    monkeypatch.setattr(repository, "owned_conversation", lambda *_: None)
    return SimpleNamespace(user_id=OWNER)


def test_ordinary_history_and_cursor_exclude_every_quick_conversation(principal):
    session = QueryCapture()
    result = routes.list_tasks(
        session, principal, conversation_id=UUID(CONVERSATION), cursor=CURSOR,
        limit=20, task_type="ordinary",
    )
    assert result.items == []
    assert len(session.statements) == 2
    for sql in session.statements:
        assert "NOT (EXISTS" in sql
        assert "quick_generation_runs.conversation_id = generation_tasks.conversation_id" in sql
        assert "quick_generation_runs.user_id = generation_tasks.user_id" in sql
        assert f"generation_tasks.user_id = '{OWNER}'" in sql
        assert f"generation_tasks.conversation_id = '{CONVERSATION}'" in sql
    # Hidden ordinary tasks remain valid cursors, preserving deletion pagination.
    assert "history_deleted_at IS NULL" not in session.statements[0]
    assert "history_deleted_at IS NULL" in session.statements[1]


def test_default_history_preserves_quick_tasks_for_existing_consumers(principal):
    session = QueryCapture()
    result = repository.TaskRepository(session).list_tasks(principal, cursor=CURSOR)
    assert result.items == []
    assert len(session.statements) == 2
    assert all("quick_generation_runs" not in sql for sql in session.statements)


def test_ordinary_history_rejects_cursor_outside_its_filtered_scope(principal):
    session = QueryCapture(anchor=False)
    with pytest.raises(HTTPException) as failure:
        repository.TaskRepository(session).list_tasks(
            principal, cursor=CURSOR, task_type="ordinary",
        )
    assert failure.value.status_code == 422
    assert len(session.statements) == 1
    assert "NOT (EXISTS" in session.statements[0]
