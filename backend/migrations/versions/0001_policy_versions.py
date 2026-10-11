"""Immutable policy content versions and one-way confirmation on MySQL 8.4."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME

revision = "0002_policy_versions"
down_revision = "0001_bootstrap"
branch_labels = None
depends_on = None


def upgrade():
    # Keep migration definitions independent of application model changes.
    op.create_table(
        "decision_versions",
        sa.Column("decision_id", sa.String(4), primary_key=True),
        sa.Column("version", sa.String(128), primary_key=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("test_only", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("confirmed_by", sa.String(36), nullable=True),
        sa.Column("confirmed_at", DATETIME(fsp=6), nullable=True),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "decision_id IN ('D-01','D-02','D-03','D-04','D-05','D-06',"
            "'D-07','D-08','D-09','D-10','D-11','D-12')",
            name="ck_decision_id",
        ),
        sa.CheckConstraint("CHAR_LENGTH(TRIM(version)) > 0", name="ck_policy_version"),
        sa.CheckConstraint("mode IN ('mock', 'staging', 'production')", name="ck_policy_mode"),
        sa.CheckConstraint("status IN ('draft', 'confirmed')", name="ck_policy_status"),
        sa.CheckConstraint(
            "(mode = 'mock' AND test_only = 1) OR "
            "(mode IN ('staging', 'production') AND test_only = 0)",
            name="ck_policy_test_only",
        ),
        sa.CheckConstraint("JSON_TYPE(payload) = 'OBJECT'", name="ck_policy_payload"),
        sa.CheckConstraint("JSON_TYPE(evidence_refs) = 'ARRAY'", name="ck_policy_evidence"),
        sa.CheckConstraint(
            "(status = 'draft' AND confirmed_by IS NULL AND confirmed_at IS NULL "
            "AND JSON_LENGTH(evidence_refs) = 0) OR "
            "(status = 'confirmed' AND confirmed_by IS NOT NULL "
            "AND CHAR_LENGTH(TRIM(confirmed_by)) = 36 AND confirmed_at IS NOT NULL "
            "AND JSON_LENGTH(evidence_refs) > 0)",
            name="ck_policy_confirmation",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_bin",
    )
    op.execute("""CREATE TRIGGER policy_version_immutable BEFORE UPDATE ON decision_versions
        FOR EACH ROW BEGIN
            IF OLD.status <> 'draft' OR NEW.status <> 'confirmed'
               OR NOT (NEW.decision_id <=> OLD.decision_id)
               OR NOT (NEW.version <=> OLD.version)
               OR NOT (NEW.mode <=> OLD.mode)
               OR NOT (NEW.test_only <=> OLD.test_only)
               OR NOT (NEW.payload <=> OLD.payload) THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Policy versions are immutable';
            END IF;
        END""")
    op.execute("""CREATE TRIGGER policy_version_no_delete BEFORE DELETE ON decision_versions
        FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Policy history cannot be deleted'
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS policy_version_no_delete")
    op.execute("DROP TRIGGER IF EXISTS policy_version_immutable")
    op.drop_table("decision_versions")
