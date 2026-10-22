"""Work search/paging contract without a database connection or SQL execution."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects import mysql

from app.works import service as module
from app.works.models import Work


@pytest.fixture
def setup(monkeypatch):
    session = Mock()
    principal = SimpleNamespace(user_id=uuid4())
    monkeypatch.setattr(module, "authenticate", Mock())
    session.scalars.return_value.all.return_value = []
    return module.WorkService(session), session, principal


def test_numbered_page_reports_total_and_corrects_removed_last_page(setup):
    service, session, principal = setup
    session.scalar.return_value = 12
    result = service.list_works(principal, page=2, limit=12)
    assert (result.total, result.page, result.page_size, result.next_cursor) == (12, 1, 12, None)
    statement = session.scalars.call_args.args[0]
    assert statement._offset_clause.value == 0
    assert statement._limit_clause.value == 12


def test_numbered_page_counts_filtered_owner_scope_before_offset(setup):
    service, session, principal = setup
    session.scalar.return_value = 30
    result = service.list_works(principal, kind="image", q="杯", page=2, limit=12)
    assert (result.total, result.page) == (30, 2)
    count = session.scalar.call_args.args[0]
    rows = session.scalars.call_args.args[0]
    assert str(count.whereclause) == str(rows.whereclause)
    params = rows.compile(dialect=mysql.dialect()).params
    assert str(principal.user_id) in params.values()
    assert "杯" in params.values() and "image" in params.values()
    assert rows._offset_clause.value == 12


def test_search_treats_percent_and_underscore_as_literal_characters(setup):
    service, _, principal = setup
    predicates = service._predicates(principal, q="  Cup_100%  ")
    statement = select(Work).where(*predicates).compile(dialect=mysql.dialect())
    assert "cup/_100/%" in statement.params.values()
    assert "ESCAPE '/'" in str(statement)


def test_existing_cursor_mode_keeps_the_original_cursor_contract(setup, monkeypatch):
    service, _, principal = setup
    paging = Mock(return_value=([], "next-work"))
    monkeypatch.setattr(module, "page_rows", paging)
    result = service.list_works(principal, limit=20)
    assert result.items == [] and result.next_cursor == "next-work"
    assert result.total is None and result.page is None
    assert paging.call_args.args[-2:] == (None, 20)


@pytest.mark.parametrize(
    "arguments",
    [dict(page=0), dict(page=True), dict(page=1, cursor="id"), dict(limit=101), dict(q="x" * 121)],
)
def test_rejects_invalid_or_mixed_pagination_before_query(setup, arguments):
    service, session, principal = setup
    with pytest.raises(HTTPException) as error:
        service.list_works(principal, **arguments)
    assert error.value.status_code == 422
    session.scalar.assert_not_called()
    session.scalars.assert_not_called()
