"""Public content versions, CAS heads, and private-disk public-copy registry."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0021_site_content"
down_revision = "0020_content_grants"
branch_labels = None
depends_on = None


def table(name, *columns):
    return op.create_table(
        name, *columns, mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin"
    )


def upgrade():
    table(
        "site_content_versions",
        sa.Column("mode", sa.String(16), primary_key=True),
        sa.Column("version", sa.BigInteger(), primary_key=True),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("policy_version", sa.String(128), nullable=False),
        sa.Column("policy_versions", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "version > 0 AND status IN ('draft','approved')", name="ck_site_version"
        ),
    )
    heads = table(
        "site_content_heads",
        sa.Column("mode", sa.String(16), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("approved_version", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "version >= 0 AND (approved_version IS NULL OR approved_version <= version)",
            name="ck_site_head",
        ),
    )
    op.bulk_insert(heads, [dict(mode=m, version=0) for m in ("mock", "staging", "production")])
    table(
        "public_cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("work_id", sa.String(36), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("authorization_ref", sa.String(1024), nullable=False),
        sa.Column("policy_versions", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("withdrawn_at", mysql.DATETIME(fsp=6)),
        sa.Column("withdrawal_policy_version", sa.String(128)),
        sa.ForeignKeyConstraint(["work_id", "owner_id"], ["works.id", "works.user_id"]),
        sa.CheckConstraint(
            "state IN ('published','cleanup_pending','withdrawn')", name="ck_public_case_state"
        ),
    )
    op.create_index("ix_public_cases_mode", "public_cases", ["mode"])
    table(
        "public_case_copies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("public_cases.id"), nullable=False),
        sa.Column("internal_path", sa.String(255), unique=True, nullable=False),
        sa.Column("media_type", sa.String(64), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("actual_bytes", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_public_case_copies_case_id", "public_case_copies", ["case_id"])


def downgrade():
    for name in (
        "public_case_copies",
        "public_cases",
        "site_content_heads",
        "site_content_versions",
    ):
        op.drop_table(name)
