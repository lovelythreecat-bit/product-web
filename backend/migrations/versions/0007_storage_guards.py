"""Protect committed content identity while permitting explicit lifecycle state changes."""

from alembic import op

revision = "0007_storage_guards"
down_revision = "0006_storage"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
CREATE TRIGGER files_identity_immutable BEFORE UPDATE ON files FOR EACH ROW
BEGIN
 IF NOT (OLD.id <=> NEW.id) OR NOT (OLD.version <=> NEW.version)
 OR NOT (OLD.user_id <=> NEW.user_id) OR NOT (OLD.internal_path <=> NEW.internal_path)
 OR NOT (OLD.actual_mime <=> NEW.actual_mime) OR NOT (OLD.actual_bytes <=> NEW.actual_bytes)
 OR NOT (OLD.sha256 <=> NEW.sha256) OR NOT (OLD.created_at <=> NEW.created_at)
 OR NOT (OLD.reservation_id <=> NEW.reservation_id) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'File content identity is immutable';
 END IF;
END
""")
    op.create_unique_constraint(
        "uq_storage_account_pool", "storage_accounts", ["user_id", "pool_id"]
    )
    op.create_foreign_key(
        "fk_capacity_account_pool",
        "capacity_reservations",
        "storage_accounts",
        ["user_id", "pool_id"],
        ["user_id", "pool_id"],
    )


def downgrade():
    op.drop_constraint("fk_capacity_account_pool", "capacity_reservations", type_="foreignkey")
    op.drop_constraint("uq_storage_account_pool", "storage_accounts", type_="unique")
    op.execute("DROP TRIGGER IF EXISTS files_identity_immutable")
