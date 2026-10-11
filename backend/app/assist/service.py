"""Short authoritative reads around a provider call; never persists a generation intent."""

import asyncio

from fastapi import HTTPException
from sqlalchemy import select

from app.assist.models import AssistRecord
from app.assist.provider import (
    TEST_SCHEME,
    MockPromptAssistProvider,
    ProviderRequest,
    ProviderResponse,
)
from app.assist.schemas import AssistProposal, AssistRequest
from app.catalog.schemas import content_digest
from app.catalog.service import CatalogService
from app.conversations.service import authenticate
from app.ledger.service import now
from app.policies.schemas import AssistPolicy
from app.policies.service import PolicyGateError, PolicyService
from app.storage.models import File


class AssistService:
    def __init__(self, session, settings):
        self.session, self.settings = session, settings

    def _context(self, principal, request, policy_version):
        session, settings = self.session, self.settings
        authenticate(session, principal)
        policies = PolicyService(session)
        policies.require_feature("prompt_assist", settings.mode, {"D-05": policy_version})
        policy = AssistPolicy.model_validate(
            policies._read("D-05", policy_version).payload["assist"]
        )
        # Only this explicitly documented simulation has implementation semantics.
        if (
            settings.mode != "mock"
            or not settings.test_only
            or settings.assist_provider != "deterministic_mock"
            or settings.assist_policy_version != policy_version
            or policy.scheme != "OTHER_CONFIRMED_SCHEME"
            or policy.policy_ref != TEST_SCHEME
            or policy.implementation_ref != TEST_SCHEME
        ):
            raise PolicyGateError()
        catalog = CatalogService(session, mode=settings.mode)
        spec, agent = catalog._current_spec(request.spec_id)
        catalog._agent_gate(agent)
        catalog._spec_gate(spec)
        if agent.agent_id != request.agent_id:
            raise HTTPException(422)
        if agent.version != request.agent_version or spec.version != request.spec_version:
            raise HTTPException(409)
        for name, value in request.parameters.items():
            rule = spec.parameter_schema.fields.get(name)
            if rule is None or not rule.accepts(value):
                raise HTTPException(422)
        refs = [(str(ref.file_id), ref.version) for ref in request.material_versions]
        if len(set(refs)) != len(refs):
            raise HTTPException(422)
        # Verify ownership first without disclosing whether another user's file exists.
        for file_id, version in sorted(refs):
            file = session.scalar(
                select(File)
                .where(
                    File.id == file_id,
                    File.version == version,
                    File.user_id == str(principal.user_id),
                    File.state == "durable",
                    File.deleted_at.is_(None),
                )
                .with_for_update(read=True)
                .execution_options(populate_existing=True)
            )
            if file is None:
                raise HTTPException(404)
        if len(refs) > agent.input_support.max_materials:
            raise HTTPException(422)
        return ProviderRequest(draft=request, agent=agent, spec=spec)

    def _replay(self, principal, key, request_hash):
        row = self.session.scalar(
            select(AssistRecord)
            .where(AssistRecord.user_id == str(principal.user_id), AssistRecord.request_key == key)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if row is None:
            return None
        if row.request_hash != request_hash:
            raise HTTPException(409)
        return AssistProposal.model_validate(row.response)

    def prepare_prompt(self, principal, request, policy_version, *, key, before_provider=None):
        request = AssistRequest.model_validate(request.model_dump())
        if (
            not isinstance(key, str)
            or not 1 <= len(key) <= 128
            or any(ord(c) <= 32 or ord(c) >= 127 for c in key)
        ):
            raise HTTPException(422)
        request_hash = content_digest(request.model_dump(mode="json"))
        # Release every lock and return the connection before external work.
        try:
            context = self._context(principal, request, policy_version)
            replay = self._replay(principal, key, request_hash)
            if replay is not None:
                return replay
        finally:
            self.session.rollback()
        if before_provider is not None:
            before_provider()

        async def invoke():
            return await asyncio.wait_for(
                MockPromptAssistProvider().prepare(context),
                timeout=self.settings.assist_timeout_seconds,
            )

        try:
            response = ProviderResponse.model_validate(asyncio.run(invoke()))
        except TimeoutError:
            raise HTTPException(504) from None
        except Exception:
            raise HTTPException(503) from None
        # Re-read authoritative account/session, selected versions and material state.
        current = self._context(principal, request, policy_version)
        replay = self._replay(principal, key, request_hash)
        if replay is not None:
            return replay
        if content_digest(current.model_dump(mode="json")) != content_digest(
            context.model_dump(mode="json")
        ):
            raise HTTPException(409)
        missing = [
            name
            for name in dict.fromkeys(
                [
                    *current.agent.input_support.product_required_fields,
                    "material",
                    "efficacy",
                    "price",
                    "promotion",
                ]
            )
            if request.product.get(name) in (None, "", [])
        ]
        missing.extend(
            "parameters." + name
            for name, rule in current.spec.parameter_schema.fields.items()
            if rule.required and name not in request.parameters
        )
        if len(request.material_versions) < current.agent.input_support.min_materials:
            missing.append("material_versions")
        if current.agent.input_support.instruction_required and not request.original.strip():
            missing.append("original")
        proposal = AssistProposal(
            original=request.original,
            proposed=response.proposed,
            missing_facts=missing,
            policy_version=policy_version,
            parameters=request.parameters,
            agent_version=current.agent.version,
            spec_version=current.spec.version,
        )
        self.session.add(
            AssistRecord(
                user_id=str(principal.user_id),
                request_key=key,
                request_hash=request_hash,
                original=proposal.original,
                proposed=proposal.proposed,
                policy_version=policy_version,
                status="COMPLETED",
                response=proposal.model_dump(mode="json"),
                created_at=now(),
            )
        )
        self.session.flush()
        return proposal
