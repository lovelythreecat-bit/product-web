"""Policy records use caller-owned transactions and immutable content versions."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

CHECKS = {
    "ck_decision_id": "decision_id IN (" + ",".join(f"'D-{i:02}'" for i in range(1, 13)) + ")",
    "ck_policy_version": "CHAR_LENGTH(TRIM(version)) > 0",
    "ck_policy_mode": "mode IN ('mock', 'staging', 'production')",
    "ck_policy_status": "status IN ('draft', 'confirmed')",
    "ck_policy_test_only": "(mode = 'mock' AND test_only = 1) OR "
    "(mode IN ('staging', 'production') AND test_only = 0)",
    "ck_policy_payload": "JSON_TYPE(payload) = 'OBJECT'",
    "ck_policy_evidence": "JSON_TYPE(evidence_refs) = 'ARRAY'",
    "ck_policy_confirmation": "(status = 'draft' AND confirmed_by IS NULL "
    "AND confirmed_at IS NULL AND JSON_LENGTH(evidence_refs) = 0) OR "
    "(status = 'confirmed' AND confirmed_by IS NOT NULL "
    "AND CHAR_LENGTH(TRIM(confirmed_by)) = 36 AND confirmed_at IS NOT NULL "
    "AND JSON_LENGTH(evidence_refs) > 0)",
}


class DecisionVersionRecord(Base):
    __tablename__ = "decision_versions"
    __table_args__ = tuple(CheckConstraint(sql, name=name) for name, sql in CHECKS.items()) + (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_bin"},
    )

    decision_id: Mapped[str] = mapped_column(String(4), primary_key=True)
    version: Mapped[str] = mapped_column(String(128), primary_key=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    test_only: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    confirmed_by: Mapped[str | None] = mapped_column(String(36))
    confirmed_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False)
