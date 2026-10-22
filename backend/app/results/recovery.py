"""Explicit repair of text results rejected by the former empty-parameters rule.

Re-read the bound upstream record, retain the old decision, and append a newly
validated receipt. This operation never submits a generation or settles credits.
"""

from uuid import uuid4

from sqlalchemy import select

from app.agents.callbacks import CallbackService
from app.agents.contracts import VerifiedEvent
from app.agents.models import AgentEvent, AgentEventDecision
from app.agents.text import PROTOCOL
from app.catalog.schemas import content_digest
from app.tasks.models import TaskSnapshot
from app.tasks.repository import locked_execution
from app.tasks.state_machine import TransitionError

REVALIDATION_RULE_VERSION = "writing-policy-v1"


def compatible_text_manifest(original, current):
    """Explicit compatibility only: unchanged artifacts and append-only warnings."""
    return (
        current.model_dump(exclude={"warnings"}) == original.model_dump(exclude={"warnings"})
        and current.warnings[:len(original.warnings)] == original.warnings
    )


def recover_text_result(upstream, task_id):
    """Recover one explicitly selected original result under a fenced lease."""
    view = upstream._view(task_id)
    if view.state in {"SUCCEEDED", "SAVING", "SAVE_RECOVERY"}:
        return view
    lease = upstream.leases.claim_task(task_id, "text-result-recovery:" + uuid4().hex)
    if lease is None:
        raise TransitionError("LEASE_UNAVAILABLE")
    callbacks = CallbackService(upstream)
    try:
        with upstream.factory() as session, session.begin():
            task = locked_execution(session, task_id, lease)
            binding = upstream.registry.bind_task(session, task)
            snapshot = session.get(TaskSnapshot, task_id)
            if (
                not (task.state == "RUNNING" or (
                    task.state == "INVESTIGATING"
                    and task.investigation_reason == "CALLBACK_EVENT_CONFLICT"
                ))
                or binding.protocol_version != PROTOCOL
                or not task.upstream_id
                or not snapshot.input_snapshot.get("parameters")
                or "platform-pricing" not in snapshot.quote.get("policy_versions", {})
            ):
                raise TransitionError("TEXT_RESULT_RECOVERY_UNAVAILABLE")
            rejected = session.scalar(select(AgentEvent).join(AgentEventDecision).where(
                AgentEvent.task_id == task_id,
                AgentEvent.source == "poll",
                AgentEvent.sequence == 2,
                AgentEvent.event_id == f"{task.upstream_id}:2",
                AgentEventDecision.disposition == "CONFLICT",
            ).order_by(AgentEvent.created_at.desc(), AgentEvent.id.desc()).limit(1))
            if rejected is None or rejected.payload["identity"] != upstream._identity(
                session, task, binding,
            ):
                raise TransitionError("EVIDENCE_MISMATCH")
            old = VerifiedEvent.model_validate(rejected.payload["event"])
            if (old.state != "RESULT_READY" or old.result is None
                    or old.upstream_task_id != task.upstream_id
                    or old.agent_id != binding.wire_agent_id
                    or old.protocol_version != binding.protocol_version
                    or old.external_submission_id != task.external_submission_id
                    or old.test_only != binding.adapter.test_only):
                raise TransitionError("EVIDENCE_MISMATCH")
            original_id = task.upstream_id
            event_id = f"{original_id}:2:{REVALIDATION_RULE_VERSION}"
            external = task.external_submission_id
            identity = upstream._identity(session, task, binding)
            attempt = upstream._latest(session, task_id)
            if attempt is None:
                raise TransitionError("EVIDENCE_MISMATCH")
            attempt_id = attempt.id
            prior = session.scalar(select(AgentEvent).where(
                AgentEvent.task_id == task_id, AgentEvent.source == "poll",
                AgentEvent.event_id == event_id,
            ))
            if prior is not None:
                # A worker may stop after committing the revalidation receipt.
                # Resume that exact proof; querying again could add warnings and
                # turn a valid pending receipt into a changed-body replay.
                _, event, binding = callbacks._event(session, task, prior.id)
                if (event.state != "RESULT_READY" or event.result is None
                        or not compatible_text_manifest(old.result, event.result)):
                    raise TransitionError("RESULT_MANIFEST_MISMATCH")
                callbacks._manifest(session, task, event, binding)
        if prior is not None:
            callbacks.reduce_pending(task_id, lease)
            view = upstream._view(task_id)
            if view.state != "SAVING":
                raise TransitionError("TEXT_RESULT_RECOVERY_UNAVAILABLE")
            return view

        outcome = upstream._leased_transport(binding.adapter.query, (original_id,), lease)
        if (outcome.status != "FOUND" or outcome.state != "RESULT_READY"
                or outcome.upstream_task_id != original_id or outcome.result is None
                or outcome.external_submission_id != external
                or outcome.protocol_version != binding.protocol_version
                or outcome.test_only != binding.adapter.test_only):
            raise TransitionError("EVIDENCE_MISMATCH")
        # Older workers did not retain warnings; compare the immutable artifact
        # identity, hash and length, then retain warnings from the fresh record.
        if not compatible_text_manifest(old.result, outcome.result):
            raise TransitionError("RESULT_MANIFEST_MISMATCH")
        reference = upstream._observe(task_id, identity, attempt_id, "query", outcome)
        event = VerifiedEvent(
            status="VERIFIED", protocol_version=outcome.protocol_version,
            test_only=outcome.test_only, agent_id=binding.wire_agent_id,
            event_id=event_id, sequence=2, state="RESULT_READY",
            external_submission_id=external, upstream_task_id=original_id,
            result=outcome.result,
        )
        with upstream.factory() as session, session.begin():
            task = locked_execution(session, task_id, lease)
            binding = upstream.registry.bind_task(session, task)
            upstream._verify_row(session, task, reference, "observation")
            callbacks._manifest(session, task, event, binding)
            receipt = callbacks._persist(
                session, task, binding, event, "poll",
                content_digest(event.model_dump(mode="json")), reference,
            )
            if receipt.status not in {"ACCEPTED", "DUPLICATE"}:
                raise TransitionError("EVIDENCE_MISMATCH")
        callbacks.reduce_pending(task_id, lease)
        view = upstream._view(task_id)
        if view.state != "SAVING":
            raise TransitionError("TEXT_RESULT_RECOVERY_UNAVAILABLE")
        return view
    finally:
        upstream.leases.release(lease)
