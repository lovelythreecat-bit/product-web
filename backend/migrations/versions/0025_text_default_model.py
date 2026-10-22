"""Store only the selected remote model identity, never a local model copy."""

import sqlalchemy as sa
from alembic import op

revision = "0025_text_default_model"
down_revision = "0024_text_service_connection"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("text_service_connections", sa.Column("default_model_id", sa.String(36)))
    op.add_column("text_service_connections", sa.Column(
        "default_revision", sa.Integer(), nullable=False, server_default="0",
    ))


def downgrade():
    raise RuntimeError("Default model selection is retained; destructive rollback needs approval")
