"""Mutable execution identity separated from append-only admission snapshots."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class GenerationTask(Base):
    __tablename__ = "generation_tasks"
    __table_args__ = (
        Index("ix_task_recovery_due", "recovery_due_at", "lease_expires_at"),
        UniqueConstraint("id", "user_id", name="uq_task_owner"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_task_intent"),
        UniqueConstraint("agent_id", "upstream_id", name="uq_task_upstream"),
        ForeignKeyConstraint(
            ["conversation_id", "user_id"], ["conversations.id", "conversations.user_id"]
        ),
        ForeignKeyConstraint(
            ["capacity_reservation_id", "user_id"],
            ["capacity_reservations.id", "capacity_reservations.user_id"],
        ),
        CheckConstraint("state_version >= 1 AND fencing_token >= 0", name="ck_task_versions"),
        CheckConstraint(
            "state IN ('SUBMITTED','QUEUED','SUBMITTING','RUNNING','INVESTIGATING',"
            "'SAVING','SAVE_RECOVERY','SUCCEEDED','FAILED','MANUALLY_CLOSED')",
            name="ck_task_state",
        ),
        CheckConstraint(
            "settlement_state IN ('FROZEN','CONSUMED','RELEASED')", name="ck_task_settlement"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128, collation="utf8mb4_bin"))
    request_hash: Mapped[str] = mapped_column(String(64))
    agent_id: Mapped[str] = mapped_column(String(36))
    agent_version: Mapped[str] = mapped_column(String(128))
    external_submission_id: Mapped[str] = mapped_column(String(36), unique=True)
    upstream_id: Mapped[str | None] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(24), default="SUBMITTED")
    state_version: Mapped[int] = mapped_column(BigInteger, default=1)
    settlement_state: Mapped[str] = mapped_column(String(16), default="FROZEN")
    capacity_reservation_id: Mapped[str] = mapped_column(String(36), unique=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    fencing_token: Mapped[int] = mapped_column(BigInteger, default=0)
    recovery_due_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), server_default=text("CURRENT_TIMESTAMP(6)")
    )
    investigation_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class TaskSnapshot(Base):
    __tablename__ = "task_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["task_id", "user_id"], ["generation_tasks.id", "generation_tasks.user_id"]
        ),
        ForeignKeyConstraint(
            ["product_version", "user_id"], ["product_versions.version", "product_versions.user_id"]
        ),
    )
    task_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    product_version: Mapped[str] = mapped_column(String(36))
    input_snapshot: Mapped[dict] = mapped_column(JSON)
    agent_snapshot: Mapped[dict] = mapped_column(JSON)
    spec_snapshot: Mapped[dict] = mapped_column(JSON)
    price_snapshot: Mapped[dict] = mapped_column(JSON)
    quote: Mapped[dict] = mapped_column(JSON)
    policy_versions: Mapped[dict] = mapped_column(JSON)
    capacity_estimate: Mapped[dict] = mapped_column(JSON)


class TaskStateEvent(Base):
    __tablename__ = "task_state_events"
    __table_args__ = (
        UniqueConstraint("task_id", "state_version", name="uq_task_state_event"),
        ForeignKeyConstraint(
            ["task_id", "user_id"], ["generation_tasks.id", "generation_tasks.user_id"]
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    state_version: Mapped[int] = mapped_column(BigInteger)
    from_state: Mapped[str | None] = mapped_column(String(24))
    to_state: Mapped[str] = mapped_column(String(24))
    evidence: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
