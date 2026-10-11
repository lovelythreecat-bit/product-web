"""Durable responsibility, immutable resolution evidence, and deduplicated alerts."""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, ForeignKey, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Investigation(Base):
    __tablename__ = "investigations"
    task_id: Mapped[str] = mapped_column(ForeignKey("generation_tasks.id"), primary_key=True)
    owner: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    policy_version: Mapped[str] = mapped_column(String(128))
    evidence: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(24))
    version: Mapped[int] = mapped_column(BigInteger)
    deadline_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    user_reason: Mapped[str | None] = mapped_column(String(500))


class Resolution(Base):
    __tablename__ = "investigation_resolutions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("investigations.task_id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[str] = mapped_column(ForeignKey("auth_sessions.id"))
    action: Mapped[str] = mapped_column(String(32))
    policy_version: Mapped[str] = mapped_column(String(128))
    evidence: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(String(500))
    before_version: Mapped[int] = mapped_column(BigInteger)
    after_version: Mapped[int] = mapped_column(BigInteger)
    task_version: Mapped[int] = mapped_column(BigInteger)
    outcome: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class InvestigationAlert(Base):
    __tablename__ = "investigation_alerts"
    key: Mapped[str] = mapped_column(String(180), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("generation_tasks.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    escalation_ref: Mapped[str] = mapped_column(String(128))
    evidence_ref: Mapped[str | None] = mapped_column(String(128))
    disposition: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
