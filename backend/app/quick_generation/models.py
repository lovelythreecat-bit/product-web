from datetime import datetime

from sqlalchemy import JSON, BigInteger, ForeignKey, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class QuickGenerationRun(Base):
    __tablename__ = "quick_generation_runs"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4",
                      "mysql_collate": "utf8mb4_bin"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), unique=True)
    version: Mapped[int] = mapped_column(BigInteger)
    state: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), index=True)
