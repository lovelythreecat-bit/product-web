"""Account-owned conversations, immutable product versions and persisted messages."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Computed,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.common.display_numbers import display_number_default
from app.db import Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("id", "user_id", name="uq_conversation_owner"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_number: Mapped[str] = mapped_column(
        String(32), unique=True, default=display_number_default("H"),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("id", "user_id", name="uq_product_owner"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))


class ProductVersion(Base):
    __tablename__ = "product_versions"
    __table_args__ = (
        UniqueConstraint("product_id", "version", name="uq_product_version"),
        UniqueConstraint("version", "user_id", name="uq_product_version_owner"),
        ForeignKeyConstraint(["product_id", "user_id"], ["products.id", "products.user_id"]),
    )
    version: Mapped[str] = mapped_column(String(36), primary_key=True)
    product_id: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    product: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["conversation_id", "user_id"], ["conversations.id", "conversations.user_id"]
        ),
        ForeignKeyConstraint(
            ["task_id", "user_id"], ["generation_tasks.id", "generation_tasks.user_id"]
        ),
        UniqueConstraint("final_task_id", name="uq_message_final_task"),
        CheckConstraint(
            "kind <> 'final' OR (task_id IS NOT NULL AND role='assistant')", name="ck_final_task"
        ),
        CheckConstraint("kind IN ('authored','final')", name="ck_message_kind"),
        CheckConstraint("role IN ('user','assistant')", name="ck_message_role"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    conversation_id: Mapped[str] = mapped_column(String(36))
    task_id: Mapped[str | None] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(16))
    final_task_id: Mapped[str | None] = mapped_column(
        String(36), Computed("CASE WHEN kind='final' THEN task_id ELSE NULL END", persisted=True)
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
