"""Durable callback/poll receipts and fenced reduction decisions."""

from alembic import op

revision = "0012_agent_events"
down_revision = "0011_upstream_attempts"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE agent_events (
        id VARCHAR(36) PRIMARY KEY, task_id VARCHAR(36) NOT NULL,
        agent_id VARCHAR(36) NOT NULL, agent_version VARCHAR(128) NOT NULL,
        source VARCHAR(16) NOT NULL, event_id VARCHAR(128) NOT NULL,
        raw_digest VARCHAR(64) NOT NULL, semantic_digest VARCHAR(64) NOT NULL,
        sequence BIGINT NOT NULL, payload JSON NOT NULL, created_at DATETIME(6) NOT NULL,
        FOREIGN KEY (task_id) REFERENCES generation_tasks(id),
        UNIQUE KEY uq_agent_event_replay (agent_id, agent_version, source, event_id),
        INDEX ix_agent_event_task (task_id, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""CREATE TABLE agent_event_decisions (
        event_ref VARCHAR(36) PRIMARY KEY, task_id VARCHAR(36) NOT NULL,
        disposition VARCHAR(32) NOT NULL, fencing_token BIGINT NULL,
        created_at DATETIME(6) NOT NULL,
        FOREIGN KEY (event_ref) REFERENCES agent_events(id),
        FOREIGN KEY (task_id) REFERENCES generation_tasks(id),
        INDEX ix_agent_event_decisions_task_id (task_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    for table in ("agent_events", "agent_event_decisions"):
        for operation in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER {table}_no_{operation.lower()} BEFORE {operation} "
                f"ON {table} FOR EACH ROW SIGNAL SQLSTATE '45000' "
                "SET MESSAGE_TEXT='Immutable agent event provenance'"
            )


def downgrade():
    raise RuntimeError("Agent evidence requires an explicit preservation plan")
