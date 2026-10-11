"""Fixed original save identities and durable evidence (no publication/settlement)."""

from alembic import op

revision = "0013_result_persistence"
down_revision = "0012_agent_events"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE result_manifests (
        id VARCHAR(36) PRIMARY KEY, task_id VARCHAR(36) NOT NULL UNIQUE,
        receipt_id VARCHAR(36) NOT NULL UNIQUE, identity JSON NOT NULL,
        manifest JSON NOT NULL, policy_versions JSON NOT NULL, created_at DATETIME(6) NOT NULL,
        FOREIGN KEY (task_id) REFERENCES generation_tasks(id),
        FOREIGN KEY (receipt_id) REFERENCES agent_events(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""CREATE TABLE result_save_items (
        id VARCHAR(36) PRIMARY KEY, manifest_id VARCHAR(36) NOT NULL,
        item_key VARCHAR(128) NOT NULL, file_id VARCHAR(36) NOT NULL UNIQUE,
        file_version VARCHAR(36) NOT NULL, internal_path VARCHAR(255) NOT NULL UNIQUE,
        locator VARCHAR(2048) NOT NULL, media_type VARCHAR(64) NOT NULL,
        sha256 VARCHAR(64) NOT NULL, actual_bytes BIGINT NOT NULL,
        UNIQUE KEY uq_result_item (manifest_id, item_key),
        FOREIGN KEY (manifest_id) REFERENCES result_manifests(id),
        CHECK (actual_bytes > 0)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""CREATE TABLE result_deliveries (
        manifest_id VARCHAR(36) PRIMARY KEY, total_bytes BIGINT NOT NULL,
        fencing_token BIGINT NOT NULL, created_at DATETIME(6) NOT NULL,
        FOREIGN KEY (manifest_id) REFERENCES result_manifests(id),
        CHECK (total_bytes > 0 AND fencing_token > 0)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    for table in ("result_manifests", "result_save_items", "result_deliveries"):
        for operation in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER {table}_no_{operation.lower()} BEFORE {operation} "
                f"ON {table} FOR EACH ROW SIGNAL SQLSTATE '45000' "
                "SET MESSAGE_TEXT='Immutable original result evidence'"
            )


def downgrade():
    raise RuntimeError("Result recovery evidence requires an explicit preservation plan")
