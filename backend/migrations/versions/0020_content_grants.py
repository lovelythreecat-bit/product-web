"""Independent content grants with explicit scope, authority and revocation."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0020_content_grants"
down_revision = "0019_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "content_access_grants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approver_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("expires_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("revoked_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("revoked_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("revoke_reason", sa.String(500), nullable=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("test_only", sa.Boolean(), nullable=False),
        sa.Column("authority_source", sa.String(128), nullable=False),
        sa.CheckConstraint("actor_id <> approver_id", name="ck_content_separate_approver"),
        sa.CheckConstraint("expires_at > created_at", name="ck_content_expiry"),
        sa.CheckConstraint(
            "(mode='mock' AND test_only=1) OR (mode IN ('staging','production') AND test_only=0)",
            name="ck_content_mode",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_bin",
    )
    op.create_index(
        "ix_content_grant_lookup",
        "content_access_grants",
        ["actor_id", "resource_type", "resource_id"],
    )


def downgrade():
    op.drop_table("content_access_grants")
