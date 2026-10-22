"""Remove artificial storage limits while retaining byte accounting and identities."""

from alembic import op

revision = "0031_remove_storage_limits"
down_revision = "0030_prompt_assist_config"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_storage_account_capacity", "storage_accounts", type_="check")
    op.drop_constraint("ck_pool_capacity", "storage_pools", type_="check")
    op.drop_column("storage_accounts", "quota_bytes")
    op.drop_column("storage_pools", "budget_bytes")
    op.create_check_constraint(
        "ck_storage_account_capacity", "storage_accounts",
        "reserved_bytes >= 0 AND actual_bytes >= 0",
    )
    op.create_check_constraint(
        "ck_pool_capacity", "storage_pools", "reserved_bytes >= 0 AND actual_bytes >= 0",
    )


def downgrade():
    raise RuntimeError("Removed storage limits cannot be reconstructed from byte accounting")
