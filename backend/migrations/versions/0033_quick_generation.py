"""Persist account-owned quick generation drafts and immutable admission batches."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME

revision = "0033_quick_generation"
down_revision = "0032_task_history_deletion"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quick_generation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id"),
                  nullable=False, unique=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", DATETIME(fsp=6), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_bin",
    )
    op.create_index("ix_quick_generation_runs_user_id", "quick_generation_runs", ["user_id"])
    op.create_index("ix_quick_generation_runs_updated_at", "quick_generation_runs", ["updated_at"])


def downgrade():
    op.drop_table("quick_generation_runs")
