"""Transactional task admission, immutable snapshots, dispatch and durable events.

Orphan preflight fails BEFORE DDL; never invent tasks for old ledger rows.
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_tasks_admission"
down_revision = "0008_storage_many_files"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("credit_reservations", "credit_ledger"):
        if (
            op.get_bind()
            .execute(sa.text(f"SELECT task_id FROM {table} WHERE task_id IS NOT NULL LIMIT 1"))
            .first()
            is not None
        ):
            raise RuntimeError(
                "Task migration requires reconciled historical task references; "
                "original records preserved"
            )
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT id FROM file_refs WHERE ref_type IN ('task_input','task_result') LIMIT 1"
            )
        )
        .first()
        is not None
    ):
        raise RuntimeError("Task migration requires reconciled historical file task references")
    op.execute(
        "CREATE TABLE conversations (\n\tid VARCHAR(36) NOT NULL, \n\tuser_id "
        "VARCHAR(36) NOT NULL, \n\ttitle VARCHAR(200) NOT NULL, \n\tcreated_at"
        " DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_conver"
        "sation_owner UNIQUE (id, user_id), \n\tFOREIGN KEY(user_id) REFEREN"
        "CES users (id)\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=ut"
        "f8mb4_bin"
    )
    op.execute("CREATE INDEX ix_conversations_user_id ON conversations (user_id)")
    op.execute(
        "CREATE TABLE products (\n\tid VARCHAR(36) NOT NULL, \n\tuser_id VARCH"
        "AR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_product_owne"
        "r UNIQUE (id, user_id), \n\tFOREIGN KEY(user_id) REFERENCES users ("
        "id)\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin"
    )
    op.execute(
        "CREATE TABLE product_versions (\n\tversion VARCHAR(36) NOT NULL, \n\t"
        "product_id VARCHAR(36) NOT NULL, \n\tuser_id VARCHAR(36) NOT NULL, "
        "\n\tproduct JSON NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tPRI"
        "MARY KEY (version), \n\tCONSTRAINT uq_product_version UNIQUE (produ"
        "ct_id, version), \n\tCONSTRAINT uq_product_version_owner UNIQUE (ve"
        "rsion, user_id), \n\tFOREIGN KEY(product_id, user_id) REFERENCES pr"
        "oducts (id, user_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id"
        ")\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin"
    )
    op.execute(
        "CREATE TABLE generation_tasks (\n\tid VARCHAR(36) NOT NULL, \n\tuser_"
        "id VARCHAR(36) NOT NULL, \n\tconversation_id VARCHAR(36) NOT NULL, "
        "\n\tidempotency_key VARCHAR(128) COLLATE utf8mb4_bin NOT NULL, \n\tre"
        "quest_hash VARCHAR(64) NOT NULL, \n\tagent_id VARCHAR(36) NOT NULL,"
        " \n\tagent_version VARCHAR(128) NOT NULL, \n\texternal_submission_id "
        "VARCHAR(36) NOT NULL, \n\tupstream_id VARCHAR(255), \n\tstate VARCHAR"
        "(24) NOT NULL, \n\tstate_version BIGINT NOT NULL, \n\tsettlement_stat"
        "e VARCHAR(16) NOT NULL, \n\tcapacity_reservation_id VARCHAR(36) NOT"
        " NULL, \n\tlease_owner VARCHAR(128), \n\tlease_expires_at DATETIME(6)"
        ", \n\tfencing_token BIGINT NOT NULL, \n\tinvestigation_reason VARCHAR"
        "(500), \n\tcreated_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tC"
        "ONSTRAINT uq_task_owner UNIQUE (id, user_id), \n\tCONSTRAINT uq_tas"
        "k_intent UNIQUE (user_id, idempotency_key), \n\tCONSTRAINT uq_task_"
        "upstream UNIQUE (agent_id, upstream_id), \n\tFOREIGN KEY(conversati"
        "on_id, user_id) REFERENCES conversations (id, user_id), \n\tFOREIGN"
        " KEY(capacity_reservation_id, user_id) REFERENCES capacity_reserv"
        "ations (id, user_id), \n\tCONSTRAINT ck_task_versions CHECK (state_"
        "version >= 1 AND fencing_token >= 0), \n\tCONSTRAINT ck_task_state "
        "CHECK (state IN ('SUBMITTED','QUEUED','SUBMITTING','RUNNING','INV"
        "ESTIGATING','SAVING','SAVE_RECOVERY','SUCCEEDED','FAILED','MANUAL"
        "LY_CLOSED')), \n\tCONSTRAINT ck_task_settlement CHECK (settlement_s"
        "tate IN ('FROZEN','CONSUMED','RELEASED')), \n\tFOREIGN KEY(user_id)"
        " REFERENCES users (id), \n\tUNIQUE (external_submission_id), \n\tUNIQ"
        "UE (capacity_reservation_id)\n) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        "mb4 COLLATE=utf8mb4_bin"
    )
    op.execute(
        "CREATE INDEX ix_generation_tasks_conversation_id ON generation_tasks (conversation_id)"
    )
    op.execute("CREATE INDEX ix_generation_tasks_user_id ON generation_tasks (user_id)")
    op.execute(
        "CREATE TABLE task_snapshots (\n\ttask_id VARCHAR(36) NOT NULL, \n\tus"
        "er_id VARCHAR(36) NOT NULL, \n\tproduct_version VARCHAR(36) NOT NUL"
        "L, \n\tinput_snapshot JSON NOT NULL, \n\tagent_snapshot JSON NOT NULL"
        ", \n\tspec_snapshot JSON NOT NULL, \n\tprice_snapshot JSON NOT NULL, "
        "\n\tquote JSON NOT NULL, \n\tpolicy_versions JSON NOT NULL, \n\tcapacit"
        "y_estimate JSON NOT NULL, \n\tPRIMARY KEY (task_id), \n\tFOREIGN KEY("
        "task_id, user_id) REFERENCES generation_tasks (id, user_id), \n\tFO"
        "REIGN KEY(product_version, user_id) REFERENCES product_versions ("
        "version, user_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)"
        " ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin"
    )
    op.execute(
        "CREATE TABLE messages (\n\tid VARCHAR(36) NOT NULL, \n\tuser_id VARCH"
        "AR(36) NOT NULL, \n\tconversation_id VARCHAR(36) NOT NULL, \n\ttask_i"
        "d VARCHAR(36), \n\tkind VARCHAR(16) NOT NULL, \n\t`role` VARCHAR(16) "
        "NOT NULL, \n\tcontent JSON NOT NULL, \n\tcreated_at DATETIME(6) NOT N"
        "ULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(conversation_id, user_id) "
        "REFERENCES conversations (id, user_id), \n\tFOREIGN KEY(task_id, us"
        "er_id) REFERENCES generation_tasks (id, user_id), \n\tCONSTRAINT ck"
        "_message_kind CHECK (kind IN ('authored','final')), \n\tCONSTRAINT "
        "ck_message_role CHECK (role IN ('user','assistant')), \n\tFOREIGN K"
        "EY(user_id) REFERENCES users (id)\n) ENGINE=InnoDB DEFAULT CHARSET"
        "=utf8mb4 COLLATE=utf8mb4_bin"
    )
    op.execute(
        "CREATE TABLE task_state_events (\n\tid VARCHAR(36) NOT NULL, \n\ttask"
        "_id VARCHAR(36) NOT NULL, \n\tuser_id VARCHAR(36) NOT NULL, \n\tstate"
        "_version BIGINT NOT NULL, \n\tfrom_state VARCHAR(24), \n\tto_state VA"
        "RCHAR(24) NOT NULL, \n\tevidence JSON NOT NULL, \n\tcreated_at DATETI"
        "ME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_task_state_ev"
        "ent UNIQUE (task_id, state_version), \n\tFOREIGN KEY(task_id, user_"
        "id) REFERENCES generation_tasks (id, user_id), \n\tFOREIGN KEY(user"
        "_id) REFERENCES users (id)\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb"
        "4 COLLATE=utf8mb4_bin"
    )
    op.execute(
        "CREATE TABLE dispatch_outbox (\n\tevent_id VARCHAR(36) NOT NULL, \n\t"
        "user_id VARCHAR(36) NOT NULL, \n\ttask_id VARCHAR(36) NOT NULL, \n\ts"
        "tate_version BIGINT NOT NULL, \n\toperation VARCHAR(32) NOT NULL, \n"
        "\tready_at DATETIME(6) NOT NULL, \n\tattempts BIGINT NOT NULL, \n\tdis"
        "patched_at DATETIME(6), \n\tPRIMARY KEY (event_id), \n\tCONSTRAINT uq"
        "_outbox_operation UNIQUE (task_id, state_version, operation), \n\tF"
        "OREIGN KEY(task_id, user_id) REFERENCES generation_tasks (id, use"
        "r_id)\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin"
    )
    op.execute("CREATE INDEX ix_dispatch_outbox_ready_at ON dispatch_outbox (ready_at)")
    op.execute(
        "CREATE TABLE durable_events (\n\tid VARCHAR(36) NOT NULL, \n\tuser_id"
        " VARCHAR(36) NOT NULL, \n\ttask_id VARCHAR(36) NOT NULL, \n\tevent_se"
        "q BIGINT NOT NULL, \n\tevent_key VARCHAR(160) COLLATE utf8mb4_bin N"
        "OT NULL, \n\tevent_type VARCHAR(32) NOT NULL, \n\tpayload JSON NOT NU"
        "LL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONS"
        "TRAINT uq_durable_sequence UNIQUE (user_id, event_seq), \n\tCONSTRA"
        "INT uq_durable_intent UNIQUE (user_id, event_key), \n\tFOREIGN KEY("
        "task_id, user_id) REFERENCES generation_tasks (id, user_id), \n\tFO"
        "REIGN KEY(user_id) REFERENCES users (id)\n) ENGINE=InnoDB DEFAULT "
        "CHARSET=utf8mb4 COLLATE=utf8mb4_bin"
    )
    op.execute(
        "ALTER TABLE credit_reservations ADD CONSTRAINT fk_credit_reservat"
        "ion_task_owner FOREIGN KEY (task_id,user_id) REFERENCES generatio"
        "n_tasks(id,user_id)"
    )
    op.execute(
        "ALTER TABLE credit_ledger ADD CONSTRAINT fk_credit_ledger_task_ow"
        "ner FOREIGN KEY (task_id,user_id) REFERENCES generation_tasks(id,"
        "user_id)"
    )
    op.execute(
        "CREATE TRIGGER product_versions_no_update BEFORE UPDATE ON produc"
        "t_versions FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT "
        "= 'Committed content is append-only'"
    )
    op.execute(
        "CREATE TRIGGER product_versions_no_delete BEFORE DELETE ON produc"
        "t_versions FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT "
        "= 'Committed content is append-only'"
    )
    op.execute(
        "CREATE TRIGGER task_snapshots_no_update BEFORE UPDATE ON task_sna"
        "pshots FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'C"
        "ommitted content is append-only'"
    )
    op.execute(
        "CREATE TRIGGER task_snapshots_no_delete BEFORE DELETE ON task_sna"
        "pshots FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'C"
        "ommitted content is append-only'"
    )
    op.execute(
        "CREATE TRIGGER task_state_events_no_update BEFORE UPDATE ON task_"
        "state_events FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEX"
        "T = 'Committed content is append-only'"
    )
    op.execute(
        "CREATE TRIGGER task_state_events_no_delete BEFORE DELETE ON task_"
        "state_events FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEX"
        "T = 'Committed content is append-only'"
    )
    op.execute(
        "CREATE TRIGGER durable_events_no_update BEFORE UPDATE ON durable_"
        "events FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'C"
        "ommitted content is append-only'"
    )
    op.execute(
        "CREATE TRIGGER durable_events_no_delete BEFORE DELETE ON durable_"
        "events FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'C"
        "ommitted content is append-only'"
    )
    op.execute(
        "CREATE TRIGGER messages_no_update BEFORE UPDATE ON messages FOR E"
        "ACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Committed con"
        "tent is append-only'"
    )
    op.execute(
        "CREATE TRIGGER messages_no_delete BEFORE DELETE ON messages FOR E"
        "ACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Committed con"
        "tent is append-only'"
    )
    op.execute(
        "CREATE TRIGGER task_admission_immutable BEFORE UPDATE ON generati"
        "on_tasks FOR EACH ROW BEGIN IF NOT (OLD.id <=> NEW.id) OR NOT (OL"
        "D.user_id <=> NEW.user_id) OR NOT (OLD.conversation_id <=> NEW.co"
        "nversation_id) OR NOT (OLD.idempotency_key <=> NEW.idempotency_ke"
        "y) OR NOT (OLD.request_hash <=> NEW.request_hash) OR NOT (OLD.age"
        "nt_id <=> NEW.agent_id) OR NOT (OLD.agent_version <=> NEW.agent_v"
        "ersion) OR NOT (OLD.external_submission_id <=> NEW.external_submi"
        "ssion_id) OR NOT (OLD.capacity_reservation_id <=> NEW.capacity_re"
        "servation_id) OR NOT (OLD.created_at <=> NEW.created_at) THEN SIG"
        "NAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Task admission identity "
        "is immutable'; END IF; END"
    )
    op.execute(
        "CREATE TRIGGER file_ref_task_owner_insert BEFORE INSERT ON file_r"
        "efs FOR EACH ROW BEGIN IF NEW.ref_type IN ('task_input','task_res"
        "ult') AND NOT EXISTS (SELECT 1 FROM generation_tasks WHERE id=NEW"
        ".ref_id AND user_id=NEW.user_id) THEN SIGNAL SQLSTATE '45000' SET"
        " MESSAGE_TEXT = 'Task reference owner mismatch'; END IF; END"
    )
    op.execute(
        "CREATE TRIGGER file_ref_task_owner_update BEFORE UPDATE ON file_r"
        "efs FOR EACH ROW BEGIN IF NEW.ref_type IN ('task_input','task_res"
        "ult') AND NOT EXISTS (SELECT 1 FROM generation_tasks WHERE id=NEW"
        ".ref_id AND user_id=NEW.user_id) THEN SIGNAL SQLSTATE '45000' SET"
        " MESSAGE_TEXT = 'Task reference owner mismatch'; END IF; END"
    )


def downgrade():
    raise RuntimeError(
        "Task admission history requires an explicit preservation plan; downgrade is disabled"
    )
