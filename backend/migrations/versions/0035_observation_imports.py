"""Append-only observation dispositions and bounded conflict lookup."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME

revision = "0035_observation_imports"
down_revision = "0034_dispatch_generations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "observation_imports",
        sa.Column("source_ref", sa.String(36), sa.ForeignKey("upstream_evidence.id"),
                  primary_key=True),
        sa.Column("context_digest", sa.String(64), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("generation_tasks.id"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("rule_version", sa.String(64), nullable=False),
        sa.Column("disposition", sa.String(32), nullable=False),
        sa.Column("event_ref", sa.String(36), sa.ForeignKey("agent_events.id")),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin",
    )
    op.create_index("ix_observation_import_variant", "observation_imports",
                    ["task_id", "context_digest", "fingerprint"])
    # After source replay is fixed, avoid scanning historic conflict storms for
    # the small set of observations or the existence of a blocking conflict.
    op.create_index("ix_upstream_evidence_task_kind_time", "upstream_evidence",
                    ["task_id", "kind", "created_at"])
    for operation in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER observation_imports_no_{operation.lower()} "
            f"BEFORE {operation} ON observation_imports FOR EACH ROW "
            "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Immutable observation disposition'"
        )


def downgrade():
    raise RuntimeError("Observation dispositions require an explicit preservation plan")
