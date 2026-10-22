"""Fence each durable outbox dispatch generation independently of task version."""

import sqlalchemy as sa
from alembic import op

revision = "0034_dispatch_generations"
down_revision = "0033_quick_generation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("dispatch_outbox", sa.Column(
        "dispatch_generation", sa.BigInteger(), nullable=False, server_default="1"))
    op.add_column("dispatch_outbox", sa.Column(
        "claimed_generation", sa.BigInteger(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("dispatch_outbox", "claimed_generation")
    op.drop_column("dispatch_outbox", "dispatch_generation")
