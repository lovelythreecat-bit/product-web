"""Submission and original-task reconciliation. No result publication or settlement.

All transport calls happen outside database transactions. Only trusted composition
installs these durable verifiers. TEST_ONLY scope proofs never authorize production.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError

from app.agents.contracts import QueryOutcome, SubmitOutcome
from app.agents.media_http import MediaServiceError
from app.agents.models import UpstreamAttempt, UpstreamEvidence
from app.catalog.schemas import content_digest
from app.dispatch.consumer import LeaseManager
from app.dispatch.recovery import database_now
from app.operations.telemetry import stage_diagnostic
from app.tasks.models import GenerationTask
from app.tasks.repository import locked_execution, original_submission_snapshot, task_view
from app.tasks.state_machine import (
    SafeRetryEvidence,
    TransitionError,
    TransitionEvidence,
    TransitionVerifiers,
    VerifiedTransition,
    transition_task,
)

SUBMIT_LEASE_REFRESH_SECONDS = 20


def same_scope(first, second):
    return (
        isinstance(first, dict)
        and isinstance(second, dict)
        and first.get("instance_id") is not None
        and (first.get("instance_id"), first.get("started"))
        == (second.get("instance_id"), second.get("started"))
    )


def valid_checkpoint(scope):
    return (
        isinstance(scope, dict)
        and isinstance(scope.get("instance_id"), str)
        and all(type(scope.get(key)) is int for key in ("sequence", "started", "observed_at"))
        and scope["sequence"] >= 1
        and scope["started"] <= scope["observed_at"]
    )


class UpstreamService:
    def __init__(self, session_factory, registry):
        self.factory, self.registry = session_factory, registry
        self.leases = LeaseManager(session_factory)
        from app.agents.execution_pool import MediaExecutionPool, TextExecutionPool

        settings = getattr(registry, "settings", None)
        self.text_pool = TextExecutionPool(
            session_factory, getattr(settings, "text_generation_concurrency", 6),
        )
        self.media_pools = {
            "image-agent-v1": MediaExecutionPool(
                session_factory, getattr(settings, "image_generation_concurrency", 6)),
            "video-agent-v1": MediaExecutionPool(
                session_factory, getattr(settings, "video_generation_concurrency", 1)),
        }

    def _latest(self, session, task_id):
        return session.scalar(
            select(UpstreamAttempt)
            .where(UpstreamAttempt.task_id == task_id)
            .order_by(UpstreamAttempt.created_at.desc(), UpstreamAttempt.id.desc())
            .limit(1)
        )

    def _identity(self, session, task, binding):
        return dict(
            task_id=task.id,
            agent_id=task.agent_id,
            agent_version=task.agent_version,
            wire_agent_id=binding.wire_agent_id,
            protocol_version=binding.protocol_version,
            external_submission_id=task.external_submission_id,
            endpoint_digest=binding.endpoint_digest,
            snapshot_digest=content_digest(original_submission_snapshot(session, task.id)),
        )

    def _verify_row(self, session, task, reference, kind):
        row = session.get(UpstreamEvidence, reference)
        binding = self.registry.bind_task(session, task)
        identity = self._identity(session, task, binding)
        if (
            row is None
            or row.task_id != task.id
            or row.kind != kind
            or row.payload.get("identity") != identity
        ):
            raise TransitionError("EVIDENCE_MISMATCH")
        return row, binding

    def _accepted(self, session, task, target, reference):
        row, binding = self._verify_row(session, task, reference, "observation")
        outcome = self._parse(row)
        if (
            outcome.status not in {"ACCEPTED", "FOUND", "COMPLETED", "NEEDS_INPUT"}
            or not outcome.upstream_task_id
            or outcome.external_submission_id != task.external_submission_id
            or outcome.protocol_version != binding.protocol_version
            or outcome.test_only != binding.adapter.test_only
        ):
            raise TransitionError("EVIDENCE_MISMATCH")
        other = session.scalar(
            select(GenerationTask.id).where(
                GenerationTask.agent_id == task.agent_id,
                GenerationTask.upstream_id == outcome.upstream_task_id,
                GenerationTask.id != task.id,
            )
        )
        if other:
            raise TransitionError("UPSTREAM_IDENTITY_CONFLICT")
        return VerifiedTransition(
            task.id,
            task.agent_id,
            task.agent_version,
            task.external_submission_id,
            "accepted",
            row.id,
            binding.protocol_version,
            upstream_id=outcome.upstream_task_id,
        )

    def _valid_absence(self, proof, task, binding, scope, minimum_sequence):
        # A protocol-authoritative checkpoint bounds a proof in the SAME instance.
        # DB wall time is intentionally absent: only DB leases/receipt timestamps use it.
        return (
            proof is not None
            and proof.test_only
            and proof.agent_id == binding.wire_agent_id
            and proof.external_submission_id == task.external_submission_id
            and proof.protocol_version == binding.protocol_version
            and proof.verified_by == "TEST_ONLY.atomic_simulator"
            and proof.consistency == "atomic_simulator_lifetime"
            and proof.scope_instance_id == scope["instance_id"]
            and proof.reference
            == f"{scope['instance_id']}:{binding.wire_agent_id}:{task.external_submission_id}"
            and proof.coverage_start_sequence == 0
            and type(proof.coverage_end_sequence) is int
            and proof.verified_sequence == proof.coverage_end_sequence
            and minimum_sequence <= proof.coverage_end_sequence <= scope["sequence"]
            and all(
                value.is_integer()
                for value in (proof.coverage_start, proof.coverage_end, proof.verified_at)
            )
            and proof.coverage_start == scope["started"]
            and proof.coverage_start
            <= proof.verified_at
            <= proof.coverage_end
            <= scope["observed_at"]
        )

    def _safe_retry(self, session, task, target, reference):
        source = session.get(UpstreamEvidence, reference)
        if source is not None and source.kind in {"observation", "concurrency_rejection_audit"}:
            return self._text_rejection_retry(session, task, reference)
        row, binding = self._verify_row(session, task, reference, "safe_retry")
        payload = row.payload
        latest = self._latest(session, task.id)
        attempts = session.scalars(
            select(UpstreamAttempt).where(UpstreamAttempt.task_id == task.id)
        ).all()
        scope = payload.get("scope")
        if (
            latest is None
            or row.attempt_id != latest.id
            or task.upstream_id
            or payload.get("basis") not in {"reliable_idempotency", "proven_not_accepted"}
            or payload.get("verified_by") != "TEST_ONLY.atomic_simulator"
            or payload.get("consistency") != "atomic_simulator_lifetime"
            or not attempts
            or not valid_checkpoint(scope)
            or any(
                not valid_checkpoint(a.scope) or not same_scope(a.scope, scope) for a in attempts
            )
            or any(
                any(getattr(a, key) != value for key, value in payload["identity"].items())
                for a in attempts
            )
            or payload.get("coverage_start_sequence") != 0
            or type(payload.get("coverage_end_sequence")) is not int
            or not max(a.scope["sequence"] for a in attempts)
            <= payload["coverage_end_sequence"]
            <= scope["sequence"]
            or payload.get("coverage_start") != scope["started"]
            or not scope["started"] <= payload.get("coverage_end", -1) <= scope["observed_at"]
        ):
            raise TransitionError("EVIDENCE_REQUIRED")
        if payload["basis"] == "proven_not_accepted":
            source = session.get(UpstreamEvidence, payload.get("source_reference"))
            if (
                source is None
                or source.task_id != task.id
                or source.attempt_id != latest.id
                or source.kind != "observation"
                or source.payload.get("identity") != payload["identity"]
            ):
                raise TransitionError("EVIDENCE_REQUIRED")
            proof = self._parse(source).absence_proof
            if (
                not self._valid_absence(
                    proof, task, binding, scope, max(a.scope["sequence"] for a in attempts)
                )
                or proof.reference != payload.get("source_proof")
                or proof.coverage_start != payload["coverage_start"]
                or proof.coverage_end != payload["coverage_end"]
                or proof.coverage_end_sequence != payload["coverage_end_sequence"]
            ):
                raise TransitionError("EVIDENCE_REQUIRED")
            # An absence query cannot exclude a still-in-flight earlier request.
            # Require each prior submission's durable, same-instance nonacceptance response.
            for attempt in attempts:
                replies = session.scalars(
                    select(UpstreamEvidence).where(
                        UpstreamEvidence.attempt_id == attempt.id,
                        UpstreamEvidence.kind == "observation",
                    )
                ).all()
                if not any(
                    r.payload.get("operation") == "submit"
                    and r.payload.get("identity") == payload["identity"]
                    and self._parse(r).status == "PROVEN_NOT_ACCEPTED"
                    and self._valid_absence(
                        self._parse(r).absence_proof,
                        task,
                        binding,
                        scope,
                        attempt.scope["sequence"],
                    )
                    for r in replies
                ):
                    raise TransitionError("EVIDENCE_REQUIRED")
        retry = SafeRetryEvidence(
            binding.protocol_version,
            payload["basis"],
            row.id,
            payload["verified_by"],
            row.created_at,
        )
        return VerifiedTransition(
            task.id,
            task.agent_id,
            task.agent_version,
            task.external_submission_id,
            "safe_retry",
            row.id,
            binding.protocol_version,
            safe_retry=retry,
        )

    def _text_rejection_retry(self, session, task, reference):
        """Every previous POST must have a durable, explicit pre-admission rejection."""
        from app.agents.image import ImageAgentAdapter
        from app.agents.text import TextAgentAdapter

        source = session.get(UpstreamEvidence, reference)
        kind = ("concurrency_rejection_audit" if source is not None
                and source.kind == "concurrency_rejection_audit" else "observation")
        row, binding = self._verify_row(session, task, reference, kind)
        latest = self._latest(session, task.id)
        attempts = session.scalars(select(UpstreamAttempt).where(
            UpstreamAttempt.task_id == task.id,
        )).all()
        if (not isinstance(binding.adapter, (TextAgentAdapter, ImageAgentAdapter))
                or task.upstream_id
                or (kind == "concurrency_rejection_audit"
                    and not isinstance(binding.adapter, TextAgentAdapter))
                or latest is None or row.attempt_id != latest.id
                or row.payload.get("operation") != "submit"
                or self._parse(row).status != "RATE_LIMITED"):
            raise TransitionError("EVIDENCE_REQUIRED")
        identity = self._identity(session, task, binding)
        for attempt in attempts:
            replies = session.scalars(select(UpstreamEvidence).where(
                UpstreamEvidence.attempt_id == attempt.id,
                UpstreamEvidence.kind == "observation",
            )).all()
            audits = session.scalars(select(UpstreamEvidence).where(
                UpstreamEvidence.attempt_id == attempt.id,
                UpstreamEvidence.kind == "concurrency_rejection_audit",
            )).all()
            audited = isinstance(binding.adapter, TextAgentAdapter) and any(
                audit.task_id == task.id and audit.payload.get("identity") == identity
                and audit.payload.get("verified_by") == "text-agent-v1.database_audit"
                and audit.payload.get("upstream_record_absent") is True
                and audit.payload.get("http_status") == 429
                and audit.payload.get("error_code") == "concurrency_limit"
                and audit.created_at >= attempt.created_at + timedelta(seconds=600)
                and audit.created_at <= database_now(session)
                for audit in audits
            )
            submits = [reply for reply in replies if reply.payload.get("operation") == "submit"]
            if (not submits or attempt.scope != binding.adapter.retry_scope()
                    or any(getattr(attempt, key) != value for key, value in identity.items())
                    or any(reply.payload.get("identity") != identity
                           or (self._parse(reply).status != "RATE_LIMITED"
                               and not (audited and self._parse(reply).status == "UNKNOWN"))
                           or self._parse(reply).external_submission_id
                           != task.external_submission_id for reply in submits)
                    or any(self._parse(reply).status in {
                        "ACCEPTED", "COMPLETED", "FOUND", "NEEDS_INPUT",
                    } for reply in replies)):
                raise TransitionError("EVIDENCE_REQUIRED")
        retry = SafeRetryEvidence(binding.protocol_version, "proven_not_accepted", row.id,
                                  binding.protocol_version + ".admission_rejection", row.created_at)
        return VerifiedTransition(task.id, task.agent_id, task.agent_version,
                                  task.external_submission_id, "safe_retry", row.id,
                                  binding.protocol_version, safe_retry=retry)

    def _text_retry_reference(self, session, task):
        latest = self._latest(session, task.id)
        if latest is None:
            return None
        rows = session.scalars(select(UpstreamEvidence).where(
            UpstreamEvidence.attempt_id == latest.id,
            UpstreamEvidence.kind.in_({"observation", "concurrency_rejection_audit"}),
        ).order_by(UpstreamEvidence.created_at.desc(), UpstreamEvidence.id.desc())).all()
        for row in rows:
            if (row.payload.get("operation") == "submit"
                    and self._parse(row).status == "RATE_LIMITED"):
                self._text_rejection_retry(session, task, row.id)
                return row.id
        return None

    def _queue(self, task_id, lease, *, reference=None, seconds=1):
        from app.dispatch.outbox import rearm_outbox

        with self.factory() as session, session.begin():
            task = locked_execution(session, task_id, lease)
            if task.state != "QUEUED":
                self._change(session, task, lease, "QUEUED", reference)
            task.investigation_reason = None
            due = database_now(session) + timedelta(seconds=seconds)
            task.submission_not_before = due
            task.recovery_due_at = due
            rearm_outbox(session, task.id, "recover", ready_at=due)
        return self._view(task_id)

    def _install(self, session):
        session.info["transition_verifiers"] = TransitionVerifiers(
            {"accepted": self._accepted, "safe_retry": self._safe_retry}
        )

    def _change(self, session, task, lease, state, reference=None):
        self._install(session)
        return transition_task(
            session, task.id, task.state_version, state, TransitionEvidence(lease, reference)
        )

    def _view(self, task_id):
        with self.factory() as session:
            return task_view(session, session.get(GenerationTask, task_id))

    def _investigate(self, session, task, lease, reason):
        if task.state in {"SUBMITTING", "RUNNING"}:
            self._change(session, task, lease, "INVESTIGATING")
        task.investigation_reason = reason

    @staticmethod
    def _parse(row):
        model = SubmitOutcome if row.payload["operation"] == "submit" else QueryOutcome
        return model.model_validate(row.payload["outcome"])

    def _observe(self, task_id, identity, attempt_id, operation, outcome):
        # Append transport facts even if the sender has since lost its lease.
        with self.factory() as session, session.begin():
            payload = dict(identity=identity, operation=operation,
                           outcome=outcome.model_dump(mode="json"))
            if outcome.status == "RATE_LIMITED" and outcome.protocol_version == "image-agent-v1":
                from app.agents.media_execution import MediaExecution

                state = session.get(MediaExecution, task_id)
                if state is not None:
                    payload["transport_rejection"] = state.state.get("submission_rejection")
            row = UpstreamEvidence(
                id=str(uuid4()),
                task_id=task_id,
                attempt_id=attempt_id,
                kind="observation",
                created_at=database_now(session),
                payload=payload,
            )
            session.add(row)
            return row.id

    def _apply_observation(self, task_id, lease, reference, *, explicit=False):
        try:
            with self.factory() as session, session.begin():
                task = locked_execution(session, task_id, lease)
                if self._manual_wait(task) and not explicit:
                    return
                row = session.get(UpstreamEvidence, reference)
                outcome = self._parse(row)
                if outcome.status == "RATE_LIMITED":
                    self._text_rejection_retry(session, task, reference)
                    delay = outcome.retry_after_seconds
                    self._change(session, task, lease, "QUEUED", reference)
                    task.investigation_reason = None
                    from app.dispatch.outbox import rearm_outbox

                    due = database_now(session) + timedelta(seconds=max(1, delay))
                    task.submission_not_before = due
                    task.recovery_due_at = due
                    rearm_outbox(session, task.id, "recover", ready_at=due)
                    return
                if task.state in {"SUBMITTED", "QUEUED"}:
                    # An old intent routed through QUEUED must reconcile, never submit blindly.
                    self._change(session, task, lease, "SUBMITTING")
                if task.state not in {"SUBMITTING", "RUNNING", "INVESTIGATING"}:
                    return
                if outcome.status in {"ACCEPTED", "FOUND", "COMPLETED", "NEEDS_INPUT"}:
                    proof = self._accepted(session, task, "RUNNING", reference)
                    if task.upstream_id and task.upstream_id != proof.upstream_id:
                        raise TransitionError("UPSTREAM_IDENTITY_CONFLICT")
                    if task.state != "RUNNING" and (
                        outcome.status != "NEEDS_INPUT" or not task.upstream_id
                    ):
                        self._change(session, task, lease, "RUNNING", reference)
                    if outcome.status == "NEEDS_INPUT":
                        self._investigate(session, task, lease, "UPSTREAM_NEEDS_INPUT")
                        stage_diagnostic(stage="upstream", task_id=task.id,
                                         state_version=task.state_version, lease=lease,
                                         code="UPSTREAM_NEEDS_INPUT", outcome="wait")
                    else:
                        task.investigation_reason = None
                    # T10 consumes this same durable observation for result/failure processing.
                else:
                    self._investigate(session, task, lease, "UPSTREAM_ACCEPTANCE_UNCONFIRMED")
        except (IntegrityError, TransitionError) as error:
            if isinstance(error, TransitionError) and str(error) == "LEASE_LOST":
                raise
            with self.factory() as session, session.begin():
                task = locked_execution(session, task_id, lease)
                session.add(
                    UpstreamEvidence(
                        id=str(uuid4()),
                        task_id=task_id,
                        kind="conflict",
                        payload={"reference": reference, "reason": "UPSTREAM_IDENTITY_CONFLICT"},
                        created_at=database_now(session),
                    )
                )
                self._investigate(session, task, lease, "UPSTREAM_IDENTITY_CONFLICT")

    @staticmethod
    def _manual_wait(task):
        # A pending callback permits local inbox reduction, not remote recovery.
        # Only the reducer can clear the original blocker after genuine progress.
        return task.investigation_reason in {
            "UPSTREAM_NEEDS_INPUT", "CALLBACK_EVENT_CONFLICT",
            "CALLBACK_INBOX_PENDING:UPSTREAM_NEEDS_INPUT",
            "CALLBACK_INBOX_PENDING:CALLBACK_EVENT_CONFLICT",
        }

    def submit_original_task(self, task_id, lease):
        retry = None
        with self.factory() as session:
            task = session.get(GenerationTask, task_id)
            if (task.state == "QUEUED" and task.submission_not_before is not None
                    and task.submission_not_before > database_now(session)):
                return task_view(session, task)
            if task.state == "QUEUED" and not task.upstream_id:
                reference = self._text_retry_reference(session, task)
                if reference:
                    retry = self._text_rejection_retry(session, task, reference).safe_retry
            needs_recovery = (
                task.upstream_id
                or task.state not in {"SUBMITTED", "QUEUED"}
                or self._latest(session, task_id) is not None
            )
        if retry is not None:
            return self._submit(task_id, lease, retry)
        if needs_recovery:
            return self.recover_original_task(task_id, lease=lease)
        return self._submit(task_id, lease)

    def _submit(self, task_id, lease, evidence=None):
        from app.agents.execution_pool import execution_scope, text_scope
        from app.agents.text import TextAgentAdapter

        with self.factory() as session:
            task = session.get(GenerationTask, task_id)
            adapter = self.registry.bind_task(session, task).adapter
        if adapter.protocol_version in self.media_pools:
            scope = execution_scope(adapter.protocol_version, adapter.profile.base_url)
            pool = self.media_pools[adapter.protocol_version]
            if pool.acquire(scope, task_id, lease=lease, protocol=adapter.protocol_version,
                            base_url=adapter.profile.base_url) is None:
                return self._queue(task_id, lease,
                                   reference=evidence.reference if evidence else None)
            result = self._submit_with_slot(task_id, lease, evidence)
            if result.state == "QUEUED":
                pool.release(scope, task_id, lease=lease)
            return result
        if not isinstance(adapter, TextAgentAdapter):
            return self._submit_with_slot(task_id, lease, evidence)
        scope = text_scope(adapter.profile.base_url)
        token = self.text_pool.acquire(scope)
        if token is None:
            return self._queue(task_id, lease, reference=evidence.reference if evidence else None)
        try:
            result = self._submit_with_slot(task_id, lease, evidence)
        except BaseException:
            # A crash/unknown transport outcome can leave upstream work running.
            # Keep the slot until its deadline (longer than the 600s HTTP maximum).
            raise
        else:
            if result.state != "INVESTIGATING":
                self.text_pool.release(scope, token)
            return result

    def _submit_with_slot(self, task_id, lease, evidence=None):
        with self.factory() as session:
            task = session.get(GenerationTask, task_id)
            binding = self.registry.bind_task(session, task)
        scope = binding.adapter.retry_scope()
        with self.factory() as session, session.begin():
            task = locked_execution(session, task_id, lease)
            binding = self.registry.bind_task(session, task)
            if task.upstream_id:
                raise TransitionError("QUERY_ORIGINAL_REQUIRED")
            latest = self._latest(session, task_id)
            if latest:
                if not isinstance(evidence, SafeRetryEvidence):
                    raise TransitionError("EVIDENCE_REQUIRED")
                proof = self._safe_retry(session, task, "SUBMITTING", evidence.reference)
                if proof.safe_retry != evidence:
                    raise TransitionError("EVIDENCE_MISMATCH")
                row = session.get(UpstreamEvidence, evidence.reference)
                retry_scope = (latest.scope if row.kind in {
                    "observation", "concurrency_rejection_audit",
                }
                               else row.payload["scope"])
                if scope is None or not same_scope(scope, retry_scope):
                    self._investigate(session, task, lease, "UPSTREAM_SCOPE_UNCONFIRMED")
                    return task_view(session, task)
                # QUEUED is not permission to skip durable retry validation.
                if task.state in {"SUBMITTING", "RUNNING"}:
                    self._investigate(session, task, lease, "UPSTREAM_ACCEPTANCE_UNCONFIRMED")
            elif task.state not in {"SUBMITTED", "QUEUED"}:
                raise TransitionError("EVIDENCE_REQUIRED")
            if scope is None:
                # No attempt or generation I/O exists yet. Preserve the schedulable stage;
                # LeaseManager.release supplies the normal database retry deadline.
                task.investigation_reason = "UPSTREAM_SCOPE_UNCONFIRMED"
                return task_view(session, task)
            self._change(
                session, task, lease, "SUBMITTING", evidence.reference if evidence else None
            )
            task.submission_not_before = None
            snapshot = original_submission_snapshot(session, task_id)
            identity = self._identity(session, task, binding)
            attempt = UpstreamAttempt(
                id=str(uuid4()),
                **identity,
                snapshot=snapshot,
                scope=scope,
                fencing_token=lease.fencing_token,
                retry_reference=evidence.reference if evidence else None,
                created_at=database_now(session),
            )
            session.add(attempt)
            attempt_id, external = attempt.id, task.external_submission_id
        # Both intent and SUBMITTING are now committed; no external I/O inside a DB transaction.
        outcome = self._submit_transport(binding.adapter, snapshot, external, scope, lease)
        reference = self._observe(task_id, identity, attempt_id, "submit", outcome)
        self._apply_observation(task_id, lease, reference)
        return self._view(task_id)

    def _submit_transport(self, adapter, snapshot, external, scope, lease):
        from app.agents.image import ImageAgentAdapter
        from app.agents.text import TextAgentAdapter
        from app.agents.video import VideoAgentAdapter

        if not isinstance(adapter, (TextAgentAdapter, ImageAgentAdapter, VideoAgentAdapter)):
            return adapter.submit_scoped(snapshot, external, scope)
        return self._leased_transport(adapter.submit_scoped, (snapshot, external, scope), lease)

    def _leased_transport(self, operation, args, lease):
        if self.leases.renew(lease) is None:
            raise TransitionError("LEASE_LOST")
        # Long synchronous model workflows must not outlive their fencing lease.
        # Lost ownership never cancels/repeats the request: persist its observation,
        # then let the normal lease check decide who may apply it.
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="agent-transport") as pool:
            pending = pool.submit(operation, *args)
            owned = True
            while True:
                try:
                    return pending.result(timeout=SUBMIT_LEASE_REFRESH_SECONDS)
                except TimeoutError:
                    if pending.done():
                        # The operation itself may raise TimeoutError. A finished
                        # failed future is not a heartbeat timeout to poll forever.
                        return pending.result()
                    if owned:
                        try:
                            owned = self.leases.renew(lease) is not None
                        except Exception as error:
                            stage_diagnostic(stage="upstream", lease=lease, error=error,
                                             code="LEASE_LOST", outcome="error")
                            owned = False

    def _recover_image_rejection(self, task_id, binding, lease):
        """Recover a refusal committed by the adapter before its outcome receipt."""
        if binding.protocol_version != "image-agent-v1":
            return
        from app.agents.media_execution import MediaTaskStore

        with self.factory() as session:
            task = session.get(GenerationTask, task_id)
            latest = self._latest(session, task_id)
            if task.upstream_id or latest is None:
                return
            seen = session.scalars(select(UpstreamEvidence).where(
                UpstreamEvidence.attempt_id == latest.id,
                UpstreamEvidence.kind == "observation",
            )).all()
            if any(row.payload.get("operation") == "submit" for row in seen):
                return
            identity = self._identity(session, task, binding)
            external, attempt_id = task.external_submission_id, latest.id
        marker = MediaTaskStore(self.factory, task_id, "image", lease).submission_rejection(
            binding.adapter.retry_scope(), external,
        )
        if marker is not None:
            delay = marker.get("retry_after_seconds", 5)
            self._observe(task_id, identity, attempt_id, "submit", SubmitOutcome(
                status="RATE_LIMITED", protocol_version="image-agent-v1",
                external_submission_id=external,
                retry_after_seconds=delay if type(delay) is int and 1 <= delay <= 3600 else 5,
            ))

    def recover_original_task(self, task_id, evidence=None, *, lease=None):
        owned = lease is None
        lease = lease or self.leases.claim_task(task_id, "upstream-recovery:" + uuid4().hex)
        if lease is None:
            return self._view(task_id)
        try:
            with self.factory() as session, session.begin():
                task = locked_execution(session, task_id, lease)
                if self._manual_wait(task) and not owned:
                    return task_view(session, task)
                if task.state not in {
                    "SUBMITTED",
                    "QUEUED",
                    "SUBMITTING",
                    "RUNNING",
                    "INVESTIGATING",
                }:
                    return task_view(session, task)
                binding = self.registry.bind_task(session, task)
                if evidence is not None and not task.upstream_id:
                    if not isinstance(evidence, SafeRetryEvidence):
                        raise TransitionError("EVIDENCE_REQUIRED")
                    if (
                        self._safe_retry(session, task, "SUBMITTING", evidence.reference).safe_retry
                        != evidence
                    ):
                        raise TransitionError("EVIDENCE_MISMATCH")
                identity = self._identity(session, task, binding)
                latest = self._latest(session, task_id)
                attempt_id = latest.id if latest else None
                upstream_id, external = task.upstream_id, task.external_submission_id
            # History may grow through repeated unavailable observations. Scan it
            # without holding the account/task lock; application revalidates the
            # selected immutable evidence and the current fencing lease.
            if not upstream_id:
                self._recover_image_rejection(task_id, binding, lease)
            pending = self._pending_observation(task_id, lease) if not upstream_id else None
            if pending:
                self._apply_observation(task_id, lease, pending, explicit=owned)
                result = self._view(task_id)
                if result.state in {"RUNNING", "QUEUED"} or self._manual_wait(result):
                    return result
            from app.agents.media_execution import saved_media_task_id

            original_id = upstream_id or saved_media_task_id(binding.adapter, external)
            operation = binding.adapter.query if original_id else binding.adapter.query_by_external
            outcome = self._leased_transport(operation, (original_id or external,), lease)
            reference = self._observe(task_id, identity, attempt_id, "query", outcome)
            self._apply_observation(task_id, lease, reference, explicit=owned)
            if (not upstream_id and outcome.status not in {"FOUND", "NEEDS_INPUT"}
                    and evidence is not None):
                return self._submit(task_id, lease, evidence)
            return self._view(task_id)
        finally:
            if owned:
                self.leases.release(lease)

    def _pending_observation(self, task_id, lease):
        cursor = None
        while True:
            if self.leases.renew(lease) is None:
                raise TransitionError("LEASE_LOST")
            with self.factory() as session:
                query = select(UpstreamEvidence).where(
                    UpstreamEvidence.task_id == task_id,
                    UpstreamEvidence.kind.in_({"observation", "concurrency_rejection_audit"}),
                )
                if cursor:
                    query = query.where(or_(
                        UpstreamEvidence.created_at < cursor[0],
                        and_(UpstreamEvidence.created_at == cursor[0],
                             UpstreamEvidence.id < cursor[1]),
                    ))
                rows = session.scalars(query.order_by(
                    UpstreamEvidence.created_at.desc(), UpstreamEvidence.id.desc(),
                ).limit(100)).all()
                for row in rows:
                    try:
                        if self._parse(row).status in {"ACCEPTED", "FOUND", "COMPLETED",
                                                       "NEEDS_INPUT", "RATE_LIMITED"}:
                            return row.id
                    except (ValueError, KeyError, TypeError) as error:
                        stage_diagnostic(stage="upstream", task_id=task_id, lease=lease,
                                         error=error, code="STAGE_EXCEPTION", outcome="error")
                if len(rows) < 100:
                    return None
                cursor = rows[-1].created_at, rows[-1].id

    def collect_retry_evidence(self, task_id, *, kind):
        """Trusted service operation, never an HTTP proof constructor or client boolean."""
        if kind not in {"reliable_idempotency", "proven_not_accepted"}:
            raise TransitionError("EVIDENCE_REQUIRED")
        with self.factory() as session:
            task = session.get(GenerationTask, task_id)
            binding = self.registry.bind_task(session, task)
            identity = self._identity(session, task, binding)
            latest = self._latest(session, task_id)
            if latest is None or task.upstream_id:
                return None
            attempt_id, external = latest.id, task.external_submission_id
        scope = binding.adapter.retry_scope()
        # The text API's finite idempotency retention is not a durable absence
        # proof. Until a lookup-by-key protocol exists, never automatically POST again.
        from app.agents.text import TextAgentAdapter

        if isinstance(binding.adapter, TextAgentAdapter):
            return None
        if scope is None:
            return None
        source_reference, absence = None, None
        if kind == "proven_not_accepted":
            outcome = binding.adapter.query_by_external(external)
            source_reference = self._observe(task_id, identity, attempt_id, "query", outcome)
            absence = outcome.absence_proof
            if absence is None or not absence.reference.startswith(scope["instance_id"] + ":"):
                return None
            after = binding.adapter.retry_scope()
            if after is None or not same_scope(scope, after):
                return None
            scope = after
        with self.factory() as session, session.begin():
            task = session.get(GenerationTask, task_id)
            latest = self._latest(session, task_id)
            if latest.id != attempt_id or not same_scope(latest.scope, scope):
                return None
            if source_reference:
                # Build from the actual durable source, never from an unpersisted float copy.
                source = session.get(UpstreamEvidence, source_reference)
                absence = self._parse(source).absence_proof
                if not self._valid_absence(absence, task, binding, scope, latest.scope["sequence"]):
                    raise TransitionError("EVIDENCE_REQUIRED")
            current = database_now(session)
            row = UpstreamEvidence(
                id=str(uuid4()),
                task_id=task_id,
                attempt_id=attempt_id,
                kind="safe_retry",
                created_at=current,
                payload=dict(
                    identity=identity,
                    basis=kind,
                    scope=scope,
                    verified_by="TEST_ONLY.atomic_simulator",
                    consistency="atomic_simulator_lifetime",
                    coverage_start=absence.coverage_start if absence else scope["started"],
                    coverage_end=absence.coverage_end if absence else scope["observed_at"],
                    coverage_start_sequence=0,
                    coverage_end_sequence=absence.coverage_end_sequence
                    if absence
                    else scope["sequence"],
                    source_reference=source_reference,
                    source_proof=absence.reference if absence else None,
                ),
            )
            session.add(row)
            session.flush()
            return self._safe_retry(session, task, "SUBMITTING", row.id).safe_retry

    def poll_original_task(self, task_id, *, lease=None):
        from app.agents.callbacks import CallbackService

        return CallbackService(self).poll_original_task(task_id, lease=lease)

    def original_result(self, task_id):
        from app.agents.callbacks import CallbackService

        return CallbackService(self).original_result(task_id)

    def pending_failure(self, task_id):
        from app.agents.callbacks import CallbackService

        return CallbackService(self).pending_failure(task_id)

    def handle(self, context):
        try:
            if context.action != "prepare_submission":
                from app.agents.video_commands import resume_queued_video_command

                if resume_queued_video_command(self, context.task_id, context.lease):
                    return
            if context.action == "prepare_submission":
                self.submit_original_task(context.task_id, context.lease)
            else:
                self.poll_original_task(context.task_id, lease=context.lease)
        except (LookupError, ValueError, MediaServiceError) as error:
            if isinstance(error, MediaServiceError) and getattr(error, "command_rejected", False):
                return
            stage_diagnostic(stage="upstream", task_id=context.task_id, action=context.action,
                             lease=context.lease, error=error,
                             http_status=getattr(error, "status_code", None),
                             code="UPSTREAM_BINDING_UNAVAILABLE", outcome="error")
            with self.factory() as session, session.begin():
                task = locked_execution(session, context.task_id, context.lease)
                if self._manual_wait(task):
                    return
                if task.state in {"SUBMITTED", "QUEUED"}:
                    self._change(session, task, context.lease, "SUBMITTING")
                self._investigate(session, task, context.lease, "UPSTREAM_BINDING_UNAVAILABLE")
