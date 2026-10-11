"""Stable newest-first pagination; cursors are resolved inside the same owner scope."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, or_, select


def page_rows(session, model, predicates, cursor, limit):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise HTTPException(422)
    query = select(model).where(*predicates)
    if cursor:
        try:
            cursor = str(UUID(cursor))
        except ValueError:
            raise HTTPException(422) from None
        anchor = session.scalar(query.where(model.id == cursor))
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
