"""Permanent public numbers; UUIDs remain the only routing/ownership identities.

The daily counter is global per resource kind and contains no account identifier.
Its upsert obtains an InnoDB row lock until the enclosing insert transaction ends.
Never commit here: a failed creation must roll back its counter increment as well.
"""

from datetime import UTC, datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import BigInteger, CheckConstraint, String, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

SHANGHAI = timezone(timedelta(hours=8))


class DisplayNumberCounter(Base):
    __tablename__ = "display_number_counters"
    __table_args__ = (
        CheckConstraint("kind IN ('H','T')", name="ck_display_number_kind"),
        CheckConstraint("`last_value` > 0", name="ck_display_number_positive"),
    )
    kind: Mapped[str] = mapped_column(String(1), primary_key=True)
    day: Mapped[str] = mapped_column(String(8), primary_key=True)
    last_value: Mapped[int] = mapped_column(BigInteger)


def allocate_display_number(connection, kind: Literal["H", "T"], created_at: datetime) -> str:
    if kind not in {"H", "T"}:
        raise ValueError("Unsupported display number kind")
    original = created_at.replace(tzinfo=UTC) if created_at.tzinfo is None else created_at
    day = original.astimezone(SHANGHAI).strftime("%Y%m%d")
    counter = DisplayNumberCounter.__table__
    connection.execute(
        insert(counter).values(kind=kind, day=day, last_value=1).on_duplicate_key_update(
            last_value=counter.c.last_value + 1,
        )
    )
    sequence = connection.scalar(
        select(counter.c.last_value).where(
            counter.c.kind == kind, counter.c.day == day,
        ).with_for_update()
    )
    return f"{kind}{day}-{sequence:06d}"


def display_number_default(kind: Literal["H", "T"]):
    """SQLAlchemy insert default also covers scripts constructing ORM rows directly."""
    def allocate(context):
        return allocate_display_number(
            context.connection, kind, context.get_current_parameters()["created_at"],
        )

    return allocate
