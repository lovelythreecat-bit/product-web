"""Typed audit boundaries admit only the intended non-secret configuration metadata."""

from datetime import UTC, datetime
from uuid import uuid4

from app.audit.models import AuditEvent


def audit_credit_config(session, actor_id, version, reason, amount, policy_version):
    session.add(
        AuditEvent(
            id=str(uuid4()),
            actor_id=str(actor_id) if actor_id else None,
            action="registration_credit_config",
            object_id=version,
            reason=reason,
            changes={"amount": amount, "policy_version": policy_version},
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
