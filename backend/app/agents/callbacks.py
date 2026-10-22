"""TEST_ONLY callback inbox and lease-fenced reducer shared with polling.

No caller-asserted verification is accepted at the HTTP boundary. A receipt is
committed before a worker may consume it. Source bytes are hashed, never logged.
mock-v1 has a fixed lifecycle: sequence 1 running, sequence 2 final result/failure;
its signed upstream:sequence event ID is also its nonce. This is not a generic
provider protocol and must not be enabled in production.
"""

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from time import monotonic
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.agents.contracts import ResultManifest, VerifiedEvent
from app.agents.mock_server import MAX_BODY
from app.agents.models import AgentEvent, AgentEventDecision, UpstreamEvidence
from app.agents.registry import AgentRegistry
from app.auth.models import User
from app.catalog.models import AgentRecord
from app.catalog.schemas import content_digest
from app.dispatch.outbox import rearm_outbox
from app.dispatch.recovery import TERMINAL_STATES, database_now
from app.operations.telemetry import stage_diagnostic
from app.tasks.models import GenerationTask, TaskSnapshot
from app.tasks.repository import locked_execution
from app.tasks.state_machine import (
    TransitionError,
    TransitionEvidence,
    TransitionVerifiers,
    VerifiedTransition,
    transition_task,
)

PENDING_CALLBACK_BLOCKERS = {
    "CALLBACK_INBOX_PENDING:UPSTREAM_NEEDS_INPUT": "UPSTREAM_NEEDS_INPUT",
    "CALLBACK_INBOX_PENDING:CALLBACK_EVENT_CONFLICT": "CALLBACK_EVENT_CONFLICT",
}


@dataclass(frozen=True)
class EventReceipt:
    status: str
    reference: str | None = None


@dataclass(frozen=True)
class OriginalResult:
    """Internal T11 handoff read from an APPLIED receipt, never an HTTP input DTO."""

    reference: str
    task_id: str
    agent_id: str
    agent_version: str
    wire_agent_id: str
    protocol_version: str
    external_submission_id: str
    upstream_id: str
    snapshot_digest: str
    manifest: ResultManifest


class CallbackService:
    def __init__(self, upstream):
        self.upstream = upstream
        self.factory, self.registry = upstream.factory, upstream.registry

    @staticmethod
    def _lock(session, task_id):
        user_id = session.scalar(select(GenerationTask.user_id).where(GenerationTask.id == task_id))
        session.scalar(select(User).where(User.id == user_id).with_for_update())
        return session.scalar(
            select(GenerationTask)
            .where(GenerationTask.id == task_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def _conflict(self, session, task, reason, reference=None, digest=None, *, context=None):
        # Every caller holds the account/task lock. The deterministic key and
        # primary key fence concurrent identical variants without editing history.
        key = str(uuid5(NAMESPACE_URL, content_digest(dict(
            task_id=task.id, reason=reason, reference=reference, digest=digest, context=context,
        ))))
        if session.get(UpstreamEvidence, key, with_for_update=True) is not None:
            return key
        session.add(
            UpstreamEvidence(
                id=key,
                task_id=task.id,
                kind="callback_conflict",
                payload=dict(reason=reason, reference=reference, digest=digest),
                created_at=database_now(session),
            )
        )
        session.flush()
        stage_diagnostic(stage="reducer", task_id=task.id, event_id=reference,
                         state_version=getattr(task, "state_version", None),
                         code=reason, outcome="wait")
        return key

    def receive_callback(self, agent_id, agent_version, raw, headers):
        with self.factory() as session:
            record = session.get(AgentRecord, (str(agent_id), agent_version))
            if record is None:
                raise HTTPException(403)
            try:
                binding = self.registry.bind_version(record)
            except (LookupError, ValueError):
                raise HTTPException(403) from None
            event = binding.adapter.verify_callback(raw, headers)
            if event.status not in {"VERIFIED", "DUPLICATE"}:
                raise HTTPException(403)
        return self.apply_verified_agent_event(
            binding, event, raw_digest=hashlib.sha256(raw).hexdigest()
        )

    def apply_verified_agent_event(self, agent_version, event, *, raw_digest):
        """Internal trusted adapter entry. Public routes always call receive_callback.

        agent_version is a server-resolved AgentBinding, not a requested wire ID.
        DUPLICATE remains advisory; MySQL is the replay authority.
        """
        with self.factory() as session, session.begin():
            task_id = session.scalar(
                select(GenerationTask.id).where(
                    GenerationTask.agent_id == agent_version.agent_id,
                    GenerationTask.agent_version == agent_version.agent_version,
                    GenerationTask.external_submission_id == event.external_submission_id,
                )
            )
            if task_id is None:
                return EventReceipt("REJECTED")
            task = self._lock(session, task_id)
            binding = self.registry.bind_task(session, task)
            if binding.endpoint_digest != agent_version.endpoint_digest:
                return EventReceipt("REJECTED")
            return self._persist(session, task, binding, event, "callback", raw_digest)

    def _persist(self, session, task, binding, event, source, raw_digest, source_ref=None):
        identity = self.upstream._identity(session, task, binding)
        conflict_context = content_digest(dict(
            identity=identity, event=event.model_dump(mode="json", exclude={"status"}),
            source=source,
        ))
        # Original persisted submit intent is required, even before upstream ID binding.
        attempt = self.upstream._latest(session, task.id)
        if (
            attempt is None
            or any(getattr(attempt, k) != v for k, v in identity.items())
            or event.agent_id != binding.wire_agent_id
            or event.protocol_version != binding.protocol_version
            or event.test_only != binding.adapter.test_only
            or event.external_submission_id != task.external_submission_id
            or not event.upstream_task_id
            or task.upstream_id
            and task.upstream_id != event.upstream_task_id
        ):
            self._conflict(session, task, "IDENTITY_MISMATCH", digest=raw_digest,
                           context=conflict_context)
            return EventReceipt("CONFLICT")
        other = session.scalar(
            select(GenerationTask.id).where(
                GenerationTask.agent_id == task.agent_id,
                GenerationTask.upstream_id == event.upstream_task_id,
                GenerationTask.id != task.id,
            )
        )
        if other:
            self._conflict(session, task, "UPSTREAM_IDENTITY_CONFLICT", digest=raw_digest,
                           context=conflict_context)
            return EventReceipt("CONFLICT")
        semantic = event.model_dump(mode="json", exclude={"status", "timestamp", "event_id"})
        digest = content_digest(semantic)
        previous = session.scalar(
            select(AgentEvent).where(
                AgentEvent.agent_id == task.agent_id,
                AgentEvent.agent_version == task.agent_version,
                AgentEvent.source == source,
                AgentEvent.event_id == event.event_id,
            )
            .with_for_update()
        )
        if previous:
            if previous.raw_digest == raw_digest and previous.semantic_digest == digest:
                return EventReceipt("DUPLICATE", previous.id)
            self._conflict(session, task, "EVENT_REPLAY_CONFLICT", previous.id, raw_digest,
                           context=conflict_context)
            return EventReceipt("CONFLICT", previous.id)
        row = AgentEvent(
            id=str(uuid4()),
            task_id=task.id,
            agent_id=task.agent_id,
            agent_version=task.agent_version,
            source=source,
            event_id=event.event_id,
            raw_digest=raw_digest,
            semantic_digest=digest,
            sequence=event.sequence,
            payload=dict(
                identity=identity, event=event.model_dump(mode="json"), source_reference=source_ref
            ),
            created_at=database_now(session),
        )
        session.add(row)
        session.flush()
        if task.state in TERMINAL_STATES:
            self._decision(session, task, row, "TERMINAL_LATE", None)
            self._conflict(session, task, "TERMINAL_LATE", row.id, digest)
        else:
            if source == "callback" and task.investigation_reason in {
                "CALLBACK_EVENT_CONFLICT", "UPSTREAM_NEEDS_INPUT",
            }:
                # Authorize only this newly verified local inbox receipt. The
                # reducer reinstates blockers on rejection; local progression
                # never grants an immediate remote query in poll_original_task.
                task.investigation_reason = "CALLBACK_INBOX_PENDING:" + task.investigation_reason
            rearm_outbox(session, task.id, "recover")
        return EventReceipt("ACCEPTED", row.id)

    def import_observations(self, task_id, lease, *, rule_version=None):
        from app.agents.observation_imports import (
            RULE_VERSION,
            context_digest,
            pending_sources,
            previous_variant,
            record_sources,
        )

        rule_version = rule_version or RULE_VERSION
        renew_at = monotonic() + 20

        def renew_if_due():
            nonlocal lease, renew_at
            if monotonic() >= renew_at:
                lease = self.upstream.leases.renew(lease)
                if lease is None:
                    raise TransitionError("LEASE_LOST")
                renew_at = monotonic() + 20

        # Scan/hash outside the account lock. Keep only one payload per variant
        # plus source references; no write transaction spans a history scan.
        with self.factory() as source:
            task = source.get(GenerationTask, task_id)
            binding = self.registry.bind_task(source, task)
            context = context_digest(self.upstream, source, task, binding, rule_version)
            groups = {}
            for row in source.scalars(pending_sources(task_id, context)):
                renew_if_due()
                fingerprint = content_digest(row.payload)
                if fingerprint not in groups:
                    groups[fingerprint] = (row, [])
                groups[fingerprint][1].append(row.id)
        for fingerprint, (row, references) in groups.items():
            # Bound write transactions even when one historical variant has a
            # very large number of source receipts. Reuse durable dispositions.
            for offset in range(0, len(references), 100):
                renew_if_due()
                with self.factory() as session, session.begin():
                    task = locked_execution(session, task_id, lease)
                    binding = self.registry.bind_task(session, task)
                    current = context_digest(self.upstream, session, task, binding, rule_version)
                    if current != context:
                        raise TransitionError("EVIDENCE_MISMATCH")
                    previous = previous_variant(session, task_id, context, fingerprint)
                    if previous is not None:
                        receipt = EventReceipt(previous.disposition, previous.event_ref)
                    else:
                        receipt = self._import_observation(session, task, binding, row, fingerprint)
                    record_sources(
                        session, task_id, references[offset:offset + 100], context, fingerprint,
                        rule_version, receipt, database_now(session),
                    )
                    session.flush()

    def _import_observation(self, session, task, binding, row, fingerprint):
        try:
            self.upstream._verify_row(session, task, row.id, "observation")
        except TransitionError as exc:
            if str(exc) == "LEASE_LOST":
                raise
            self._conflict(session, task, "OBSERVATION_IDENTITY", row.id, fingerprint)
            return EventReceipt("CONFLICT")
        outcome = self.upstream._parse(row)
        if outcome.status not in {"FOUND", "COMPLETED"}:
            return EventReceipt("IGNORED")
        state = getattr(outcome, "state", None) or "RESULT_READY"
        sequence = 1 if state == "RUNNING" else 2
        event = VerifiedEvent(
            status="VERIFIED", agent_id=binding.wire_agent_id,
            protocol_version=outcome.protocol_version, test_only=outcome.test_only,
            external_submission_id=outcome.external_submission_id,
            upstream_task_id=outcome.upstream_task_id,
            event_id=f"{outcome.upstream_task_id}:{sequence}", sequence=sequence,
            state=state, result=outcome.result,
        )
        digest = content_digest(event.model_dump(mode="json"))
        return self._persist(session, task, binding, event, "poll", digest, row.id)

    def _event(self, session, task, reference):
        row = session.get(AgentEvent, reference)
        binding = self.registry.bind_task(session, task)
        if (
            row is None
            or row.task_id != task.id
            or row.payload["identity"] != self.upstream._identity(session, task, binding)
        ):
            raise TransitionError("EVIDENCE_MISMATCH")
        decision = session.get(AgentEventDecision, reference)
        if decision and decision.disposition not in {"APPLIED", "FAILURE_PENDING"}:
            raise TransitionError("EVIDENCE_MISMATCH")
        accepted = session.scalars(
            select(AgentEvent)
            .join(AgentEventDecision)
            .where(
                AgentEvent.task_id == task.id,
                AgentEventDecision.disposition.in_({"APPLIED", "FAILURE_PENDING"}),
            )
        ).all()
        if any(
            prior.sequence > row.sequence
            or (prior.sequence == row.sequence and prior.semantic_digest != row.semantic_digest)
            for prior in accepted
        ):
            raise TransitionError("EVIDENCE_MISMATCH")
        event = VerifiedEvent.model_validate(row.payload["event"])
        if (
            event.external_submission_id != task.external_submission_id
            or event.agent_id != binding.wire_agent_id
            or event.protocol_version != binding.protocol_version
            or event.test_only != binding.adapter.test_only
            or task.upstream_id
            and task.upstream_id != event.upstream_task_id
        ):
            raise TransitionError("EVIDENCE_MISMATCH")
        return row, event, binding

    def _manifest(self, session, task, event, binding):
        from app.agents.text import PROTOCOL as TEXT_PROTOCOL

        if binding.protocol_version in {TEXT_PROTOCOL, "image-agent-v1", "video-agent-v1"}:
            from app.results.manifest import result_rule, validate_manifest

            return validate_manifest(
                event.result, result_rule(session, task, binding), binding, event.upstream_task_id
            )
        manifest = event.result
        snapshot = session.get(TaskSnapshot, task.id)
        if snapshot.spec_snapshot.get("delivery_kind", "single") != "single":
            from app.results.manifest import result_rule, validate_manifest

            return validate_manifest(
                manifest, result_rule(session, task, binding), binding, event.upstream_task_id
            )
        # Confirmed mock-v1 emits exactly one original artifact. A multiple/detail
        # specification cannot silently inherit this single-item test protocol.
        if (
            snapshot.spec_snapshot.get("delivery_kind", "single") != "single"
            or manifest is None
            or not manifest.complete
            or manifest.expected_items != 1
            or len(manifest.items) != 1
        ):
            raise TransitionError("RESULT_MANIFEST_MISMATCH")
        item = manifest.items[0]
        if (
            item.item_key != "original-1"
            or item.locator != f"/v1/{binding.wire_agent_id}/results/{event.upstream_task_id}"
            or item.media_type
            != {"copy": "text/plain", "image": "image/png", "video": "video/mp4"}[
                binding.wire_agent_id
            ]
        ):
            raise TransitionError("RESULT_MANIFEST_MISMATCH")
        return manifest

    def verify_original_result(self, session, task, target, reference):
        row, event, binding = self._event(session, task, reference)
        if event.state != "RESULT_READY":
            raise TransitionError("EVIDENCE_MISMATCH")
        self._manifest(session, task, event, binding)
        return self._proof(task, event, row, "original_result")

    def verify_definite_failure(self, session, task, target, reference):
        row, event, _ = self._event(session, task, reference)
        decision = session.get(AgentEventDecision, reference)
        if event.state != "FAILED" or decision is None or decision.disposition != "FAILURE_PENDING":
            raise TransitionError("EVIDENCE_MISMATCH")
        return self._proof(task, event, row, "definite_failure")

    @staticmethod
    def _proof(task, event, row, kind):
        return VerifiedTransition(
            task.id,
            task.agent_id,
            task.agent_version,
            task.external_submission_id,
            kind,
            row.id,
            event.protocol_version,
            upstream_id=event.upstream_task_id,
        )

    def _accepted(self, session, task, target, reference):
        if session.get(AgentEvent, reference) is None:
            return self.upstream._accepted(session, task, target, reference)
        row, event, _ = self._event(session, task, reference)
        return self._proof(task, event, row, "accepted")

    def install_verifiers(self, session, *, extra=None):
        session.info["transition_verifiers"] = TransitionVerifiers(
            {
                "accepted": self._accepted,
                "safe_retry": self.upstream._safe_retry,
                "original_result": self.verify_original_result,
                "definite_failure": self.verify_definite_failure,
                **(extra or {}),
            }
        )

    @staticmethod
    def _decision(session, task, row, disposition, lease):
        session.add(
            AgentEventDecision(
                event_ref=row.id,
                task_id=task.id,
                disposition=disposition,
                fencing_token=lease.fencing_token if lease else None,
                created_at=database_now(session),
            )
        )

    def reduce_pending(self, task_id, lease):
        self.import_observations(task_id, lease)
        progressed = False
        with self.factory() as session, session.begin():
            task = locked_execution(session, task_id, lease)
            prior_blocker = PENDING_CALLBACK_BLOCKERS.get(task.investigation_reason)
            self.install_verifiers(session)
            rows = session.scalars(
                select(AgentEvent)
                .where(AgentEvent.task_id == task.id)
                .order_by(AgentEvent.created_at, AgentEvent.id)
                .with_for_update()
            ).all()
            applied = []
            for row in rows:
                decision = session.get(AgentEventDecision, row.id, with_for_update=True)
                if decision and decision.disposition in {"APPLIED", "FAILURE_PENDING"}:
                    applied.append(row)
            for row in rows:
                if session.get(AgentEventDecision, row.id, with_for_update=True):
                    continue
                disposition = "APPLIED"
                conflict_reason = "EVENT_REPLAY_CONFLICT"
                latest = max(applied, key=lambda r: r.sequence) if applied else None
                if latest and row.sequence == latest.sequence:
                    disposition = (
                        "DUPLICATE" if row.semantic_digest == latest.semantic_digest else "CONFLICT"
                    )
                elif latest and row.sequence < latest.sequence:
                    disposition = "STALE"
                elif task.state in TERMINAL_STATES:
                    disposition = "TERMINAL_LATE"
                elif task.state in {"SAVING", "SAVE_RECOVERY"}:
                    disposition = "STALE" if row.sequence == 1 else "CONFLICT"
                if disposition == "APPLIED":
                    try:
                        _, event, binding = self._event(session, task, row.id)
                        if event.state == "RESULT_READY":
                            self._manifest(session, task, event, binding)
                        if task.state in {"SUBMITTED", "QUEUED"}:
                            transition_task(
                                session,
                                task.id,
                                task.state_version,
                                "SUBMITTING",
                                TransitionEvidence(lease),
                            )
                        if task.state != "RUNNING":
                            transition_task(
                                session,
                                task.id,
                                task.state_version,
                                "RUNNING",
                                TransitionEvidence(lease, row.id),
                            )
                        if event.state == "RESULT_READY":
                            transition_task(
                                session,
                                task.id,
                                task.state_version,
                                "SAVING",
                                TransitionEvidence(lease, row.id),
                            )
                            task.investigation_reason = None
                        elif event.state == "FAILED":
                            transition_task(
                                session,
                                task.id,
                                task.state_version,
                                "INVESTIGATING",
                                TransitionEvidence(lease),
                            )
                            task.investigation_reason = "UPSTREAM_FAILURE_PENDING_SETTLEMENT"
                            disposition = "FAILURE_PENDING"
                        else:
                            task.investigation_reason = None
                        applied.append(row)
                        progressed = True
                    except TransitionError as exc:
                        if str(exc) == "LEASE_LOST":
                            raise
                        disposition = "CONFLICT"
                        conflict_reason = str(exc) if str(exc) in {
                            "EVIDENCE_MISMATCH", "RESULT_MANIFEST_MISMATCH",
                            "RESULT_POLICY_UNAVAILABLE", "UPSTREAM_IDENTITY_CONFLICT",
                        } else "EVIDENCE_MISMATCH"
                if disposition in {"CONFLICT", "TERMINAL_LATE"}:
                    self._conflict(session, task,
                                   "TERMINAL_LATE" if disposition == "TERMINAL_LATE"
                                   else conflict_reason, row.id, row.semantic_digest)
                self._decision(session, task, row, disposition, lease)
                session.flush()
            # Historical rejection decisions remain immutable. Stop automatic
            # transport retries while allowing fresh receipts, save and failure
            # settlement, and explicitly selected historical repair to proceed.
            if task.state not in TERMINAL_STATES | {"SAVING", "SAVE_RECOVERY"} and not any(
                session.get(AgentEventDecision, row.id, with_for_update=True).disposition
                == "FAILURE_PENDING"
                for row in rows
            ):
                conflict = session.scalar(select(UpstreamEvidence.id).where(
                    UpstreamEvidence.task_id == task.id,
                    UpstreamEvidence.kind == "callback_conflict",
                ).limit(1))
                if conflict is not None:
                    if task.state in {"RUNNING", "SUBMITTING"}:
                        transition_task(session, task.id, task.state_version, "INVESTIGATING",
                                        TransitionEvidence(lease))
                    task.investigation_reason = "CALLBACK_EVENT_CONFLICT"
            if prior_blocker and not progressed and task.state not in (
                TERMINAL_STATES | {"SAVING", "SAVE_RECOVERY"}
            ):
                task.investigation_reason = prior_blocker
            if progressed and task.state == "RUNNING":
                # Match the existing lease-release/scheduler retry interval.
                # A RUNNING transition enqueues an immediately-ready new version;
                # fence that generation before commit so local callback progress
                # cannot indirectly trigger an immediate remote query.
                ready_at = database_now(session) + timedelta(seconds=30)
                task.recovery_due_at = ready_at
                rearm_outbox(session, task.id, "recover", ready_at=ready_at)
        return progressed

    def original_result(self, task_id):
        with self.factory() as session:
            task = session.get(GenerationTask, task_id)
            row = session.scalar(
                select(AgentEvent)
                .join(AgentEventDecision)
                .where(
                    AgentEvent.task_id == task_id,
                    AgentEventDecision.disposition == "APPLIED",
                    AgentEvent.sequence == 2,
                )
            )
            if row is None:
                return None
            _, event, binding = self._event(session, task, row.id)
            manifest = self._manifest(session, task, event, binding)
            return OriginalResult(
                row.id,
                task.id,
                task.agent_id,
                task.agent_version,
                binding.wire_agent_id,
                binding.protocol_version,
                task.external_submission_id,
                event.upstream_task_id,
                row.payload["identity"]["snapshot_digest"],
                manifest,
            )

    def pending_failure(self, task_id):
        with self.factory() as session:
            return session.scalar(
                select(AgentEvent.id)
                .join(AgentEventDecision)
                .where(
                    AgentEvent.task_id == task_id,
                    AgentEventDecision.disposition == "FAILURE_PENDING",
                )
            )

    def poll_original_task(self, task_id, *, lease=None):
        owned = lease is None
        lease = lease or self.upstream.leases.claim_task(task_id, "callback-poll:" + uuid4().hex)
        if lease is None:
            return self.upstream._view(task_id)
        try:
            progressed = self.reduce_pending(task_id, lease)
            view = self.upstream._view(task_id)
            if view.state in {"SAVING", "SAVE_RECOVERY"} or self.pending_failure(task_id):
                return view
            reason = getattr(view, "investigation_reason", None)
            if (view.state in TERMINAL_STATES or reason in PENDING_CALLBACK_BLOCKERS
                    or reason in {"CALLBACK_EVENT_CONFLICT", "UPSTREAM_NEEDS_INPUT"}):
                return view
            if progressed:
                return view
            self.upstream.recover_original_task(task_id, lease=lease)
            self.reduce_pending(task_id, lease)
            return self.upstream._view(task_id)
        finally:
            if owned:
                self.upstream.leases.release(lease)


router = APIRouter(prefix="/api/v1/agent-callbacks", tags=["agent-callbacks"])


@router.post(
    "/{agent_id}/{version}",
    status_code=202,
    response_model=EventReceipt,
    operation_id="receive_agent_callback",
    responses={
        403: {"description": "Unverified or disabled protocol"},
        409: {"description": "Identity or replay conflict"},
        413: {"description": "Callback too large"},
    },
    openapi_extra={
        "parameters": [
            {
                "name": "X-Mock-Signature",
                "in": "header",
                "required": True,
                "schema": {"type": "string"},
                "description": "TEST_ONLY mock-v1 raw-body HMAC-SHA256",
            }
        ],
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"type": "string", "format": "binary"},
                    "description": "Exact signed mock-v1 event bytes; no caller-verified DTO",
                }
            },
        },
    },
)
async def receive_callback(agent_id: UUID, version: str, request: Request):
    from app.agents.upstream import UpstreamService

    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_BODY:
            raise HTTPException(413)
    settings = request.app.state.settings
    if request.app.state.engine is None:
        raise HTTPException(503)
    service = CallbackService(
        UpstreamService(
            sessionmaker(request.app.state.engine, expire_on_commit=False),
            AgentRegistry.from_settings(settings),
        )
    )
    receipt = service.receive_callback(str(agent_id), version, bytes(raw), request.headers)
    if receipt.status in {"CONFLICT", "REJECTED"}:
        raise HTTPException(409)
    return receipt
