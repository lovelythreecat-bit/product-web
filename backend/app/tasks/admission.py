"""Caller-owned admission transaction; remote text metadata is read before any freeze.

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


class MaterialUnavailable(Exception):
    """Owned original material needs an explicit reupload and new quote."""

    def __init__(self, status_code=404):
        self.status_code = status_code


TERMINAL_STATES = ("SUCCEEDED", "FAILED", "MANUALLY_CLOSED")


class AdmissionService:
    def __init__(self, session, settings):
        self.session, self.settings = session, settings

    def admit_task(self, principal, key, request, *, free_regeneration=False,
                   regeneration_metadata=None):
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
            hash_input = request.model_dump(mode="json")
            if request.regeneration is None:
                # Preserve replay hashes for requests admitted before this field existed.
                hash_input.pop("regeneration", None)
            if free_regeneration:
                # This entitlement is supplied only by locked server-owned workflows.
                # Bind it to replay identity while retaining the original paid request.
                hash_input = {"request": hash_input, "free_regeneration": True}
            request_hash = content_digest(hash_input)
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
        # Always validate the full current catalog price before applying a server
        # entitlement. The actual quote, price and reservation must settle equally.
        billing_quote = validated.quote
        billing_price = validated.price.model_dump(mode="json")
        if request.regeneration is not None:
            from app.tasks.regeneration import RegenerationService

            if free_regeneration or regeneration_metadata is not None:
                raise HTTPException(422)
            decision = RegenerationService(session, settings).confirm(
                principal, request.regeneration, request.agent_id, request.input,
                billing_quote.credits,
            )
            free_regeneration = decision.free
            regeneration_metadata = decision.metadata
        if regeneration_metadata is not None:
            billing_price["regeneration"] = regeneration_metadata
        if free_regeneration:
            billing_price["standard_quote"] = billing_quote.model_dump(mode="json")
            billing_price["credits"] = 0
            billing_quote = billing_quote.model_copy(update={"credits": 0})
        routing_snapshot = None
        from app.agents.text import PROTOCOL as TEXT_PROTOCOL

        if validated.agent.protocol_version == TEXT_PROTOCOL:
            from app.agents.registry import AgentRegistry
            from app.agents.text import TextAgentRouting, build_copy_request
            from app.catalog.models import AgentRecord

            try:
                agent_record = session.get(
                    AgentRecord, (str(validated.agent.agent_id), validated.agent.version)
                )
                binding = AgentRegistry.from_settings(settings).bind_version(
                    agent_record, session=session,
                )
                if validated.spec.delivery_kind != "single":
                    raise ValueError("Text service returns a single result")
                if request.input.material_versions and not binding.adapter.profile.supports_images:
                    from app.agents.model_configs import TextModelError

                    raise TextModelError(422, public_message=(
                        "当前默认文本模型不支持图片，请移除商品图片或更换默认模型。"
                    ))
                build_copy_request({"input_snapshot": request.input.model_dump(mode="json")},
                                   binding.adapter.profile, validate_only=True)
                profile = binding.adapter.profile
                from app.agents.text_runtime import DATABASE_PROFILE

                routing_snapshot = TextAgentRouting(
                    profile=DATABASE_PROFILE, base_url=profile.base_url,
                    model_config_id=profile.model_config_id,
                    supports_images=profile.supports_images,
                ).model_dump(mode="json")
            except LookupError:
                raise PolicyGateError() from None
            except (ValueError, TypeError, KeyError):
                raise HTTPException(422) from None
        media_kind = None
        if validated.agent.protocol_version in {"image-agent-v1", "video-agent-v1"}:
            from app.agents.media_connection import read_media_connection
            from app.agents.media_execution import validate_media_input
            from app.agents.registry import AgentRegistry
            from app.catalog.models import AgentRecord

            media_kind = validated.agent.kind
            try:
                validate_media_input(media_kind, request.input)
                connection = read_media_connection(session, settings, media_kind)
                agent_record = session.get(AgentRecord, (str(validated.agent.agent_id),
                                                         validated.agent.version))
                binding = AgentRegistry.from_settings(settings).bind_version(
                    agent_record, session=session)
                route = dict(protocol_version=validated.agent.protocol_version,
                             connection_id=str(connection.id), base_url=connection.base_url)
                if media_kind == "image":
                    from app.agents.image import build_image_request

                    build_image_request({"input_snapshot": request.input.model_dump(mode="json")},
                                        binding.adapter.profile, validate_only=True)
                    route.update(agent_config_id=str(connection.default_config_id),
                                 image_model=connection.image_model)
                else:
                    from app.agents.video import build_video_request

                    build_video_request({"input_snapshot": request.input.model_dump(mode="json")},
                                        validate_only=True)
                    route["video_audio_enabled"] = connection.video_audio_enabled
                routing_snapshot = route
            except LookupError:
                raise PolicyGateError() from None
            except (ValueError, TypeError, KeyError):
                raise HTTPException(422) from None
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
        if media_kind == "image" and request.input.parameters["output_type"] == "detail_page":
            # Billing includes all three images; delivery still needs its own
            # confirmed complete-delivery/partial-failure policy.
            delivery_version = versions.get("D-04")
            if delivery_version is None:
                raise PolicyGateError()
            delivery_record = policies._read("D-04", delivery_version)
            from app.policies.schemas import DeliveryPolicy

            try:
                if (delivery_record.mode != settings.mode
                        or settings.mode != "mock" and delivery_record.status != "confirmed"):
                    raise ValueError()
                DeliveryPolicy.model_validate(
                    delivery_record.payload["specs"][str(validated.agent.agent_id)])
            except (ValueError, KeyError, TypeError):
                raise PolicyGateError() from None
            receipt.decision_versions["D-04"] = delivery_version
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
        if media_kind is not None:
            routing_snapshot["max_result_bytes"] = min(estimate.total_bytes,
                                                       storage.max_download_bytes)
        account = locked_account(session, user_id)
        if account.available < billing_quote.credits:
            raise LedgerError("INSUFFICIENT_CREDITS", 402)
        store = LocalStore(settings.storage_root)
        store.require_space(estimate.total_bytes)
        task_id = str(uuid4())
        capacity_rules = capacity_policy(session, versions["D-10"], settings.mode)
        lock_capacity(session, user_id, settings.mode, capacity_rules, versions["D-10"])
        # Current locking read after pool/account locks; user serialization protects
        # the count even at MySQL REPEATABLE READ with an older auth snapshot.
        if concurrency.max_concurrent_tasks is not None:
            inflight = session.scalars(
                select(GenerationTask.id)
                .where(GenerationTask.user_id == user_id,
                       GenerationTask.state.not_in(TERMINAL_STATES))
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
            free_bytes=store.free_bytes,
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
        if media_kind is not None:
            from app.agents.media_execution import new_execution

            execution = new_execution(task_id, media_kind)
            execution.state = {"user_id": user_id}
            session.add(execution)
        session.add(
            TaskSnapshot(
                task_id=task_id,
                user_id=user_id,
                product_version=product.version,
                input_snapshot=request.input.model_dump(mode="json"),
                agent_snapshot=validated.agent.model_dump(mode="json"),
                routing_snapshot=routing_snapshot,
                spec_snapshot=validated.spec.model_dump(mode="json"),
                price_snapshot=billing_price,
                quote=billing_quote.model_dump(mode="json"),
                policy_versions=receipt.decision_versions,
                capacity_estimate=estimate.model_dump(mode="json"),
            )
        )
        session.flush()
        freeze_credits(session, user_id, task_id, billing_quote.credits)
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
                )
                .with_for_update()
            )
            if file is None:
                raise HTTPException(404)
            if file.deleted_at is not None or file.state != "durable":
                raise MaterialUnavailable()
            text_material = validated.agent.protocol_version == TEXT_PROTOCOL
            if media_kind is not None and (
                file.actual_bytes > 20 * 1024 * 1024
                or file.actual_mime not in {"image/png", "image/jpeg", "image/webp"}
            ):
                raise HTTPException(422)
            if text_material:
                from app.agents.text import MAX_IMAGE_BYTES

                if (file.actual_bytes > MAX_IMAGE_BYTES
                        or file.actual_mime not in {"image/png", "image/jpeg", "image/webp"}):
                    raise HTTPException(422)
            try:
                digest, size = hashlib.sha256(), 0
                text_bytes = bytearray()
                with store.read(file.internal_path) as stream:
                    while chunk := stream.read(65536):
                        size += len(chunk)
                        if size > file.actual_bytes:
                            raise MaterialUnavailable(422)
                        digest.update(chunk)
                        if text_material:
                            text_bytes.extend(chunk)
                if size != file.actual_bytes or digest.hexdigest() != file.sha256:
                    raise MaterialUnavailable(422)
                if text_material:
                    from app.agents.text import validate_text_image

                    try:
                        validate_text_image(bytes(text_bytes), file.actual_mime)
                    except ValueError:
                        raise HTTPException(422) from None
            except OSError:
                raise MaterialUnavailable(422) from None
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
