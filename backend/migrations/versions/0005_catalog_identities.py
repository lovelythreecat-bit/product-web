"""Stable spec identity separates discovery locks from version insertion ranges."""

import sqlalchemy as sa
from alembic import op

revision = "0005_catalog_identities"
down_revision = "0004_catalog"
branch_labels = None
depends_on = None


def upgrade():
    # Refuse ambiguous legacy ownership before any DDL. No history is rewritten.
    conflicts = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT spec_id FROM generation_specs GROUP BY spec_id "
                "HAVING COUNT(DISTINCT agent_id) <> 1 LIMIT 1"
            )
        )
        .first()
    )
    if conflicts is not None:
        raise RuntimeError("Catalog identity migration requires consistent historical ownership")
    op.create_table(
        "spec_identities",
        sa.Column("spec_id", sa.String(36), primary_key=True),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.UniqueConstraint("spec_id", "agent_id", name="uq_spec_identity_owner"),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_heads.agent_id"], name="fk_identity_agent"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_bin",
    )
    op.execute(
        "INSERT INTO spec_identities(spec_id,agent_id) "
        "SELECT DISTINCT spec_id,agent_id FROM generation_specs"
    )
    op.create_foreign_key(
        "fk_spec_identity",
        "generation_specs",
        "spec_identities",
        ["spec_id", "agent_id"],
        ["spec_id", "agent_id"],
    )
    op.create_foreign_key(
        "fk_price_identity", "price_versions", "spec_identities", ["spec_id"], ["spec_id"]
    )
    for event in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER spec_identities_no_{event.lower()} BEFORE {event} "
            "ON spec_identities FOR EACH ROW SIGNAL SQLSTATE '45000' "
            "SET MESSAGE_TEXT = 'Catalog identities are immutable'"
        )


def downgrade():
    op.drop_constraint("fk_price_identity", "price_versions", type_="foreignkey")
    op.drop_constraint("fk_spec_identity", "generation_specs", type_="foreignkey")
    for event in ("update", "delete"):
        op.execute(f"DROP TRIGGER IF EXISTS spec_identities_no_{event}")
    op.drop_table("spec_identities")
