"""Stable newest-first pagination; cursors are resolved inside the same owner scope."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select


def numbered_page_rows(session, model, predicates, cursor, limit, *, page=None, cursor_reader=None):
    """Count the authorized result set and optionally jump directly to a page.

    Existing cursor callers retain their anchor rules. A numbered request never
    walks cursors or loads all matching records into application memory.
    """
    if type(limit) is not int or not 1 <= limit <= 100:
        raise HTTPException(422)
    if page is not None and (type(page) is not int or page < 1 or cursor is not None):
        raise HTTPException(422, "Use either a positive page number or a cursor")
    total = int(session.scalar(select(func.count()).select_from(model).where(*predicates)) or 0)
    if page is None:
        rows, next_cursor = (
            cursor_reader()
            if cursor_reader
            else page_rows(session, model, predicates, cursor, limit)
        )
    else:
        page = min(page, max(1, (total + limit - 1) // limit))
        rows = list(
            session.scalars(
                select(model)
                .where(*predicates)
                .order_by(model.created_at.desc(), model.id.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            ).all()
        )
        next_cursor = rows[-1].id if rows and page * limit < total else None
    return rows, next_cursor, {"total": total, "page": page, "page_size": limit}


def page_rows(session, model, predicates, cursor, limit, *, cursor_predicates=None):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise HTTPException(422)
    query = select(model).where(*predicates)
    if cursor:
        try:
            cursor = str(UUID(cursor))
        except ValueError:
            raise HTTPException(422) from None
        anchor_scope = predicates if cursor_predicates is None else cursor_predicates
        anchor = session.scalar(select(model).where(*anchor_scope, model.id == cursor))
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
