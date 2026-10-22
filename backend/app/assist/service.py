"""Short authoritative reads around a provider call; never persists a generation intent."""

import asyncio

from fastapi import HTTPException
from sqlalchemy import select

from app.assist.configuration import read_assist_connection
from app.assist.models import AssistRecord
from app.assist.provider import (
    TEST_SCHEME,
    MockPromptAssistProvider,
    OpenAIPromptAssistProvider,
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


def validate_draft_parameters(request, agent, spec):
    from app.agents.media_execution import OUTPUT_TYPES, PLATFORMS

    parameters = request.parameters
    if agent.kind == "image":
        if (set(parameters) - {"platform", "output_type"}
                or "platform" in parameters and parameters["platform"] not in PLATFORMS
                or "output_type" in parameters and parameters["output_type"] not in OUTPUT_TYPES):
            raise HTTPException(422)
    elif agent.kind == "video":
        if (set(parameters) - {"first_frame_file_id"}
                or "first_frame_file_id" in parameters
                and parameters["first_frame_file_id"] not in {
                    str(ref.file_id) for ref in request.material_versions
                }):
            raise HTTPException(422)
    elif agent.protocol_version == "text-agent-v1":
        from app.agents.text_parameters import validate_text_parameters

        try:
            validate_text_parameters(parameters)
        except (ValueError, TypeError):
            raise HTTPException(422) from None
    else:
        for name, value in parameters.items():
            rule = spec.parameter_schema.fields.get(name)
            if rule is None or not rule.accepts(value):
                raise HTTPException(422)


class AssistService:
    def __init__(self, session, settings):
        self.session, self.settings = session, settings

    def _context(self, principal, request, policy_version):
        session, settings = self.session, self.settings
        authenticate(session, principal)
        mock = (settings.mode == "mock" and settings.test_only
                and settings.assist_provider == "deterministic_mock")
        self.connection = read_assist_connection(session, settings, required=not mock)
        if self.connection is None:
            # Retain the explicitly isolated deterministic simulation for existing
            # fixtures. A configured independent model always takes precedence.
            policies = PolicyService(session)
            policies.require_feature("prompt_assist", settings.mode, {"D-05": policy_version})
            policy = AssistPolicy.model_validate(
                policies._read("D-05", policy_version).payload["assist"]
            )
            if (settings.assist_policy_version != policy_version
                    or policy.scheme != "OTHER_CONFIRMED_SCHEME"
                    or policy.policy_ref != TEST_SCHEME
                    or policy.implementation_ref != TEST_SCHEME):
                raise PolicyGateError()
        catalog = CatalogService(session, mode=settings.mode)
        spec, agent = catalog.single_context(request.agent_id)
        if agent.agent_id != request.agent_id:
            raise HTTPException(422)
        if agent.version != request.agent_version:
            raise HTTPException(409)
        validate_draft_parameters(request, agent, spec)
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
            connection = self.connection
            replay = self._replay(principal, key, request_hash)
            if replay is not None:
                return replay
        finally:
            self.session.rollback()
        if before_provider is not None:
            before_provider()

        async def invoke():
            provider = (OpenAIPromptAssistProvider(
                connection, timeout=self.settings.assist_timeout_seconds,
            ) if connection else MockPromptAssistProvider())
            return await asyncio.wait_for(
                provider.prepare(context),
                timeout=self.settings.assist_timeout_seconds,
            )

        try:
            response = ProviderResponse.model_validate(asyncio.run(invoke()))
        except TimeoutError:
            raise HTTPException(504) from None
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(503) from None
        # Re-read authoritative account/session, selected versions and material state.
        current = self._context(principal, request, policy_version)
        replay = self._replay(principal, key, request_hash)
        if replay is not None:
            return replay
        if content_digest(current.model_dump(mode="json")) != content_digest(
            context.model_dump(mode="json")
        ) or self.connection != connection:
            raise HTTPException(409)
        missing = [
            name
            for name in dict.fromkeys(current.agent.input_support.product_required_fields)
            if request.product.get(name) in (None, "", [])
        ]
        missing.extend(
            "parameters." + name
            for name, rule in current.spec.parameter_schema.fields.items()
            if rule.required and name not in request.parameters
        )
        missing.extend("parameters." + name for name in {
            "image": ("platform", "output_type"), "video": ("first_frame_file_id",),
        }.get(current.agent.kind, ()) if name not in request.parameters)
        if len(request.material_versions) < current.agent.input_support.min_materials:
            missing.append("material_versions")
        if current.agent.input_support.instruction_required and not request.original.strip():
            missing.append("original")
        proposal = AssistProposal(
            original=request.original,
            proposed=response.proposed,
            missing_facts=missing,
            policy_version=str(connection.version) if connection else policy_version,
            parameters=request.parameters,
            agent_version=current.agent.version,
            spec_version=current.spec.version,
            test_only=connection is None,
        )
        self.session.add(
            AssistRecord(
                user_id=str(principal.user_id),
                request_key=key,
                request_hash=request_hash,
                original=proposal.original,
                proposed=proposal.proposed,
                policy_version=proposal.policy_version,
                status="COMPLETED",
                response=proposal.model_dump(mode="json"),
                created_at=now(),
            )
        )
        self.session.flush()
        return proposal
