"""Permit pruning transport payloads only after permanent sequence/receipt protection."""

from alembic import op

revision = "0017_event_payload_retention"
down_revision = "0016_event_retention"
branch_labels = None
depends_on = None


def upgrade():
    for operation in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER event_receipts_no_{operation.lower()} BEFORE {operation} "
            "ON event_receipts FOR EACH ROW SIGNAL SQLSTATE '45000' "
            "SET MESSAGE_TEXT='Event deduplication receipts are immutable'"
        )
    op.execute("""CREATE TRIGGER event_heads_no_delete BEFORE DELETE ON event_heads
        FOR EACH ROW SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT='Event sequence head must be retained'""")
    op.execute("""CREATE TRIGGER event_heads_monotonic BEFORE UPDATE ON event_heads
        FOR EACH ROW BEGIN
        IF NEW.last_seq < OLD.last_seq OR NEW.pruned_through < OLD.pruned_through THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Event sequence cannot rewind';
        END IF; END""")
    op.execute("DROP TRIGGER durable_events_no_delete")
    op.execute("""CREATE TRIGGER durable_events_no_delete BEFORE DELETE ON durable_events
        FOR EACH ROW BEGIN
        IF NOT EXISTS (SELECT 1 FROM event_receipts r JOIN event_heads h ON h.user_id=r.user_id
            WHERE r.id=OLD.id AND r.user_id=OLD.user_id AND r.event_seq=OLD.event_seq
            AND h.pruned_through >= OLD.event_seq) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Event retention facts required';
        END IF; END""")


def downgrade():
    raise RuntimeError("Event retention protections must be preserved")
