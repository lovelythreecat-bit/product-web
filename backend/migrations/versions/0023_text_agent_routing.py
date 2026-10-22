"""Pin nonsecret upstream model routing when accepting a task."""

import sqlalchemy as sa
from alembic import op

revision = "0023_text_agent_routing"
down_revision = "0022_user_profile_avatar"
branch_labels = None
depends_on = None


def upgrade():
    # Existing task snapshots remain intact; only new real text tasks require this field.
    op.add_column("task_snapshots", sa.Column("routing_snapshot", sa.JSON(), nullable=True))


def downgrade():
    raise RuntimeError("Task routing snapshots are retained; destructive rollback needs approval")
