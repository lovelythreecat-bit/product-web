"""Configurable public Logo name, separate from approved marketing content."""

import sqlalchemy as sa
from alembic import op

revision = "0037_site_brand"
down_revision = "0036_upstream_execution_pools"
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table(
        "site_brands",
        sa.Column("mode", sa.String(16), primary_key=True),
        sa.Column("name", sa.String(24), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin",
    )
    op.bulk_insert(table, [
        {"mode": mode, "name": "映作", "version": 0}
        for mode in ("mock", "staging", "production")
    ])


def downgrade():
    op.drop_table("site_brands")
