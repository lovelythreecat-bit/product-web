"""Caller-owned manual settlement; recovery I/O is queued and runs without resource locks."""

from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.agents.callbacks import CallbackService
from app.agents.models import AgentEventDecision
from app.audit.models import AuditEvent
from app.auth.models import User
from app.catalog.service import CatalogService
from app.common.types import Principal
from app.dispatch.consumer import Lease
from app.dispatch.outbox import enqueue_outbox
from app.dispatch.recovery import TERMINAL_STATES, database_now
from app.investigations.models import Investigation, InvestigationAlert, Resolution
from app.ledger.service import lock_task_resources, release_credits
from app.policies.schemas import InvestigationPolicy
from app.policies.service import PolicyGateError, PolicyService
from app.tasks.models import GenerationTask, TaskSnapshot, TaskStateEvent
from app.tasks.state_machine import TransitionError, TransitionEvidence, VerifiedTransition


class InvestigationService:
    def __init__(self, factory, *, upstream, mode="mock"):
        self.factory, self.upstream, self.mode = factory, upstream, mode
        self._scan_cursor = ""

    def policy(self, session, version):
        policies = PolicyService(session)
        policies.require_feature("investigations", self.mode, {"D-08": version})
        return InvestigationPolicy.model_validate(
            policies._read("D-08", version).payload["investigations"]
        )

    def _authorize(self, session, actor, task_id, *, extra_users=()):
        identity = session.get(GenerationTask, str(task_id))
        if identity is None:
            raise HTTPException(404)
        # Always lock every user in sorted order before sessions, credits, capacity or task.
        ids = sorted({str(actor.user_id), identity.user_id, *map(str, extra_users)})
        for uid in ids:
            session.scalar(
                select(User)
                .where(User.id == uid)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        CatalogService(session)._principal(actor, admin=True)
        return lock_task_resources(session, task_id)[0]

    @staticmethod
    def _allowed(policy, actor, action=None):
        if actor.user_id not in policy.authorized_actor_ids or (
            action is not None and action not in policy.actions
        ):
            raise HTTPException(403)

    def open_investigation(self, session, actor, task_id, owner, policy_version, evidence):
        task = self._authorize(session, actor, task_id, extra_users=[owner])
        policy = self.policy(session, policy_version)
        self._allowed(policy, actor)
        if str(owner) != str(policy.responsible_user_id):
            raise HTTPException(403)
        responsible = session.get(User, str(owner))
        if responsible is None or responsible.status != "active" or responsible.role != "admin":
            raise HTTPException(409)
        case = session.get(Investigation, task.id, with_for_update=True)
        if case:
            if (case.owner, case.policy_version, case.evidence) != (
                str(owner),
                policy_version,
                evidence,
            ):
                raise HTTPException(409)
            return case
        if task.state not in {"INVESTIGATING", "SAVE_RECOVERY"}:
            raise HTTPException(409)
        current = database_now(session)
        case = Investigation(
            task_id=task.id,
            owner=str(owner),
            policy_version=policy_version,
            evidence=evidence,
            status="open",
            version=1,
            created_at=current,
            deadline_at=current + timedelta(seconds=policy.deadline_seconds),
        )
        session.add(case)
        self.audit(
            session,
            actor,
            task.id,
            "open",
            "Investigation assigned",
            dict(owner=str(owner), policy_version=policy_version, evidence=evidence),
        )
        session.flush()
        return case

    def assign(self, session, actor, task_id, dto):
        task = self._authorize(session, actor, task_id, extra_users=[dto.owner])
        case = session.get(Investigation, task.id, with_for_update=True)
        if case is None:
            raise HTTPException(404)
        if case.version != dto.expected_version or case.status == "resolved":
            raise HTTPException(409)
        self._allowed(self.policy(session, case.policy_version), actor)
        policy = self.policy(session, dto.policy_version)
        self._allowed(policy, actor)
        responsible = session.get(User, str(dto.owner))
        if (
            str(dto.owner) != str(policy.responsible_user_id)
            or responsible is None
            or responsible.status != "active"
            or responsible.role != "admin"
        ):
            raise HTTPException(403)
        self.audit(
            session,
            actor,
            task.id,
            "assign",
            dto.reason,
            dict(
                before_version=case.version,
                after_version=case.version + 1,
                old_owner=case.owner,
                owner=str(dto.owner),
                old_policy=case.policy_version,
                policy_version=dto.policy_version,
                evidence=dto.evidence,
            ),
        )
        case.owner, case.policy_version, case.evidence = (
            str(dto.owner),
            dto.policy_version,
            dto.evidence,
        )
        case.version += 1
        session.flush()
        return case

    def resolve_investigation(self, session, actor, task_id, dto, *, publisher=None, prepared=None):
        task = self._authorize(session, actor, task_id)
        policy = self.policy(session, dto.policy_version)
        self._allowed(policy, actor, dto.action)
        case = session.get(Investigation, task.id, with_for_update=True)
        if case is None:
            raise HTTPException(404)
        if case.policy_version != dto.policy_version:
            raise PolicyGateError()
        if (
            case.version != dto.expected_version
            or case.status == "resolved"
            or task.state in TERMINAL_STATES
        ):
            raise HTTPException(409)
        if dto.evidence.kind not in policy.evidence_types:
            raise HTTPException(403)
        owner = session.get(User, task.user_id)
        if owner.status != "active":
            snapshot = session.get(TaskSnapshot, task.id)
            PolicyService(session).require_feature(
                "account_disable", self.mode, snapshot.policy_versions
            )
        current = database_now(session)
        if task.lease_expires_at and task.lease_expires_at > current:
            from app.dispatch.consumer import lease_matches

            if prepared is None or not lease_matches(task, prepared.lease, current):
                raise HTTPException(409)
        if dto.action == "settle" and (
            publisher is None or prepared is None or dto.evidence.kind != "durable_delivery"
        ):
            raise TransitionError("PUBLICATION_REQUIRED")
        row = Resolution(
            id=str(uuid4()),
            task_id=task.id,
            actor_id=str(actor.user_id),
            session_id=str(actor.session_id),
            action=dto.action,
            policy_version=dto.policy_version,
            evidence=dto.evidence.model_dump(),
            reason=dto.reason,
            before_version=case.version,
            after_version=case.version + 1,
            task_version=task.state_version,
            outcome="pending",
            created_at=current,
        )
        session.add(row)
        self.audit(
            session,
            actor,
            task.id,
            dto.action,
            dto.reason,
            dict(
                before_version=case.version,
                after_version=case.version + 1,
                task_before_version=task.state_version,
                resolution_id=row.id,
                policy_version=case.policy_version,
                previous_investigation_reason=task.investigation_reason,
                evidence=dto.evidence.model_dump(),
            ),
        )
        session.flush()
        if dto.action == "resume_original":
            case.status = "recovery_pending"
            row.outcome = "recovery_scheduled"
            enqueue_outbox(session, task.id, "save" if task.state == "SAVE_RECOVERY" else "recover")
        elif dto.action == "settle":
            from app.results.publisher import publish_and_settle

            publisher.install_verifiers(session, prepared)
            publish_and_settle(session, task.id, prepared.delivery.manifest_id, task.state_version)
            row.evidence = dict(row.evidence, manifest_id=prepared.delivery.manifest_id)
            case.status, row.outcome = "resolved", "SUCCEEDED"
        else:
            if dto.action == "manual_close" and dto.evidence.kind != "review":
                raise TransitionError("EVIDENCE_REQUIRED")
            if dto.action == "confirm_failure" and dto.evidence.kind != "upstream_failure":
                raise TransitionError("EVIDENCE_REQUIRED")
            task.fencing_token += 1
            task.lease_owner = "investigation:" + row.id
            task.lease_expires_at = current + timedelta(seconds=60)
            lease = Lease(task.id, task.lease_owner, task.fencing_token, task.lease_expires_at)
            session.flush()
            CallbackService(self.upstream).install_verifiers(
                session, extra={"manual_close": self.verify_manual_close}
            )
            reference = row.id if dto.action == "manual_close" else dto.evidence.reference
            release_credits(
                session,
                task.id,
                TransitionEvidence(lease, reference),
                manual_close=dto.action == "manual_close",
            )
            if dto.action == "manual_close":
                from app.storage.models import CapacityReservation

                capacity = session.get(CapacityReservation, task.capacity_reservation_id)
                row.evidence = dict(
                    row.evidence,
                    capacity_reservation_id=capacity.id,
                    protected_bytes=capacity.estimated_bytes
                    if capacity.state == "reserved"
                    else capacity.actual_bytes,
                )
            task.lease_owner, task.lease_expires_at = None, None
            case.status = "resolved"
            row.outcome = task.state
        case.version += 1
        case.user_reason = dto.reason
        task.investigation_reason = case.user_reason
        row.task_version = task.state_version
        session.flush()
        return row

    @staticmethod
    def audit(session, actor, task_id, action, reason, changes):
        session.add(
            AuditEvent(
                id=str(uuid4()),
                actor_id=str(actor.user_id),
                action="investigation." + action,
                object_id=task_id,
                reason=reason,
                changes=changes,
                created_at=database_now(session),
            )
        )

    def preflight_settlement(self, session, actor, task_id, dto):
        task = self._authorize(session, actor, task_id)
        policy = self.policy(session, dto.policy_version)
        self._allowed(policy, actor, "settle")
        case = session.get(Investigation, task.id, with_for_update=True)
        if (
            case is None
            or case.version != dto.expected_version
            or case.policy_version != dto.policy_version
            or case.status == "resolved"
            or dto.evidence.kind != "durable_delivery"
            or task.state in TERMINAL_STATES
        ):
            raise TransitionError("PUBLICATION_REQUIRED")
        if session.get(User, task.user_id).status != "active":
            PolicyService(session).require_feature(
                "account_disable", self.mode, session.get(TaskSnapshot, task.id).policy_versions
            )

    def verify_manual_close(self, session, task, target, reference):
        row = session.get(Resolution, reference, with_for_update=True)
        case = session.get(Investigation, task.id, with_for_update=True)
        if (
            row is None
            or case is None
            or row.task_id != task.id
            or row.action != "manual_close"
            or target != "MANUALLY_CLOSED"
            or row.policy_version != case.policy_version
            or not row.reason.strip()
            or row.evidence.get("kind") != "review"
            or row.before_version != case.version
            or row.outcome != "pending"
        ):
            raise TransitionError("EVIDENCE_REQUIRED")
        policy = self.policy(session, row.policy_version)
        actor = Principal(
            user_id=row.actor_id,
            session_id=row.session_id,
            role="admin",
            auth_version=session.get(User, row.actor_id).auth_version,
        )
        CatalogService(session)._principal(actor, admin=True)
        self._allowed(policy, actor, "manual_close")
        return VerifiedTransition(
            task.id,
            task.agent_id,
            task.agent_version,
            task.external_submission_id,
            "manual_close",
            row.id,
            policy.schema_version,
            upstream_id=task.upstream_id,
        )

    @staticmethod
    def alert(session, task, kind, escalation, reference=None, disposition="pending"):
        key = f"{kind}:{task.id}:{reference or 'task'}"
        if session.get(InvestigationAlert, key) is None:
            session.add(
                InvestigationAlert(
                    key=key,
                    task_id=task.id,
                    kind=kind,
                    escalation_ref=escalation,
                    evidence_ref=reference,
                    disposition=disposition,
                    created_at=database_now(session),
                )
            )

    def scan(self, task_ids=None):
        """Bounded operational sweep; no upstream I/O, money change or automatic failure."""
        with self.factory() as session:
            query = select(GenerationTask.id).where(
                GenerationTask.state.in_(["INVESTIGATING", "SAVE_RECOVERY", *TERMINAL_STATES])
            )
            if task_ids is not None:
                query = query.where(GenerationTask.id.in_(task_ids))
            else:
                query = query.where(GenerationTask.id > self._scan_cursor)
            ids = session.scalars(query.order_by(GenerationTask.id).limit(1000)).all()
        if task_ids is None:
            self._scan_cursor = ids[-1] if len(ids) == 1000 else ""
        for task_id in ids:
            with self.factory() as session, session.begin():
                # Read immutable identities first; lock every candidate user in UUID order.
                identity = session.get(GenerationTask, task_id)
                initial_case = session.get(Investigation, task_id)
                snapshot = session.get(TaskSnapshot, task_id)
                version = (
                    initial_case.policy_version
                    if initial_case
                    else snapshot.policy_versions.get("D-08")
                )
                try:
                    initial_policy = self.policy(session, version)
                except PolicyGateError:
                    initial_policy = None
                candidate = (
                    initial_case.owner
                    if initial_case
                    else str(initial_policy.responsible_user_id)
                    if initial_policy
                    else None
                )
                for uid in sorted({identity.user_id, *([candidate] if candidate else [])}):
                    session.scalar(
                        select(User)
                        .where(User.id == uid)
                        .with_for_update()
                        .execution_options(populate_existing=True)
                    )
                task, _, _ = lock_task_resources(session, task_id)
                case = session.scalar(
                    select(Investigation)
                    .where(Investigation.task_id == task_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                if case is None:
                    responsible = session.get(User, candidate) if candidate else None
                    if task.state not in TERMINAL_STATES:
                        if (
                            initial_policy
                            and responsible
                            and responsible.status == "active"
                            and responsible.role == "admin"
                        ):
                            started = (
                                session.scalar(
                                    select(TaskStateEvent.created_at)
                                    .where(
                                        TaskStateEvent.task_id == task.id,
                                        TaskStateEvent.to_state.in_(
                                            ["INVESTIGATING", "SAVE_RECOVERY"]
                                        ),
                                    )
                                    .order_by(TaskStateEvent.state_version)
                                    .limit(1)
                                )
                                or task.created_at
                            )
                            case = Investigation(
                                task_id=task.id,
                                owner=candidate,
                                policy_version=version,
                                evidence="task:" + task.id,
                                status="open",
                                version=1,
                                created_at=database_now(session),
                                deadline_at=started
                                + timedelta(seconds=initial_policy.deadline_seconds),
                            )
                            session.add(case)
                            session.add(
                                AuditEvent(
                                    id=str(uuid4()),
                                    actor_id=None,
                                    action="investigation.auto_assign",
                                    object_id=task.id,
                                    reason="Exact task policy responsibility",
                                    changes=dict(owner=candidate, policy_version=version),
                                    created_at=database_now(session),
                                )
                            )
                            session.flush()
                        else:
                            self.alert(
                                session,
                                task,
                                "UNASSIGNED",
                                initial_policy.escalation_ref
                                if initial_policy
                                else "operations:investigations",
                            )
                    if case is None:
                        continue
                try:
                    policy = self.policy(session, case.policy_version)
                except PolicyGateError:
                    self.alert(session, task, "POLICY_BLOCKED", "operations:investigations")
                    continue
                responsible = session.get(User, case.owner) if case.owner else None
                if not responsible or responsible.status != "active" or responsible.role != "admin":
                    self.alert(session, task, "UNASSIGNED", policy.escalation_ref)
                if case.status != "resolved" and case.deadline_at <= database_now(session):
                    case.status = "overdue"
                    self.alert(session, task, "OVERDUE", policy.escalation_ref)
                for decision in session.scalars(
                    select(AgentEventDecision).where(
                        AgentEventDecision.task_id == task.id,
                        AgentEventDecision.disposition == "TERMINAL_LATE",
                    )
                ):
                    self.alert(
                        session,
                        task,
                        "LATE_RESULT",
                        policy.escalation_ref,
                        decision.event_ref,
                        policy.late_delivery,
                    )


def complete_from_task(session, task, evidence):
    """Close any outstanding investigation in the same trusted terminal transaction."""
    case = session.get(Investigation, task.id, with_for_update=True)
    if case is None or case.status == "resolved":
        return
    manual = session.scalar(
        select(Resolution.id).where(
            Resolution.task_id == task.id,
            Resolution.before_version == case.version,
            Resolution.outcome == "pending",
        )
    )
    if manual is not None:
        return  # The caller finishes its same-transaction manual resolution and reason.
    before = case.version
    previous_reason = task.investigation_reason
    case.version += 1
    case.status = "resolved"
    case.user_reason = (
        "原任务已完成保存并结算。"
        if task.state == "SUCCEEDED"
        else "原任务已确认失败并释放冻结积分。"
    )
    task.investigation_reason = case.user_reason
    session.add(
        AuditEvent(
            id=str(uuid4()),
            actor_id=None,
            action="investigation.recovered",
            object_id=task.id,
            reason=case.user_reason,
            changes=dict(
                before_version=before,
                after_version=case.version,
                task_version=task.state_version,
                state=task.state,
                previous_investigation_reason=previous_reason,
                evidence=evidence.reference,
            ),
            created_at=database_now(session),
        )
    )
