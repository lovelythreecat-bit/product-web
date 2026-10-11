"""One short caller-owned MySQL admission transaction; no upstream/Redis calls.

Lock order: user -> auth session -> idempotency lookup (replay ends here);
new intent: conversation/product -> catalog heads -> exact policies -> credits ->
capacity pool/account -> existing in-flight tasks -> capacity reservation -> NEW
task INSERT -> credit reservation -> files (sorted IDs) -> outbox/events.
The absent-key lookup has no existing task to lock; the route retries only MySQL
deadlocks before commit. Existing
task execution in T08/T12 must lock capacity before task, then reservations.
"""

import hashlib
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from app.catalog.schemas import content_digest
from app.catalog.service import CatalogService
from app.common.types import AdmissionResult, SubmitTaskRequest
from app.conversations.models import Message, ProductVersion
from app.conversations.service import authenticate, owned_conversation
from app.dispatch.outbox import enqueue_outbox
from app.events.service import append_durable_event
from app.ledger.service import LedgerError, freeze_credits, locked_account, now
from app.policies.schemas import ConcurrencyPolicy, StoragePolicy
from app.policies.service import PolicyGateError, PolicyService
from app.storage.capacity import lock_capacity, reserve_capacity
from app.storage.local_store import LocalStore
from app.storage.models import File, FileRef
from app.storage.schemas import capacity_policy
from app.tasks.models import GenerationTask, TaskSnapshot, TaskStateEvent
from app.tasks.repository import task_view
from app.tasks.schemas import GenerationEstimate

TERMINAL_STATES = ("SUCCEEDED", "FAILED", "MANUALLY_CLOSED")


class AdmissionService:
    def __init__(self, session, settings):
        self.session, self.settings = session, settings

    def admit_task(self, principal, key, request):
        session, settings = self.session, self.settings
        authenticate(session, principal)
        if (
            not isinstance(key, str)
            or not 1 <= len(key) <= 128
            or not key.isascii()
            or any(ord(c) <= 32 or ord(c) >= 127 for c in key)
        ):
            raise HTTPException(422)
        request = SubmitTaskRequest.model_validate(request.model_dump())
        try:
            request_hash = content_digest(request.model_dump(mode="json"))
        except (ValueError, TypeError):
            raise HTTPException(422) from None
        user_id = str(principal.user_id)
        existing = session.scalar(
            select(GenerationTask)
            .where(GenerationTask.user_id == user_id, GenerationTask.idempotency_key == key)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if existing:
            if existing.request_hash != request_hash:
                raise LedgerError()
            return AdmissionResult(task=task_view(session, existing), replayed=True)

        owned_conversation(session, user_id, request.conversation_id)
        product = session.scalar(
            select(ProductVersion)
            .where(
                ProductVersion.version == request.input.product_version,
                ProductVersion.user_id == user_id,
            )
            .with_for_update(read=True)
        )
        if product is None:
            raise HTTPException(404)
        if content_digest(product.product) != content_digest(request.input.product):
            raise HTTPException(422)
        validated = CatalogService(session, mode=settings.mode).validate_confirmed_quote(
            request.confirmed_quote, request.input
        )
        if validated.agent.agent_id != request.agent_id:
            raise HTTPException(422)
        if settings.test_only != (settings.mode == "mock"):
            raise PolicyGateError()
        policies = PolicyService(session)
        versions = dict(settings.generation_policy_versions)
        # Agent protocol/input contracts stay bound to the catalog's exact version.
        for decision in ("D-01", "D-03"):
            bound = validated.agent.policy_versions.get(decision)
            if bound:
                if decision in versions and versions[decision] != bound:
                    raise PolicyGateError()
                versions[decision] = bound
        receipt = policies.require_feature(
            f"agent.{request.agent_id}.generation", settings.mode, versions
        )
        protocol = policies._read("D-01", versions["D-01"]).payload["agents"][str(request.agent_id)]
        if protocol["protocol_version"] != validated.agent.protocol_version:
            raise PolicyGateError()
        concurrency = ConcurrencyPolicy.model_validate(
            policies._read("D-05", versions["D-05"]).payload["generation"]
        )
        storage = StoragePolicy.model_validate(
            policies._read("D-10", versions["D-10"]).payload["generation"]
        )
        try:
            estimate = GenerationEstimate.model_validate(
                settings.generation_capacity_estimates[str(validated.spec.spec_id)]
            )
        except (KeyError, ValidationError):
            raise PolicyGateError() from None
        if (estimate.spec_version, estimate.policy_version, estimate.estimation_ref) != (
            validated.spec.version,
            versions["D-10"],
            storage.estimation_ref,
        ) or not settings.storage_persistent:
            raise PolicyGateError()
        account = locked_account(session, user_id)
        if account.available < validated.quote.credits:
            raise LedgerError("INSUFFICIENT_CREDITS", 402)
        store = LocalStore(settings.storage_root)
        store.require_space(estimate.total_bytes)
        task_id = str(uuid4())
        capacity_rules = capacity_policy(session, versions["D-10"], settings.mode)
        lock_capacity(session, user_id, settings.mode, capacity_rules, versions["D-10"])
        # Current locking read after pool/account locks; user serialization protects
        # the count even at MySQL REPEATABLE READ with an older auth snapshot.
        inflight = session.scalars(
            select(GenerationTask.id)
            .where(GenerationTask.user_id == user_id, GenerationTask.state.not_in(TERMINAL_STATES))
            .with_for_update()
        ).all()
        if len(inflight) >= concurrency.max_concurrent_tasks:
            raise HTTPException(429)
        capacity = reserve_capacity(
            session,
            user_id,
            "generation:" + task_id,
            estimate.total_bytes,
            versions["D-10"],
            mode=settings.mode,
        )
        row = GenerationTask(
            id=task_id,
            user_id=user_id,
            conversation_id=str(request.conversation_id),
            idempotency_key=key,
            request_hash=request_hash,
            agent_id=str(request.agent_id),
            agent_version=validated.agent.version,
            external_submission_id=str(uuid4()),
            state="SUBMITTED",
            state_version=1,
            settlement_state="FROZEN",
            capacity_reservation_id=capacity.id,
            fencing_token=0,
            created_at=now(),
        )
        session.add(row)
        session.flush()
        session.add(
            TaskSnapshot(
                task_id=task_id,
                user_id=user_id,
                product_version=product.version,
                input_snapshot=request.input.model_dump(mode="json"),
                agent_snapshot=validated.agent.model_dump(mode="json"),
                spec_snapshot=validated.spec.model_dump(mode="json"),
                price_snapshot=validated.price.model_dump(mode="json"),
                quote=validated.quote.model_dump(mode="json"),
                policy_versions=receipt.decision_versions,
                capacity_estimate=estimate.model_dump(mode="json"),
            )
        )
        session.flush()
        freeze_credits(session, user_id, task_id, validated.quote.credits)
        material_ids = [(str(ref.file_id), ref.version) for ref in request.input.material_versions]
        if len(set(material_ids)) != len(material_ids):
            raise HTTPException(422)
        for file_id, version in sorted(material_ids):
            file = session.scalar(
                select(File)
                .where(
                    File.id == file_id,
                    File.version == version,
                    File.user_id == user_id,
                    File.deleted_at.is_(None),
                    File.state == "durable",
                )
                .with_for_update()
            )
            if file is None:
                raise HTTPException(404)
            try:
                digest, size = hashlib.sha256(), 0
                with store.read(file.internal_path) as stream:
                    while chunk := stream.read(65536):
                        size += len(chunk)
                        if size > file.actual_bytes:
                            raise HTTPException(422)
                        digest.update(chunk)
                if size != file.actual_bytes or digest.hexdigest() != file.sha256:
                    raise HTTPException(422)
            except OSError:
                raise HTTPException(422) from None
            session.add(
                FileRef(
                    id=str(uuid4()),
                    file_id=file_id,
                    version=version,
                    user_id=user_id,
                    ref_type="task_input",
                    ref_id=task_id,
                    created_at=now(),
                )
            )
        session.add(
            Message(
                id=str(uuid4()),
                user_id=user_id,
                conversation_id=row.conversation_id,
                task_id=task_id,
                kind="authored",
                role="user",
                content={"instruction": request.input.instruction},
                created_at=now(),
            )
        )
        session.add(
            TaskStateEvent(
                id=str(uuid4()),
                task_id=task_id,
                user_id=user_id,
                state_version=1,
                from_state=None,
                to_state="SUBMITTED",
                evidence={"kind": "admission"},
                created_at=now(),
            )
        )
        session.flush()
        enqueue_outbox(session, task_id, "submit")
        append_durable_event(
            session,
            user_id,
            "task.updated",
            {
                "task_id": task_id,
                "state": "SUBMITTED",
                "state_version": 1,
            },
            event_key="task:" + task_id + ":1",
        )
        return AdmissionResult(task=task_view(session, row), replayed=False)
