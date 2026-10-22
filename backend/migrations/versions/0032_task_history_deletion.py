"""Hide owner-deleted task history without changing execution or settlement."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME

revision = "0032_task_history_deletion"
down_revision = "0031_remove_storage_limits"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "generation_tasks", sa.Column("history_deleted_at", DATETIME(fsp=6), nullable=True)
    )


def downgrade():
    op.drop_column("generation_tasks", "history_deleted_at")
