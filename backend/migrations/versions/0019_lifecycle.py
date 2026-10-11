"""Explicit deletion decisions and durable, resumable physical-cleanup claims."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0019_lifecycle"
down_revision = "0018_assist_requests"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("files", sa.Column("deletion_policy_version", sa.String(128), nullable=True))
    op.add_column("works", sa.Column("deletion_policy_version", sa.String(128), nullable=True))
    op.add_column("works", sa.Column("deleted_at", mysql.DATETIME(fsp=6), nullable=True))
    op.create_table(
        "file_cleanups",
        sa.Column(
            "file_id",
            sa.String(36, collation="utf8mb4_bin"),
            sa.ForeignKey("files.id"),
            primary_key=True,
        ),
        sa.Column("policy_version", sa.String(128), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("completed_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.CheckConstraint("state IN ('pending','completed')", name="ck_cleanup_state"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_bin",
    )


def downgrade():
    op.drop_table("file_cleanups")
    op.drop_column("works", "deleted_at")
    op.drop_column("works", "deletion_policy_version")
    op.drop_column("files", "deletion_policy_version")
