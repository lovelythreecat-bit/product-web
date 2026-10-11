"""Immutable grants and complete balance transitions."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CreditAccount(Base):
    __tablename__ = "credit_accounts"
    __table_args__ = (
        CheckConstraint(
            "available >= 0 AND frozen >= 0 AND consumed >= 0 AND credited_total >= 0",
            name="ck_credit_nonnegative",
        ),
        CheckConstraint(
            "available + frozen + consumed = credited_total", name="ck_credit_conservation"
        ),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    available: Mapped[int] = mapped_column(BigInteger, default=0)
    frozen: Mapped[int] = mapped_column(BigInteger, default=0)
    consumed: Mapped[int] = mapped_column(BigInteger, default=0)
    credited_total: Mapped[int] = mapped_column(BigInteger, default=0)


class CreditGrant(Base):
    __tablename__ = "credit_grants"
    __table_args__ = (
        UniqueConstraint("kind", "business_key", name="uq_grant_business"),
        CheckConstraint("amount >= 0", name="ck_grant_amount"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(32))
    business_key: Mapped[str] = mapped_column(String(128))
    amount: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(String(500))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class CreditReservation(Base):
    __tablename__ = "credit_reservations"
    __table_args__ = (
        CheckConstraint("amount >= 0 AND version >= 1", name="ck_reservation_amount"),
        CheckConstraint("state IN ('frozen','consumed','released')", name="ck_reservation_state"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    # generation_tasks is introduced by T07; its FK is attached by that migration.
    task_id: Mapped[str] = mapped_column(String(36), unique=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    state: Mapped[str] = mapped_column(String(16), default="frozen")
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class CreditLedger(Base):
    __tablename__ = "credit_ledger"
    __table_args__ = (CheckConstraint("amount >= 0", name="ck_ledger_amount"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    operation_key: Mapped[str] = mapped_column(String(200), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    grant_id: Mapped[str | None] = mapped_column(ForeignKey("credit_grants.id"))
    reservation_id: Mapped[str | None] = mapped_column(ForeignKey("credit_reservations.id"))
    task_id: Mapped[str | None] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(32))
    amount: Mapped[int] = mapped_column(BigInteger)
    balances_before: Mapped[dict] = mapped_column(JSON)
    balances_after: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class RegistrationCreditConfig(Base):
    __tablename__ = "registration_credit_configs"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_signup_amount"),
        CheckConstraint(
            "(mode='mock' AND test_only=1) OR (mode IN ('production','staging') AND test_only=0)",
            name="ck_signup_mode",
        ),
    )
    version: Mapped[str] = mapped_column(String(36), primary_key=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    mode: Mapped[str] = mapped_column(String(16))
    test_only: Mapped[bool] = mapped_column(Boolean)
    policy_version: Mapped[str] = mapped_column(String(128))
    reason: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class RegistrationCreditHead(Base):
    __tablename__ = "registration_credit_heads"
    mode: Mapped[str] = mapped_column(String(16), primary_key=True)
    version: Mapped[str] = mapped_column(ForeignKey("registration_credit_configs.version"))
