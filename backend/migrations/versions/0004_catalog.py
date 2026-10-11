"""Immutable catalog version history with explicit active pointers."""

import sqlalchemy as sa
from alembic import op

revision = "0004_catalog"
down_revision = "0003_auth_credit_base"
branch_labels = None
depends_on = None


def upgrade():
    for table, key in (
        ("agent_versions", "agent_id"),
        ("generation_specs", "spec_id"),
        ("price_versions", "spec_id"),
    ):
        columns = [
            sa.Column(key, sa.String(36), primary_key=True),
            sa.Column("version", sa.String(128), primary_key=True),
            sa.Column("snapshot", sa.JSON(), nullable=False),
        ]
        if table == "agent_versions":
            columns += [
                sa.Column("endpoint", sa.String(2048), nullable=False),
                sa.Column("secret_ref", sa.String(1024), nullable=True),
            ]
        if table == "generation_specs":
            columns += [
                sa.Column("agent_id", sa.String(36), nullable=False),
                sa.Column("agent_version", sa.String(128), nullable=False),
                sa.ForeignKeyConstraint(
                    ["agent_id", "agent_version"],
                    ["agent_versions.agent_id", "agent_versions.version"],
                ),
            ]
        op.create_table(
            table,
            *columns,
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_bin",
        )
        for event in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER {table}_no_{event.lower()} BEFORE {event} ON {table} "
                "FOR EACH ROW SIGNAL SQLSTATE '45000' "
                "SET MESSAGE_TEXT = 'Catalog versions are immutable'"
            )
    for table, key, versions in (
        ("agent_heads", "agent_id", "agent_versions"),
        ("spec_heads", "spec_id", "generation_specs"),
        ("price_heads", "spec_id", "price_versions"),
    ):
        op.create_table(
            table,
            sa.Column(key, sa.String(36), primary_key=True),
            sa.Column("version", sa.String(128), nullable=False),
            sa.ForeignKeyConstraint([key, "version"], [f"{versions}.{key}", f"{versions}.version"]),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_bin",
        )


def downgrade():
    for table in ("price_heads", "spec_heads", "agent_heads"):
        op.drop_table(table)
    for table in ("price_versions", "generation_specs", "agent_versions"):
        for event in ("update", "delete"):
            op.execute(f"DROP TRIGGER IF EXISTS {table}_no_{event}")
        op.drop_table(table)
