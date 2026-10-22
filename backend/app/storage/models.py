"""Capacity and immutable file identities; all bytes are signed 64-bit integers."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class StoragePool(Base):
    __tablename__ = "storage_pools"
    __table_args__ = (
        CheckConstraint(
            "reserved_bytes >= 0 AND actual_bytes >= 0",
            name="ck_pool_capacity",
        ),
    )
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    reserved_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    actual_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    policy_version: Mapped[str] = mapped_column(String(128))


class StorageAccount(Base):
    __tablename__ = "storage_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "pool_id", name="uq_storage_account_pool"),
        CheckConstraint(
            "reserved_bytes >= 0 AND actual_bytes >= 0",
            name="ck_storage_account_capacity",
        ),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    pool_id: Mapped[str] = mapped_column(ForeignKey("storage_pools.id"))
    reserved_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    actual_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    policy_version: Mapped[str] = mapped_column(String(128))


class CapacityReservation(Base):
    __tablename__ = "capacity_reservations"
    __table_args__ = (
        UniqueConstraint("user_id", "intent_id", name="uq_capacity_intent"),
        UniqueConstraint("id", "user_id", name="uq_capacity_owner"),
        ForeignKeyConstraint(
            ["user_id", "pool_id"],
            ["storage_accounts.user_id", "storage_accounts.pool_id"],
            name="fk_capacity_account_pool",
        ),
        CheckConstraint("estimated_bytes > 0 AND actual_bytes >= 0", name="ck_reservation_bytes"),
        CheckConstraint("state IN ('reserved','finalized','released')", name="ck_capacity_state"),
        CheckConstraint("state = 'finalized' OR actual_bytes = 0", name="ck_capacity_actual_state"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("storage_accounts.user_id"))
    pool_id: Mapped[str] = mapped_column(ForeignKey("storage_pools.id"))
    intent_id: Mapped[str] = mapped_column(String(128))
    estimated_bytes: Mapped[int] = mapped_column(BigInteger)
    actual_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    state: Mapped[str] = mapped_column(String(16), default="reserved")
    policy_version: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class File(Base):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("id", "version", "user_id", name="uq_file_version_owner"),
        ForeignKeyConstraint(
            ["reservation_id", "user_id"],
            ["capacity_reservations.id", "capacity_reservations.user_id"],
            name="fk_file_reservation_owner",
        ),
        CheckConstraint("actual_bytes > 0", name="ck_file_bytes"),
        CheckConstraint("state IN ('durable','unavailable')", name="ck_file_state"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    internal_path: Mapped[str] = mapped_column(String(255), unique=True)
    actual_mime: Mapped[str] = mapped_column(String(64))
    actual_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(16), default="durable")
    deleted_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    reservation_id: Mapped[str] = mapped_column(ForeignKey("capacity_reservations.id"), index=True)
    deletion_policy_version: Mapped[str | None] = mapped_column(String(128))


class FileRef(Base):
    __tablename__ = "file_refs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["file_id", "version", "user_id"],
            ["files.id", "files.version", "files.user_id"],
            name="fk_ref_file_owner_version",
        ),
        UniqueConstraint("file_id", "version", "ref_type", "ref_id", name="uq_file_reference"),
        CheckConstraint(
            "ref_type IN ('task_input','task_result','message','work','avatar')",
            name="ck_file_ref_type",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    file_id: Mapped[str] = mapped_column(String(36))
    version: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    ref_type: Mapped[str] = mapped_column(String(32))
    ref_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class FileCleanup(Base):
    """Committed claim before unlink; completed is the exactly-once capacity receipt."""

    __tablename__ = "file_cleanups"
    __table_args__ = (CheckConstraint("state IN ('pending','completed')", name="ck_cleanup_state"),)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"), primary_key=True)
    policy_version: Mapped[str] = mapped_column(String(128))
    state: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    completed_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
