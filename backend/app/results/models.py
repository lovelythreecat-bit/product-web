"""Append-only save identities precede all disk I/O; delivery follows confirmed save commit."""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ResultManifestRecord(Base):
    __tablename__ = "result_manifests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("generation_tasks.id"), unique=True)
    receipt_id: Mapped[str] = mapped_column(ForeignKey("agent_events.id"), unique=True)
    identity: Mapped[dict] = mapped_column(JSON)
    manifest: Mapped[dict] = mapped_column(JSON)
    policy_versions: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class ResultSaveItem(Base):
    __tablename__ = "result_save_items"
    __table_args__ = (UniqueConstraint("manifest_id", "item_key", name="uq_result_item"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    manifest_id: Mapped[str] = mapped_column(ForeignKey("result_manifests.id"))
    item_key: Mapped[str] = mapped_column(String(128))
    file_id: Mapped[str] = mapped_column(String(36), unique=True)
    file_version: Mapped[str] = mapped_column(String(36))
    internal_path: Mapped[str] = mapped_column(String(255), unique=True)
    locator: Mapped[str] = mapped_column(String(2048))
    media_type: Mapped[str] = mapped_column(String(64))
    sha256: Mapped[str] = mapped_column(String(64))
    actual_bytes: Mapped[int] = mapped_column(BigInteger)


class ResultDeliveryRecord(Base):
    __tablename__ = "result_deliveries"
    manifest_id: Mapped[str] = mapped_column(ForeignKey("result_manifests.id"), primary_key=True)
    total_bytes: Mapped[int] = mapped_column(BigInteger)
    fencing_token: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
