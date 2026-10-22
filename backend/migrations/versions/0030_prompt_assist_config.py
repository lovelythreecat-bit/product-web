"""Independent encrypted model configuration for prompt assistance."""

import sqlalchemy as sa
from alembic import op

revision = "0030_prompt_assist_config"
down_revision = "0029_readable_numbers"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("generation_parameter_configs", sa.Column("assist_base_url", sa.String(2048)))
    op.add_column("generation_parameter_configs", sa.Column("assist_model", sa.String(200)))
    op.add_column("generation_parameter_configs",
                  sa.Column("assist_key_ciphertext", sa.LargeBinary()))


def downgrade():
    raise RuntimeError("Historical encrypted parameter versions must be retained")
