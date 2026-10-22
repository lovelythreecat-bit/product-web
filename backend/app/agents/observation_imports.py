"""Durable source progress and content-scoped dispositions, never a mutable cursor.

Source identity and payload are immutable. Changing a verifier requires an explicit
rule version; historical receipts remain audit facts and are never overwritten.
Callers hold the task/account lock when checking and recording a disposition.
"""

from sqlalchemy import exists, select

from app.agents.models import ObservationImport, UpstreamEvidence
from app.catalog.schemas import content_digest

RULE_VERSION = "observation-v1"


def context_digest(upstream, session, task, binding, rule_version):
    attempt = upstream._latest(session, task.id)
    return content_digest(dict(
        identity=upstream._identity(session, task, binding), upstream_id=task.upstream_id,
        test_only=binding.adapter.test_only, attempt_id=attempt.id if attempt else None,
        rule_version=rule_version,
    ))


def pending_sources(task_id, context):
    processed = exists().where(
        ObservationImport.source_ref == UpstreamEvidence.id,
        ObservationImport.context_digest == context,
    )
    return select(UpstreamEvidence).where(
        UpstreamEvidence.task_id == task_id, UpstreamEvidence.kind == "observation", ~processed,
    ).order_by(UpstreamEvidence.created_at, UpstreamEvidence.id).execution_options(yield_per=100)


def previous_variant(session, task_id, context, fingerprint):
    # The account/task lock serializes concurrent importers. A committed decision
    # and every source marker use the same transaction as its evidence writes.
    return session.scalar(select(ObservationImport).where(
        ObservationImport.task_id == task_id,
        ObservationImport.context_digest == context,
        ObservationImport.fingerprint == fingerprint,
    ).limit(1).with_for_update())


def record_sources(session, task_id, references, context, fingerprint, rule_version, receipt, now):
    # A second importer may have committed while this caller scanned history.
    existing = set(session.scalars(select(ObservationImport.source_ref).where(
        ObservationImport.source_ref.in_(references),
        ObservationImport.context_digest == context,
    ).with_for_update()))
    session.add_all([
        ObservationImport(
            source_ref=reference, task_id=task_id, context_digest=context,
            fingerprint=fingerprint, rule_version=rule_version,
            disposition=receipt.status, event_ref=receipt.reference, created_at=now,
        ) for reference in references if reference not in existing
    ])
