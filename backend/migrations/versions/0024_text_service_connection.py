"""Store the web-to-textAgent connection; model data stays in textAgent."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0024_text_service_connection"
down_revision = "0023_text_agent_routing"
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table(
        "text_service_connections",
        sa.Column("slot", sa.String(16), primary_key=True),
        sa.Column("base_url", sa.String(2048), nullable=True),
        sa.Column("key_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("updated_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.CheckConstraint("slot = 'text'", name="ck_text_service_slot"),
        sa.CheckConstraint(
            "(revision = 0 AND base_url IS NULL AND key_ciphertext IS NULL) OR "
            "(revision > 0 AND base_url IS NOT NULL AND key_ciphertext IS NOT NULL)",
            name="ck_text_service_configured",
        ),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin",
    )
    # A permanent singleton also serializes concurrent first-time configuration.
    op.bulk_insert(table, [{"slot": "text", "revision": 0}])


def downgrade():
    raise RuntimeError("Service credentials are retained; destructive rollback needs approval")
