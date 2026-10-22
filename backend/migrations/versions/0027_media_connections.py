"""Retain immutable, encrypted media connection versions for historical recovery."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME

revision = "0027_media_connections"
down_revision = "0026_generation_parameters"
branch_labels = None
depends_on = None


def upgrade():
    options = dict(mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin")
    op.create_table(
        "media_service_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("base_url", sa.String(2048), nullable=False),
        sa.Column("key_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("has_management_key", sa.Boolean(), nullable=False),
        sa.Column("default_config_id", sa.String(36)),
        sa.Column("image_model", sa.String(16)),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.CheckConstraint("kind IN ('image','video')", name="ck_media_connection_kind"),
        sa.CheckConstraint("revision > 0", name="ck_media_connection_revision"),
        sa.UniqueConstraint("kind", "revision", name="uq_media_connection_revision"),
        **options,
    )
    op.create_table(
        "media_service_connection_heads",
        sa.Column("kind", sa.String(16), primary_key=True),
        sa.Column("connection_id", sa.String(36), sa.ForeignKey("media_service_connections.id")),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("kind IN ('image','video')", name="ck_media_connection_head_kind"),
        **options,
    )
    op.bulk_insert(
        sa.table(
            "media_service_connection_heads",
            sa.column("kind", sa.String(16)),
            sa.column("revision", sa.Integer()),
        ),
        [{"kind": kind, "revision": 0} for kind in ("image", "video")],
    )
    for operation in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER media_connections_no_{operation.lower()} "
            f"BEFORE {operation} ON media_service_connections "
            "FOR EACH ROW SIGNAL SQLSTATE '45000' "
            "SET MESSAGE_TEXT='Media connection history is immutable'"
        )


def downgrade():
    raise RuntimeError("Historical connections must remain available; no destructive rollback")
