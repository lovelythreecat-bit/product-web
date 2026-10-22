"""Shared upstream execution slots across worker processes."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME

revision = "0036_upstream_execution_pools"
down_revision = "0035_observation_imports"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("generation_tasks", sa.Column("submission_not_before", DATETIME(fsp=6)))
    op.create_table(
        "upstream_execution_pools",
        sa.Column("scope_key", sa.String(64), primary_key=True),
        sa.Column("holders", sa.JSON(), nullable=False),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin",
    )


def downgrade():
    op.drop_table("upstream_execution_pools")
    op.drop_column("generation_tasks", "submission_not_before")
