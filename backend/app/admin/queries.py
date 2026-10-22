"""Literal searches and narrow diagnostic identities; no private projections."""

import re

from fastapi import HTTPException
from sqlalchemy import func, or_, select

from app.ledger.models import CreditAccount


def search_terms(q, columns):
    if q is None:
        return []
    if not isinstance(q, str) or len(q) > 128:
        raise HTTPException(422)
    q = q.strip()
    if not q:
        return []
    pattern = "%" + q.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
    return [or_(*(column.ilike(pattern, escape="!") for column in columns))]


def safe_identity(value):
    # Opaque identifiers only: no URLs, whitespace, request headers or errors.
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", value) is None:
        return None
    return value


def balance_totals(session):
    values = session.execute(
        select(
            *(
                func.coalesce(func.sum(getattr(CreditAccount, field)), 0)
                for field in ("available", "frozen", "consumed", "credited_total")
            )
        )
    ).one()
    return dict(zip(("available", "frozen", "consumed", "credited_total"), map(int, values)))
