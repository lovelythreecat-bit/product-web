"""Persistent recovery schedule; reuse existing lease and fencing columns."""

from alembic import op

revision = "0010_task_recovery"
down_revision = "0009_tasks_admission"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE generation_tasks ADD recovery_due_at DATETIME(6) "
        "NOT NULL DEFAULT CURRENT_TIMESTAMP(6)"
    )
    op.create_index(
        "ix_task_recovery_due", "generation_tasks", ["recovery_due_at", "lease_expires_at"]
    )
    op.create_index("ix_outbox_pending", "dispatch_outbox", ["dispatched_at", "ready_at"])


def downgrade():
    raise RuntimeError("Recovery history requires an explicit preservation plan")
