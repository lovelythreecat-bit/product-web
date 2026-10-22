"""Permanent readable conversation/task numbers and transactional daily counters.

Run with application writers stopped, as with other MySQL DDL migrations. Historical
numbers follow creation time and UUID as a deterministic tie breaker. No UUID,
foreign key, task snapshot, idempotency key or owner identity is replaced.
"""

from datetime import timedelta

import sqlalchemy as sa
from alembic import op

revision = "0029_readable_numbers"
down_revision = "0028_media_execution"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "display_number_counters",
        sa.Column("kind", sa.String(1), primary_key=True),
        sa.Column("day", sa.String(8), primary_key=True),
        sa.Column("last_value", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("kind IN ('H','T')", name="ck_display_number_kind"),
        sa.CheckConstraint("`last_value` > 0", name="ck_display_number_positive"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin",
    )
    connection = op.get_bind()
    counters = []
    for name, kind in (("conversations", "H"), ("generation_tasks", "T")):
        op.add_column(name, sa.Column("display_number", sa.String(32), nullable=True))
        table = sa.table(
            name, sa.column("id", sa.String(36)), sa.column("created_at", sa.DateTime()),
            sa.column("display_number", sa.String(32)),
        )
        counts = {}
        rows = connection.execute(
            sa.select(table.c.id, table.c.created_at).order_by(table.c.created_at, table.c.id)
        ).mappings()
        for row in rows:
            # DATETIME values in this application are UTC without timezone metadata.
            day = (row["created_at"] + timedelta(hours=8)).strftime("%Y%m%d")
            counts[day] = counts.get(day, 0) + 1
            connection.execute(
                table.update().where(table.c.id == row["id"]).values(
                    display_number=f"{kind}{day}-{counts[day]:06d}",
                )
            )
        counters.extend(
            {"kind": kind, "day": day, "last_value": value} for day, value in counts.items()
        )
        op.alter_column(name, "display_number", existing_type=sa.String(32), nullable=False)
        op.create_unique_constraint(f"uq_{name}_display_number", name, ["display_number"])
        op.execute(
            f"CREATE TRIGGER {name}_display_number_immutable BEFORE UPDATE ON {name} "
            "FOR EACH ROW BEGIN IF NOT (OLD.display_number <=> NEW.display_number) THEN "
            "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Display number is immutable'; "
            "END IF; END"
        )
    if counters:
        op.bulk_insert(sa.table(
            "display_number_counters", sa.column("kind", sa.String(1)),
            sa.column("day", sa.String(8)), sa.column("last_value", sa.BigInteger()),
        ), counters)


def downgrade():
    raise RuntimeError("Public numbers must remain stable; destructive rollback needs approval")
