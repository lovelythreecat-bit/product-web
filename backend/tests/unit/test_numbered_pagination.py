"""Numbered queries count and page the same authorized, filtered row set."""

from datetime import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base

from app.common.pagination import numbered_page_rows

Base = declarative_base()


class Row(Base):
    __tablename__ = "pagination_rows"
    id = Column(String, primary_key=True)
    owner = Column(String)
    category = Column(Integer)
    created_at = Column(DateTime)


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Row(
                    id=f"00000000-0000-0000-0000-{i:012d}",
                    owner=owner,
                    category=i % 2,
                    created_at=datetime(2026, 10, 21),
                )
                for owner, numbers in [("mine", range(1, 12)), ("other", range(12, 20))]
                for i in numbers
            ]
        )
        session.commit()
        yield session
    engine.dispose()


def test_random_page_counts_only_matching_owner_rows_and_clamps(session):
    scope = [Row.owner == "mine", Row.category == 1]
    rows, cursor, meta = numbered_page_rows(session, Row, scope, None, 2, page=3)
    assert [int(row.id[-12:]) for row in rows] == [3, 1]
    assert cursor is None
    assert meta == {"total": 6, "page": 3, "page_size": 2}
    rows, _, meta = numbered_page_rows(session, Row, scope, None, 2, page=999)
    assert meta["page"] == 3
    assert len(rows) == 2


def test_empty_result_and_legacy_cursor(session):
    rows, _, meta = numbered_page_rows(session, Row, [Row.owner == "missing"], None, 2, page=4)
    assert rows == [] and meta == {"total": 0, "page": 1, "page_size": 2}
    rows, cursor, _ = numbered_page_rows(session, Row, [Row.owner == "mine"], None, 2)
    older, _, meta = numbered_page_rows(session, Row, [Row.owner == "mine"], cursor, 2)
    assert set(row.id for row in rows).isdisjoint(row.id for row in older)
    assert meta["total"] == 11 and meta["page"] is None


@pytest.mark.parametrize(
    "page,cursor,limit",
    [(0, None, 2), (-1, None, 2), (True, None, 2), (1, "cursor", 2), (1, None, 0)],
)
def test_invalid_or_mixed_paging_is_rejected(session, page, cursor, limit):
    with pytest.raises(HTTPException) as caught:
        numbered_page_rows(session, Row, [], cursor, limit, page=page)
    assert caught.value.status_code == 422
