from datetime import datetime

from sqlalchemy import JSON, BigInteger, ForeignKey, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DurableEvent(Base):
    __tablename__ = "durable_events"
    __table_args__ = (
        UniqueConstraint("user_id", "event_seq", name="uq_durable_sequence"),
        UniqueConstraint("user_id", "event_key", name="uq_durable_intent"),
        ForeignKeyConstraint(
            ["task_id", "user_id"], ["generation_tasks.id", "generation_tasks.user_id"]
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    task_id: Mapped[str] = mapped_column(String(36))
    event_seq: Mapped[int] = mapped_column(BigInteger)
    event_key: Mapped[str] = mapped_column(String(160, collation="utf8mb4_bin"))
    event_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
