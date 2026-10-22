"""Nullable shop/contact fields and a private, owner-bound current avatar."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0022_user_profile_avatar"
down_revision = "0021_site_content"
branch_labels = None
depends_on = None


def upgrade():
    for name, length in (
        ("shop_name", 80), ("category", 80), ("email", 120), ("phone", 40),
        ("avatar_file_id", 36), ("avatar_file_version", 36),
    ):
        op.add_column("users", sa.Column(name, sa.String(length), nullable=True))
    op.add_column("users", sa.Column("last_login_at", mysql.DATETIME(fsp=6), nullable=True))
    op.create_check_constraint(
        "ck_user_avatar_identity", "users",
        "(avatar_file_id IS NULL AND avatar_file_version IS NULL) OR "
        "(avatar_file_id IS NOT NULL AND avatar_file_version IS NOT NULL)",
    )
    # Both tables already exist. No table recreation, column shortening or
    # historical profile/login backfill is performed.
    op.create_foreign_key(
        "fk_user_avatar_owner_version", "users", "files",
        ["avatar_file_id", "avatar_file_version", "id"], ["id", "version", "user_id"],
    )
    op.drop_constraint("ck_file_ref_type", "file_refs", type_="check")
    op.create_check_constraint(
        "ck_file_ref_type", "file_refs",
        "ref_type IN ('task_input','task_result','message','work','avatar')",
    )


def downgrade():
    raise RuntimeError(
        "Profile/avatar data is retained; destructive rollback needs explicit approval"
    )
