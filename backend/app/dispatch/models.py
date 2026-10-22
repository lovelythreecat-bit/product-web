from datetime import datetime

from sqlalchemy import BigInteger, ForeignKeyConstraint, Index, String, UniqueConstraint
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OutboxEvent(Base):
    __tablename__ = "dispatch_outbox"
    __table_args__ = (
        Index("ix_outbox_pending", "dispatched_at", "ready_at"),
        UniqueConstraint("task_id", "state_version", "operation", name="uq_outbox_operation"),
        ForeignKeyConstraint(
            ["task_id", "user_id"], ["generation_tasks.id", "generation_tasks.user_id"]
        ),
    )
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36))
    task_id: Mapped[str] = mapped_column(String(36))
    state_version: Mapped[int] = mapped_column(BigInteger)
    operation: Mapped[str] = mapped_column(String(32))
    ready_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), index=True)
    attempts: Mapped[int] = mapped_column(BigInteger, default=0)
    dispatch_generation: Mapped[int] = mapped_column(BigInteger, default=1, server_default="1")
    claimed_generation: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    dispatched_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
