"""Durable media upload, protocol and explicit user command state."""

import sqlalchemy as sa
from alembic import op

revision = "0028_media_execution"
down_revision = "0027_media_connections"
branch_labels = None
depends_on = None


def upgrade():
    options = dict(mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin")
    op.create_table("media_executions",
        sa.Column("task_id", sa.String(36), sa.ForeignKey("generation_tasks.id"), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False), **options)
    op.create_table("media_commands",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("generation_tasks.id"), nullable=False),
        sa.Column("operation", sa.String(24), nullable=False),
        sa.Column("request_key", sa.String(128, collation="utf8mb4_bin"), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("task_id", "operation", "request_key", name="uq_media_command_intent"),
        **options)
    op.create_index("ix_media_commands_task_id", "media_commands", ["task_id"])


def downgrade():
    raise RuntimeError("Original task and command evidence must be retained")
