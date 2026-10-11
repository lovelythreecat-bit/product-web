"""Fenced state CAS and event writers in the caller's transaction.

Lock order: caller must acquire user/credit/capacity before task/reservation.
This function acquires user then task; callers must not enter holding task only.
Verifiers are trusted server-side integrations, never request body callables.
"""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, text, update

from app.auth.models import User
from app.dispatch.consumer import Lease, lease_matches
from app.dispatch.outbox import enqueue_outbox
from app.dispatch.recovery import TERMINAL_STATES, database_now
from app.events.service import append_durable_event
from app.ledger.models import CreditReservation
from app.tasks.models import GenerationTask, TaskStateEvent


class TransitionError(Exception):
    pass


@dataclass(frozen=True)
class TransitionEvidence:
    lease: Lease
    reference: str | None = None


@dataclass(frozen=True)
class SafeRetryEvidence:
    protocol_version: str
    kind: str
    reference: str
    verified_by: str
    verified_at: datetime


@dataclass(frozen=True)
class VerifiedTransition:
    """Verifier loads durable source by reference and binds all identity fields.

    safe_retry additionally requires a confirmed protocol_version. publication
    must validate complete durable files/text and atomic message/work publication.
    A bare bool or upstream success notification is never a publication proof.
    """

    task_id: str
    agent_id: str
    agent_version: str
    external_submission_id: str
    kind: str
    reference: str
    protocol_version: str
    upstream_id: str | None = None
    safe_retry: SafeRetryEvidence | None = None


EvidenceVerifier = Callable[[object, GenerationTask, str, str], VerifiedTransition]


class TransitionVerifiers:
    """Install on session.info['transition_verifiers'] from trusted composition code.

    Validator(session, locked_task, target_state, reference) must re-read durable
    proof in THIS transaction; no external I/O or resource locks preceding user.
    Missing kinds fail closed. T09: accepted/safe_retry; T10: original_result/
    definite_failure; T11: original_save; T12: publication; T13: manual_close.
    """

    def __init__(self, validators: Mapping[str, EvidenceVerifier]):
        self._validators = dict(validators)

    def verify(self, session, task, target, kind, reference):
        validator = self._validators.get(kind)
        if (
            validator is None
            or not reference
            or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", reference)
        ):
            raise TransitionError("EVIDENCE_REQUIRED")
        proof = validator(session, task, target, reference)
        if not isinstance(proof, VerifiedTransition) or (
            proof.task_id,
            proof.agent_id,
            proof.agent_version,
            proof.external_submission_id,
            proof.kind,
            proof.reference,
        ) != (
            task.id,
            task.agent_id,
            task.agent_version,
            task.external_submission_id,
            kind,
            reference,
        ):
            raise TransitionError("EVIDENCE_MISMATCH")
        if not proof.protocol_version:
            raise TransitionError("EVIDENCE_REQUIRED")
        if kind == "safe_retry":
            if proof.upstream_id:
                raise TransitionError("QUERY_ORIGINAL_REQUIRED")
            retry = proof.safe_retry
            if (
                not isinstance(retry, SafeRetryEvidence)
                or retry.kind not in {"reliable_idempotency", "proven_not_accepted"}
                or (retry.protocol_version, retry.reference)
                != (proof.protocol_version, proof.reference)
                or not isinstance(retry.verified_by, str)
                or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", retry.verified_by)
                or not isinstance(retry.verified_at, datetime)
            ):
                raise TransitionError("EVIDENCE_REQUIRED")
            verified_at = retry.verified_at
            if verified_at.tzinfo is not None:
                verified_at = verified_at.astimezone(UTC).replace(tzinfo=None)
            if verified_at > database_now(session):
                raise TransitionError("EVIDENCE_REQUIRED")
        if task.upstream_id and proof.upstream_id != task.upstream_id:
            raise TransitionError("UPSTREAM_IDENTITY_CONFLICT")
        return proof


@dataclass(frozen=True)
class TransitionReceipt:
    task_id: str
    state: str
    state_version: int
    changed: bool


ALLOWED = {
    "SUBMITTED": {"QUEUED", "SUBMITTING", "FAILED"},
    "QUEUED": {"QUEUED", "SUBMITTING", "FAILED"},
    "SUBMITTING": {"RUNNING", "SAVING", "INVESTIGATING", "FAILED"},
    "RUNNING": {"SAVING", "INVESTIGATING", "FAILED"},
    "INVESTIGATING": {"RUNNING", "SAVING", "SUBMITTING", "QUEUED", "FAILED", "MANUALLY_CLOSED"},
    "SAVING": {"SUCCEEDED", "SAVE_RECOVERY"},
    "SAVE_RECOVERY": {"SAVING", "INVESTIGATING", "MANUALLY_CLOSED"},
}


def required_proof(source, target):
    if target == "SUCCEEDED":
        return "publication"
    if target == "FAILED":
        return "definite_failure"
    if target == "MANUALLY_CLOSED":
        return "manual_close"
    if source == "INVESTIGATING" and target in {"SUBMITTING", "QUEUED"}:
        return "safe_retry"
    if target == "RUNNING":
        return "accepted"
    if target == "SAVING":
        return "original_save" if source == "SAVE_RECOVERY" else "original_result"
    return None


def transition_task(session, task_id, expected_version, event, evidence):
    if not isinstance(evidence, TransitionEvidence):
        raise TransitionError("EVIDENCE_REQUIRED")
    task_id = str(task_id)
    user_id = session.scalar(select(GenerationTask.user_id).where(GenerationTask.id == task_id))
    if user_id is None:
        raise TransitionError("TASK_NOT_FOUND")
    session.scalar(select(User).where(User.id == user_id).with_for_update())
    task = session.scalar(
        select(GenerationTask)
        .where(GenerationTask.id == task_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    current = database_now(session)
    if not lease_matches(task, evidence.lease, current):
        raise TransitionError("LEASE_LOST")
    if task.state_version != expected_version:
        raise TransitionError("VERSION_CONFLICT")
    source = task.state
    if source in TERMINAL_STATES or event not in ALLOWED.get(source, set()):
        raise TransitionError("INVALID_TRANSITION")
    if event in {"QUEUED", "SUBMITTING"} and task.upstream_id:
        raise TransitionError("QUERY_ORIGINAL_REQUIRED")
    proof_kind = required_proof(source, event)
    proof = None
    if proof_kind:
        registry = session.info.get("transition_verifiers")
        if not isinstance(registry, TransitionVerifiers):
            raise TransitionError("EVIDENCE_REQUIRED")
        proof = registry.verify(session, task, event, proof_kind, evidence.reference)
    if event in TERMINAL_STATES:
        reservation = session.scalar(
            select(CreditReservation).where(CreditReservation.task_id == task.id).with_for_update()
        )
        expected_settlement = "CONSUMED" if event == "SUCCEEDED" else "RELEASED"
        if (
            task.settlement_state != expected_settlement
            or reservation is None
            or reservation.state != expected_settlement.lower()
        ):
            raise TransitionError("SETTLEMENT_REQUIRED")
    if source == event:
        return TransitionReceipt(task.id, source, task.state_version, False)
    values = {"state": event, "state_version": expected_version + 1, "recovery_due_at": current}
    if proof is not None and proof.upstream_id is not None:
        values["upstream_id"] = proof.upstream_id
    lease = evidence.lease
    changed = session.execute(
        update(GenerationTask)
        .where(
            GenerationTask.id == task_id,
            GenerationTask.state_version == expected_version,
            GenerationTask.lease_owner == lease.worker_id,
            GenerationTask.fencing_token == lease.fencing_token,
            GenerationTask.lease_expires_at > text("UTC_TIMESTAMP(6)"),
        )
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    if changed.rowcount != 1:
        raise TransitionError("LEASE_LOST")
    session.refresh(task)
    session.add(
        TaskStateEvent(
            id=str(uuid4()),
            task_id=task.id,
            user_id=task.user_id,
            state_version=task.state_version,
            from_state=source,
            to_state=event,
            evidence={
                "kind": proof_kind or "stage",
                "reference": proof.reference if proof else None,
                "fencing_token": lease.fencing_token,
                "protocol_version": proof.protocol_version if proof else None,
                "retry_basis": proof.safe_retry.kind if proof and proof.safe_retry else None,
                "verified_by": proof.safe_retry.verified_by if proof and proof.safe_retry else None,
                "verified_at": (
                    proof.safe_retry.verified_at.isoformat() if proof and proof.safe_retry else None
                ),
            },
            created_at=current,
        )
    )
    append_durable_event(
        session,
        task.user_id,
        "task.updated",
        {"task_id": task.id, "state": task.state, "state_version": task.state_version},
        event_key=f"task:{task.id}:state:{task.state_version}",
    )
    if event in TERMINAL_STATES:
        from app.investigations.service import complete_from_task

        complete_from_task(session, task, evidence)
    if event not in TERMINAL_STATES:
        enqueue_outbox(
            session, task.id, "save" if event in {"SAVING", "SAVE_RECOVERY"} else "recover"
        )
    session.flush()
    return TransitionReceipt(task.id, task.state, task.state_version, True)
