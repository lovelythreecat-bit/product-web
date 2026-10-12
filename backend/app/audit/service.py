"""Typed audit boundaries admit only the intended non-secret configuration metadata."""

from datetime import UTC, datetime
from uuid import uuid4

from app.audit.models import AuditEvent


def audit_admin(session, actor_id, action, object_id, reason, changes):
    """Internal call sites supply explicit metadata, never raw DTOs or snapshots."""
    row = AuditEvent(
        id=str(uuid4()),
        actor_id=str(actor_id),
        action=action,
        object_id=str(object_id),
        reason=reason,
        changes=changes,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(row)
    return row


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


def audit_catalog(
    session,
    actor_id,
    kind,
    object_id,
    version,
    reason,
    enabled,
    *,
    secret_configured=None,
    credits=None,
):
    """Only typed publication metadata enters audit; endpoints/credential refs never do."""
    changes = {"version": version, "enabled": enabled}
    if secret_configured is not None:
        changes["secret_configured"] = secret_configured
    if credits is not None:
        changes["credits"] = credits
    session.add(
        AuditEvent(
            id=str(uuid4()),
            actor_id=str(actor_id),
            action=f"catalog_{kind}",
            object_id=str(object_id),
            reason=reason,
            changes=changes,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
