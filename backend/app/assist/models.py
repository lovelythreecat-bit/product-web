"""Completed assist receipts; separate from generation and credit accounting."""

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.mysql import DATETIME, MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AssistRecord(Base):
    __tablename__ = "assist_requests"
    __table_args__ = (CheckConstraint("status = 'COMPLETED'", name="ck_assist_status"),)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    request_key: Mapped[str] = mapped_column(String(128, collation="utf8mb4_bin"), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    original: Mapped[str] = mapped_column(MEDIUMTEXT)
    proposed: Mapped[str] = mapped_column(MEDIUMTEXT)
    policy_version: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16))
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
