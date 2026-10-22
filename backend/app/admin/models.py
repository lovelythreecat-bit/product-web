"""Independent, revocable content access; no admin-role implicit grant."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, LargeBinary, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TextServiceConnection(Base):
    """Only the platform-to-textAgent connection; never stores model configurations."""

    __tablename__ = "text_service_connections"
    __table_args__ = (
        CheckConstraint("slot = 'text'", name="ck_text_service_slot"),
        CheckConstraint(
            "(revision = 0 AND base_url IS NULL AND key_ciphertext IS NULL) OR "
            "(revision > 0 AND base_url IS NOT NULL AND key_ciphertext IS NOT NULL)",
            name="ck_text_service_configured",
        ),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_bin"},
    )
    slot: Mapped[str] = mapped_column(String(16), primary_key=True)
    base_url: Mapped[str | None] = mapped_column(String(2048))
    key_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    revision: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    updated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    default_model_id: Mapped[str | None] = mapped_column(String(36))
    default_revision: Mapped[int] = mapped_column(Integer, default=0)


class ContentAccessGrant(Base):
    __tablename__ = "content_access_grants"
    __table_args__ = (
        Index("ix_content_grant_lookup", "actor_id", "resource_type", "resource_id"),
        CheckConstraint("actor_id <> approver_id", name="ck_content_separate_approver"),
        CheckConstraint("expires_at > created_at", name="ck_content_expiry"),
        CheckConstraint(
            "(mode='mock' AND test_only=1) OR (mode IN ('staging','production') AND test_only=0)",
            name="ck_content_mode",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    approver_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    resource_type: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[str] = mapped_column(String(36))
    reason: Mapped[str] = mapped_column(String(500))
    expires_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    revoked_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    revoked_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    revoke_reason: Mapped[str | None] = mapped_column(String(500))
    mode: Mapped[str] = mapped_column(String(16))
    test_only: Mapped[bool] = mapped_column(Boolean)
    authority_source: Mapped[str] = mapped_column(String(128))
