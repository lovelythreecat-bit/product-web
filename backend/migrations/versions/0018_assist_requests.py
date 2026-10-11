"""Independent completed prompt-assist receipts; no quota policy is chosen."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0018_assist_requests"
down_revision = "0017_event_payload_retention"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assist_requests",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("request_key", sa.String(128, collation="utf8mb4_bin"), primary_key=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("original", mysql.MEDIUMTEXT(), nullable=False),
        sa.Column("proposed", mysql.MEDIUMTEXT(), nullable=False),
        sa.Column("policy_version", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint("status = 'COMPLETED'", name="ck_assist_status"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_bin",
    )


def downgrade():
    op.drop_table("assist_requests")
