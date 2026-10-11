"""T13 additive investigation responsibility and evidence. No policy is confirmed here."""

from alembic import op

revision = "0015_investigations"
down_revision = "0014_publication_settlement"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE investigations (
        task_id VARCHAR(36) PRIMARY KEY, owner VARCHAR(36), policy_version VARCHAR(128) NOT NULL,
        evidence VARCHAR(128) NOT NULL, status VARCHAR(24) NOT NULL, version BIGINT NOT NULL,
        deadline_at DATETIME(6) NOT NULL, created_at DATETIME(6) NOT NULL,
        user_reason VARCHAR(500), INDEX ix_investigation_due (status,deadline_at),
        FOREIGN KEY (task_id) REFERENCES generation_tasks(id),
        FOREIGN KEY (owner) REFERENCES users(id), CHECK (version > 0)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""CREATE TABLE investigation_resolutions (
        id VARCHAR(36) PRIMARY KEY, task_id VARCHAR(36) NOT NULL, actor_id VARCHAR(36) NOT NULL,
        session_id VARCHAR(36) NOT NULL, action VARCHAR(32) NOT NULL,
        policy_version VARCHAR(128) NOT NULL, evidence JSON NOT NULL, reason VARCHAR(500) NOT NULL,
        before_version BIGINT NOT NULL, after_version BIGINT NOT NULL, task_version BIGINT NOT NULL,
        outcome VARCHAR(32) NOT NULL, created_at DATETIME(6) NOT NULL,
        UNIQUE KEY uq_resolution_version (task_id,before_version),
        INDEX ix_investigation_resolutions_task_id (task_id),
        FOREIGN KEY (task_id) REFERENCES investigations(task_id),
        FOREIGN KEY (actor_id) REFERENCES users(id),
        FOREIGN KEY (session_id) REFERENCES auth_sessions(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""CREATE TABLE investigation_alerts (
        `key` VARCHAR(180) PRIMARY KEY, task_id VARCHAR(36) NOT NULL,
        kind VARCHAR(32) NOT NULL, escalation_ref VARCHAR(128) NOT NULL,
        evidence_ref VARCHAR(128), disposition VARCHAR(32) NOT NULL,
        created_at DATETIME(6) NOT NULL, INDEX ix_investigation_alerts_task_id (task_id),
        FOREIGN KEY (task_id) REFERENCES generation_tasks(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")


def downgrade():
    raise RuntimeError("Investigation evidence requires an explicit preservation plan")
