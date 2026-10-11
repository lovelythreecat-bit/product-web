"""T14 permanent sequence/dedup facts separated from pruneable SSE payloads."""

from alembic import op

revision = "0016_event_retention"
down_revision = "0015_investigations"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE event_heads (
        user_id VARCHAR(36) PRIMARY KEY, last_seq BIGINT NOT NULL,
        pruned_through BIGINT NOT NULL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id),
        CHECK (last_seq >= pruned_through AND pruned_through >= 0)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""CREATE TABLE event_receipts (
        id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL,
        task_id VARCHAR(36) NOT NULL, event_seq BIGINT NOT NULL,
        event_key VARCHAR(160) NOT NULL, event_type VARCHAR(32) NOT NULL,
        payload_digest VARCHAR(64) NOT NULL, created_at DATETIME(6) NOT NULL,
        UNIQUE KEY uq_event_receipt_intent (user_id,event_key),
        UNIQUE KEY uq_event_receipt_sequence (user_id,event_seq),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (task_id) REFERENCES generation_tasks(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""INSERT INTO event_heads(user_id,last_seq,pruned_through)
        SELECT user_id,MAX(event_seq),0 FROM durable_events GROUP BY user_id""")
    op.execute("""INSERT INTO event_receipts
        (id,user_id,task_id,event_seq,event_key,event_type,payload_digest,created_at)
        SELECT id,user_id,task_id,event_seq,event_key,event_type,
        SHA2(CONCAT(event_type,'|',task_id,'|',
            JSON_UNQUOTE(JSON_EXTRACT(payload,'$.state')),'|',
            JSON_UNQUOTE(JSON_EXTRACT(payload,'$.state_version'))),256),created_at
        FROM durable_events""")


def downgrade():
    raise RuntimeError("Event sequence and deduplication facts must be preserved")
