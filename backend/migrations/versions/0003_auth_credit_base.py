"""T04 accounts, sessions, atomic credits and immutable signup configuration."""

from alembic import op

revision = "0003_auth_credit_base"
down_revision = "0002_policy_versions"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
CREATE TABLE audit_events (
	id VARCHAR(36) NOT NULL, 
	actor_id VARCHAR(36), 
	action VARCHAR(64) NOT NULL, 
	object_id VARCHAR(128) NOT NULL, 
	reason VARCHAR(500) NOT NULL, 
	changes JSON NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id)
)

 ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""
CREATE TABLE registration_credit_configs (
	version VARCHAR(36) NOT NULL, 
	amount BIGINT NOT NULL, 
	mode VARCHAR(16) NOT NULL, 
	test_only BOOL NOT NULL, 
	policy_version VARCHAR(128) NOT NULL, 
	reason VARCHAR(500) NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (version), 
	CONSTRAINT ck_signup_amount CHECK (amount >= 0), 
	CONSTRAINT ck_signup_mode CHECK ((mode='mock' AND test_only=1)
        OR (mode IN ('production','staging') AND test_only=0))
)

 ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""
CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	account_normalized VARCHAR(64) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	`role` VARCHAR(16) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	auth_version BIGINT NOT NULL, 
	nickname VARCHAR(80), 
	bio VARCHAR(500), 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_user_role CHECK (role IN ('user','admin')), 
	CONSTRAINT ck_user_status CHECK (status IN ('active','disabled')), 
	CONSTRAINT ck_user_auth_version CHECK (auth_version >= 0), 
	UNIQUE (account_normalized)
)

 ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""
CREATE TABLE auth_sessions (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	csrf_hash VARCHAR(64) NOT NULL, 
	auth_version BIGINT NOT NULL, 
	expires_at DATETIME(6) NOT NULL, 
	revoked_at DATETIME(6), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	UNIQUE (token_hash)
)

 ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id)""")
    op.execute("""
CREATE TABLE credit_accounts (
	user_id VARCHAR(36) NOT NULL, 
	available BIGINT NOT NULL, 
	frozen BIGINT NOT NULL, 
	consumed BIGINT NOT NULL, 
	credited_total BIGINT NOT NULL, 
	PRIMARY KEY (user_id), 
	CONSTRAINT ck_credit_nonnegative CHECK (available >= 0 AND frozen >= 0
        AND consumed >= 0 AND credited_total >= 0), 
	CONSTRAINT ck_credit_conservation CHECK (available + frozen + consumed = credited_total), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

 ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""
CREATE TABLE credit_grants (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	kind VARCHAR(32) NOT NULL, 
	business_key VARCHAR(128) NOT NULL, 
	amount BIGINT NOT NULL, 
	reason VARCHAR(500) NOT NULL, 
	actor_id VARCHAR(36), 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_grant_business UNIQUE (kind, business_key), 
	CONSTRAINT ck_grant_amount CHECK (amount >= 0), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id)
)

 ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""
CREATE TABLE credit_reservations (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	task_id VARCHAR(36) NOT NULL, 
	amount BIGINT NOT NULL, 
	state VARCHAR(16) NOT NULL, 
	version BIGINT NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_reservation_amount CHECK (amount >= 0 AND version >= 1), 
	CONSTRAINT ck_reservation_state CHECK (state IN ('frozen','consumed','released')), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	UNIQUE (task_id)
)

 ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""
CREATE TABLE registration_credit_heads (
	mode VARCHAR(16) NOT NULL, 
	version VARCHAR(36) NOT NULL, 
	PRIMARY KEY (mode), 
	FOREIGN KEY(version) REFERENCES registration_credit_configs (version)
)

 ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""
CREATE TABLE registration_receipts (
	request_key VARCHAR(128) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	account_normalized VARCHAR(64) NOT NULL, 
	config_version VARCHAR(36) NOT NULL, 
	PRIMARY KEY (request_key), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(config_version) REFERENCES registration_credit_configs (version)
)

 ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""
CREATE TABLE credit_ledger (
	id VARCHAR(36) NOT NULL, 
	operation_key VARCHAR(200) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	grant_id VARCHAR(36), 
	reservation_id VARCHAR(36), 
	task_id VARCHAR(36), 
	kind VARCHAR(32) NOT NULL, 
	amount BIGINT NOT NULL, 
	balances_before JSON NOT NULL, 
	balances_after JSON NOT NULL, 
	reason VARCHAR(500) NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_ledger_amount CHECK (amount >= 0), 
	UNIQUE (operation_key), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(grant_id) REFERENCES credit_grants (id), 
	FOREIGN KEY(reservation_id) REFERENCES credit_reservations (id)
)

 ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin""")
    op.execute("""CREATE INDEX ix_credit_ledger_user_id ON credit_ledger (user_id)""")
    op.execute(
        """CREATE TRIGGER credit_grants_update_guard BEFORE UPDATE ON credit_grants
        FOR EACH ROW SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Immutable history'"""
    )
    op.execute(
        """CREATE TRIGGER credit_grants_delete_guard BEFORE DELETE ON credit_grants
        FOR EACH ROW SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Immutable history'"""
    )
    op.execute(
        """CREATE TRIGGER credit_ledger_update_guard BEFORE UPDATE ON credit_ledger
        FOR EACH ROW SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Immutable history'"""
    )
    op.execute(
        """CREATE TRIGGER credit_ledger_delete_guard BEFORE DELETE ON credit_ledger
        FOR EACH ROW SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Immutable history'"""
    )
    op.execute(
        """CREATE TRIGGER registration_credit_configs_update_guard BEFORE UPDATE
        ON registration_credit_configs
        FOR EACH ROW SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Immutable history'"""
    )
    op.execute(
        """CREATE TRIGGER registration_credit_configs_delete_guard BEFORE DELETE
        ON registration_credit_configs
        FOR EACH ROW SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Immutable history'"""
    )
    op.execute(
        """CREATE TRIGGER audit_events_update_guard BEFORE UPDATE ON audit_events
        FOR EACH ROW SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Immutable history'"""
    )
    op.execute(
        """CREATE TRIGGER audit_events_delete_guard BEFORE DELETE ON audit_events
        FOR EACH ROW SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Immutable history'"""
    )
    op.execute(
        """CREATE TRIGGER registration_receipts_update_guard BEFORE UPDATE ON registration_receipts
        FOR EACH ROW SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Immutable history'"""
    )
    op.execute(
        """CREATE TRIGGER registration_receipts_delete_guard BEFORE DELETE ON registration_receipts
        FOR EACH ROW SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Immutable history'"""
    )


def downgrade():
    op.drop_table("credit_ledger")
    op.drop_table("registration_receipts")
    op.drop_table("registration_credit_heads")
    op.drop_table("credit_reservations")
    op.drop_table("credit_grants")
    op.drop_table("credit_accounts")
    op.drop_table("auth_sessions")
    op.drop_table("users")
    op.drop_table("registration_credit_configs")
    op.drop_table("audit_events")
