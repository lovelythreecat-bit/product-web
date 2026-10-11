"""One task reservation may own multiple files, with exact account attribution."""

import sqlalchemy as sa
from alembic import op

revision = "0008_storage_many_files"
down_revision = "0007_storage_guards"
branch_labels = None
depends_on = None


def upgrade():
    mismatch = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT f.id FROM files f JOIN capacity_reservations r ON r.id=f.reservation_id "
                "WHERE f.user_id <> r.user_id LIMIT 1"
            )
        )
        .first()
    )
    if mismatch is not None:
        raise RuntimeError("Storage migration requires consistent file/reservation ownership")
    op.create_unique_constraint("uq_capacity_owner", "capacity_reservations", ["id", "user_id"])
    # Establish a nonunique supporting index before dropping the old FK's unique index.
    op.create_index("ix_files_reservation_id", "files", ["reservation_id"])
    op.drop_index("reservation_id", table_name="files")
    op.create_foreign_key(
        "fk_file_reservation_owner",
        "files",
        "capacity_reservations",
        ["reservation_id", "user_id"],
        ["id", "user_id"],
    )


def downgrade():
    duplicate = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT reservation_id FROM files GROUP BY reservation_id "
                "HAVING COUNT(*) > 1 LIMIT 1"
            )
        )
        .first()
    )
    if duplicate is not None:
        raise RuntimeError("Cannot downgrade multi-file reservations without losing history")
    op.drop_constraint("fk_file_reservation_owner", "files", type_="foreignkey")
    op.create_unique_constraint("reservation_id", "files", ["reservation_id"])
    op.drop_index("ix_files_reservation_id", table_name="files")
    op.drop_constraint("uq_capacity_owner", "capacity_reservations", type_="unique")
