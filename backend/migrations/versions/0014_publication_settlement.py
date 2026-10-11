"""Atomic publication relationships and final-message uniqueness."""

from alembic import op

revision = "0014_publication_settlement"
down_revision = "0013_result_persistence"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""ALTER TABLE messages ADD final_task_id VARCHAR(36)
        GENERATED ALWAYS AS (CASE WHEN kind='final' THEN task_id ELSE NULL END) STORED,
        ADD CONSTRAINT uq_message_final_task UNIQUE (final_task_id),
        ADD CONSTRAINT ck_final_task CHECK
        (kind <> 'final' OR (task_id IS NOT NULL AND role='assistant'))""")
    op.execute("""CREATE TABLE works (
      id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL,
      task_id VARCHAR(36) NOT NULL UNIQUE, conversation_id VARCHAR(36) NOT NULL,
      manifest_id VARCHAR(36) NOT NULL UNIQUE, message_id VARCHAR(36) NOT NULL UNIQUE,
      created_at DATETIME(6) NOT NULL, UNIQUE KEY uq_work_owner (id,user_id),
      FOREIGN KEY (user_id) REFERENCES users(id),
      FOREIGN KEY (task_id,user_id) REFERENCES generation_tasks(id,user_id),
      FOREIGN KEY (conversation_id,user_id) REFERENCES conversations(id,user_id),
      FOREIGN KEY (manifest_id) REFERENCES result_manifests(id),
      FOREIGN KEY (message_id) REFERENCES messages(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""CREATE TABLE work_items (
      id VARCHAR(36) PRIMARY KEY, work_id VARCHAR(36) NOT NULL, user_id VARCHAR(36) NOT NULL,
      item_key VARCHAR(128) NOT NULL, file_id VARCHAR(36) NOT NULL UNIQUE,
      file_version VARCHAR(36) NOT NULL, UNIQUE KEY uq_work_item (work_id,item_key),
      FOREIGN KEY (user_id) REFERENCES users(id),
      FOREIGN KEY (work_id,user_id) REFERENCES works(id,user_id),
      FOREIGN KEY (file_id,file_version,user_id) REFERENCES files(id,version,user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")


def downgrade():
    raise RuntimeError("Publication and settlement records require an explicit preservation plan")
