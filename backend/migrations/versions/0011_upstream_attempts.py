"""Append-only upstream attempts and provenance, after T08 recovery schedule."""

from alembic import op

revision = "0011_upstream_attempts"
down_revision = "0010_task_recovery"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE upstream_attempts (
        id VARCHAR(36) PRIMARY KEY, task_id VARCHAR(36) NOT NULL,
        agent_id VARCHAR(36) NOT NULL, agent_version VARCHAR(128) NOT NULL,
        wire_agent_id VARCHAR(24) NOT NULL, protocol_version VARCHAR(128) NOT NULL,
        external_submission_id VARCHAR(36) NOT NULL, endpoint_digest VARCHAR(64) NOT NULL,
        snapshot_digest VARCHAR(64) NOT NULL, snapshot JSON NOT NULL, scope JSON NOT NULL,
        fencing_token BIGINT NOT NULL, retry_reference VARCHAR(36) NULL,
        created_at DATETIME(6) NOT NULL,
        FOREIGN KEY (task_id) REFERENCES generation_tasks(id),
        INDEX ix_upstream_attempt_task (task_id, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""CREATE TABLE upstream_evidence (
        id VARCHAR(36) PRIMARY KEY, task_id VARCHAR(36) NOT NULL,
        attempt_id VARCHAR(36) NULL, kind VARCHAR(32) NOT NULL, payload JSON NOT NULL,
        created_at DATETIME(6) NOT NULL,
        FOREIGN KEY (task_id) REFERENCES generation_tasks(id),
        FOREIGN KEY (attempt_id) REFERENCES upstream_attempts(id),
        INDEX ix_upstream_evidence_task (task_id, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    for table in ("upstream_attempts", "upstream_evidence"):
        for operation in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER {table}_no_{operation.lower()} BEFORE {operation} "
                f"ON {table} FOR EACH ROW SIGNAL SQLSTATE '45000' "
                "SET MESSAGE_TEXT='Immutable upstream provenance'"
            )


def downgrade():
    raise RuntimeError("Upstream evidence requires an explicit preservation plan")
