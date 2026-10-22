"""Account and session persistence; bearer and CSRF secrets are stored only as hashes."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, ForeignKeyConstraint, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user','admin')", name="ck_user_role"),
        CheckConstraint("status IN ('active','disabled')", name="ck_user_status"),
        CheckConstraint("auth_version >= 0", name="ck_user_auth_version"),
        CheckConstraint(
            "(avatar_file_id IS NULL AND avatar_file_version IS NULL) OR "
            "(avatar_file_id IS NOT NULL AND avatar_file_version IS NOT NULL)",
            name="ck_user_avatar_identity",
        ),
        ForeignKeyConstraint(
            ["avatar_file_id", "avatar_file_version", "id"],
            ["files.id", "files.version", "files.user_id"],
            name="fk_user_avatar_owner_version",
            use_alter=True,
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_normalized: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")
    status: Mapped[str] = mapped_column(String(16), default="active")
    auth_version: Mapped[int] = mapped_column(BigInteger, default=0)
    nickname: Mapped[str | None] = mapped_column(String(80))
    bio: Mapped[str | None] = mapped_column(String(500))
    shop_name: Mapped[str | None] = mapped_column(String(80))
    category: Mapped[str | None] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))
    avatar_file_id: Mapped[str | None] = mapped_column(String(36))
    avatar_file_version: Mapped[str | None] = mapped_column(String(36))
    last_login_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    auth_version: Mapped[int] = mapped_column(BigInteger)
    expires_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    revoked_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))


class RegistrationReceipt(Base):
    __tablename__ = "registration_receipts"
    request_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    account_normalized: Mapped[str] = mapped_column(String(64))
    config_version: Mapped[str] = mapped_column(ForeignKey("registration_credit_configs.version"))
