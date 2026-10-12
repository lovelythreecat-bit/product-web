"""Versioned public content and independent public-copy records."""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, ForeignKey, ForeignKeyConstraint, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SiteContentVersion(Base):
    __tablename__ = "site_content_versions"
    mode: Mapped[str] = mapped_column(String(16), primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    content: Mapped[dict] = mapped_column(JSON)
    content_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    policy_version: Mapped[str] = mapped_column(String(128))
    policy_versions: Mapped[dict] = mapped_column(JSON)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class SiteContentHead(Base):
    __tablename__ = "site_content_heads"
    mode: Mapped[str] = mapped_column(String(16), primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger)
    approved_version: Mapped[int | None] = mapped_column(BigInteger)


class PublicCase(Base):
    __tablename__ = "public_cases"
    __table_args__ = (ForeignKeyConstraint(["work_id", "owner_id"], ["works.id", "works.user_id"]),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mode: Mapped[str] = mapped_column(String(16), index=True)
    work_id: Mapped[str] = mapped_column(String(36))
    owner_id: Mapped[str] = mapped_column(String(36))
    authorization_ref: Mapped[str] = mapped_column(String(1024))
    policy_versions: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(24))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    withdrawal_policy_version: Mapped[str | None] = mapped_column(String(128))


class PublicCaseCopy(Base):
    __tablename__ = "public_case_copies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("public_cases.id"), index=True)
    # A new random copy path, never the private source path or file identity.
    internal_path: Mapped[str] = mapped_column(String(255), unique=True)
    media_type: Mapped[str] = mapped_column(String(64))
    sha256: Mapped[str] = mapped_column(String(64))
    actual_bytes: Mapped[int] = mapped_column(BigInteger)
