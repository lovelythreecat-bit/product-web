"""Three nullable per-kind prices; deliberately no default generation fees."""

import sqlalchemy as sa
from alembic import op

revision = "0026_generation_parameters"
down_revision = "0025_text_default_model"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "generation_parameter_configs",
        sa.Column("version", sa.String(36), primary_key=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("text_price", sa.BigInteger()),
        sa.Column("image_price", sa.BigInteger()),
        sa.Column("video_price", sa.BigInteger()),
        sa.CheckConstraint("mode IN ('mock','staging','production')", name="ck_parameter_mode"),
        *[
            sa.CheckConstraint(
                f"{field} IS NULL OR ({field} >= 0 AND {field} <= 9007199254740991)",
                name=f"ck_parameter_{field}",
            )
            for field in ("text_price", "image_price", "video_price")
        ],
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_bin",
    )
    op.create_table(
        "generation_parameter_heads",
        sa.Column("mode", sa.String(16), primary_key=True),
        sa.Column("version", sa.String(36), sa.ForeignKey("generation_parameter_configs.version")),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_bin",
    )
    op.bulk_insert(
        sa.table("generation_parameter_heads", sa.column("mode", sa.String(16))),
        [{"mode": mode} for mode in ("mock", "staging", "production")],
    )
    for operation in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER generation_parameters_no_{operation.lower()} "
            f"BEFORE {operation} ON generation_parameter_configs "
            "FOR EACH ROW SIGNAL SQLSTATE '45000' "
            "SET MESSAGE_TEXT='Parameter versions are immutable'"
        )


def downgrade():
    raise RuntimeError("Price history is retained; destructive rollback requires approval")
