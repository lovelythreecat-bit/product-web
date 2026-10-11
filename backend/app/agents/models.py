"""Append-only submission intent and provenance; never settlement or final delivery."""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, ForeignKey, Index, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UpstreamAttempt(Base):
    __tablename__ = "upstream_attempts"
    __table_args__ = (Index("ix_upstream_attempt_task", "task_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("generation_tasks.id"))
    agent_id: Mapped[str] = mapped_column(String(36))
    agent_version: Mapped[str] = mapped_column(String(128))
    wire_agent_id: Mapped[str] = mapped_column(String(24))
    protocol_version: Mapped[str] = mapped_column(String(128))
    external_submission_id: Mapped[str] = mapped_column(String(36))
    endpoint_digest: Mapped[str] = mapped_column(String(64))
    snapshot_digest: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSON)
    scope: Mapped[dict] = mapped_column(JSON)
    fencing_token: Mapped[int] = mapped_column(BigInteger)
    retry_reference: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class UpstreamEvidence(Base):
    __tablename__ = "upstream_evidence"
    __table_args__ = (Index("ix_upstream_evidence_task", "task_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("generation_tasks.id"))
    attempt_id: Mapped[str | None] = mapped_column(ForeignKey("upstream_attempts.id"))
    kind: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
