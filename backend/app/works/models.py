"""One immutable published collection per original task, with owned file versions."""

from datetime import datetime

from sqlalchemy import ForeignKey, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Work(Base):
    __tablename__ = "works"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_work_owner"),
        ForeignKeyConstraint(
            ["task_id", "user_id"], ["generation_tasks.id", "generation_tasks.user_id"]
        ),
        ForeignKeyConstraint(
            ["conversation_id", "user_id"], ["conversations.id", "conversations.user_id"]
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    task_id: Mapped[str] = mapped_column(String(36), unique=True)
    conversation_id: Mapped[str] = mapped_column(String(36))
    manifest_id: Mapped[str] = mapped_column(ForeignKey("result_manifests.id"), unique=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    deletion_policy_version: Mapped[str | None] = mapped_column(String(128))
    deleted_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))


class WorkItem(Base):
    __tablename__ = "work_items"
    __table_args__ = (
        UniqueConstraint("work_id", "item_key", name="uq_work_item"),
        ForeignKeyConstraint(["work_id", "user_id"], ["works.id", "works.user_id"]),
        ForeignKeyConstraint(
            ["file_id", "file_version", "user_id"], ["files.id", "files.version", "files.user_id"]
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    work_id: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    item_key: Mapped[str] = mapped_column(String(128))
    file_id: Mapped[str] = mapped_column(String(36), unique=True)
    file_version: Mapped[str] = mapped_column(String(36))
