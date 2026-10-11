"""T06 persistent private file identities and transactional byte reservations."""

from alembic import op

revision = "0006_storage"
down_revision = "0005_catalog_identities"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
CREATE TABLE storage_pools (
	id VARCHAR(16) NOT NULL, 
	budget_bytes BIGINT NOT NULL, 
	reserved_bytes BIGINT NOT NULL, 
	actual_bytes BIGINT NOT NULL, 
	policy_version VARCHAR(128) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_pool_capacity CHECK (budget_bytes > 0 
        AND reserved_bytes >= 0 AND actual_bytes >= 0 
        AND reserved_bytes <= budget_bytes - actual_bytes)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
""")
    op.execute("""
CREATE TABLE storage_accounts (
	user_id VARCHAR(36) NOT NULL, 
	pool_id VARCHAR(16) NOT NULL, 
	quota_bytes BIGINT NOT NULL, 
	reserved_bytes BIGINT NOT NULL, 
	actual_bytes BIGINT NOT NULL, 
	policy_version VARCHAR(128) NOT NULL, 
	PRIMARY KEY (user_id), 
	CONSTRAINT ck_storage_account_capacity CHECK (quota_bytes > 0 
        AND reserved_bytes >= 0 AND actual_bytes >= 0 
        AND reserved_bytes <= quota_bytes - actual_bytes), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(pool_id) REFERENCES storage_pools (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
""")
    op.execute("""
CREATE TABLE capacity_reservations (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	pool_id VARCHAR(16) NOT NULL, 
	intent_id VARCHAR(128) NOT NULL, 
	estimated_bytes BIGINT NOT NULL, 
	actual_bytes BIGINT NOT NULL, 
	state VARCHAR(16) NOT NULL, 
	policy_version VARCHAR(128) NOT NULL, 
	expires_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_capacity_intent UNIQUE (user_id, intent_id), 
	CONSTRAINT ck_reservation_bytes CHECK (estimated_bytes > 0 AND actual_bytes >= 0), 
	CONSTRAINT ck_capacity_state CHECK (state IN ('reserved','finalized','released')), 
	CONSTRAINT ck_capacity_actual_state CHECK (state = 'finalized' OR actual_bytes = 0), 
	FOREIGN KEY(user_id) REFERENCES storage_accounts (user_id), 
	FOREIGN KEY(pool_id) REFERENCES storage_pools (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
""")
    op.execute("""
CREATE TABLE files (
	id VARCHAR(36) NOT NULL, 
	version VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	internal_path VARCHAR(255) NOT NULL, 
	actual_mime VARCHAR(64) NOT NULL, 
	actual_bytes BIGINT NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	display_name VARCHAR(200) NOT NULL, 
	state VARCHAR(16) NOT NULL, 
	deleted_at DATETIME(6), 
	created_at DATETIME(6) NOT NULL, 
	reservation_id VARCHAR(36) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_file_version_owner UNIQUE (id, version, user_id), 
	CONSTRAINT ck_file_bytes CHECK (actual_bytes > 0), 
	CONSTRAINT ck_file_state CHECK (state IN ('durable','unavailable')), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	UNIQUE (internal_path), 
	UNIQUE (reservation_id), 
	FOREIGN KEY(reservation_id) REFERENCES capacity_reservations (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
""")
    op.execute("""
CREATE INDEX ix_files_user_id ON files (user_id)
""")
    op.execute("""
CREATE TABLE file_refs (
	id VARCHAR(36) NOT NULL, 
	file_id VARCHAR(36) NOT NULL, 
	version VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	ref_type VARCHAR(32) NOT NULL, 
	ref_id VARCHAR(36) NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_ref_file_owner_version FOREIGN KEY(file_id, version, user_id)
        REFERENCES files (id, version, user_id), 
	CONSTRAINT uq_file_reference UNIQUE (file_id, version, ref_type, ref_id), 
	CONSTRAINT ck_file_ref_type CHECK (ref_type IN ('task_input','task_result','message','work')), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
""")


def downgrade():
    op.drop_table("file_refs")
    op.drop_table("files")
    op.drop_table("capacity_reservations")
    op.drop_table("storage_accounts")
    op.drop_table("storage_pools")
