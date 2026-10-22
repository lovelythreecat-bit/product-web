"""Explicit owner-authorized video commands; network I/O follows durable intent."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.agents.media_execution import (
    MediaCommand,
    MediaExecution,
    command_digest,
    new_command,
    public_media_state,
    validate_command_key,
)
from app.agents.registry import AgentRegistry
from app.auth.routes import DB, PrincipalDep, require_csrf
from app.common.types import DTO
from app.conversations.service import authenticate
from app.dispatch.consumer import LeaseManager
from app.storage.local_store import LocalStore
from app.tasks.models import GenerationTask, TaskSnapshot
from app.tasks.repository import locked_execution

router = APIRouter(prefix="/api/v1/tasks", tags=["video-interaction"])


class VideoConfirm(DTO):
    plan_version: int = Field(strict=True, ge=1)


class VideoInputs(DTO):
    text: str = Field(min_length=1, max_length=10000)


class VideoShotTextPatch(DTO):
    shot_id: str = Field(min_length=1, max_length=200)
    content: str | None = Field(default=None, max_length=10000)
    action: str | None = Field(default=None, max_length=10000)
    shot_size: str | None = Field(default=None, max_length=1000)
    camera: str | None = Field(default=None, max_length=1000)
    subtitle_text: str | None = Field(default=None, max_length=10000)
    voiceover_text: str | None = Field(default=None, max_length=10000)


class VideoPlanPatch(DTO):
    shot_texts: list[VideoShotTextPatch] | None = Field(default=None, min_length=1, max_length=100)
    music_direction: str | None = Field(default=None, max_length=10000)


class VideoPlanRevision(DTO):
    plan_version: int = Field(strict=True, ge=1)
    instruction: str | None = Field(default=None, min_length=1, max_length=10000)
    patch: VideoPlanPatch | None = None

    @model_validator(mode="after")
    def one_change(self):
        if ((self.instruction is None) == (self.patch is None)
                or self.instruction is not None and not self.instruction.strip()
                or self.patch is not None and not self.patch.model_dump(exclude_none=True)):
            raise ValueError("Provide one non-empty plan change")
        return self


def assert_video_command_task(task, snapshot, owner_id):
    if task is None or task.user_id != str(owner_id):
        raise HTTPException(404)
    if (snapshot is None or snapshot.agent_snapshot.get("protocol_version") != "video-agent-v1"
            or task.state != "RUNNING" or task.settlement_state != "FROZEN"
            or not task.upstream_id):
        raise HTTPException(409, detail="当前任务尚不能执行此操作，请刷新原任务。")


def validate_new_command(state, operation, body):
    if operation in {"confirm", "revise"}:
        if (state.get("status") != "awaiting_confirmation"
                or state.get("head_plan_version") != body["plan_version"]
                or state.get("plan", {}).get("plan_version") != body["plan_version"]):
            raise HTTPException(409, detail="方案已更新，请重新查看当前方案。")
    elif state.get("status") != "awaiting_input":
        raise HTTPException(409, detail="当前任务不需要补充资料，请刷新原任务。")


def recover_command_response(command, state):
    if command.operation == "confirm":
        intended = {"idempotency_key": command.request_key,
                    "plan_version": command.request["upstream_body"]["plan_version"]}
        proven = (state.get("confirmation_intent") == intended
                  and state.get("confirmed_plan_version") == intended["plan_version"]
                  and state.get("generation_id"))
    elif command.operation == "revise":
        intended = {"idempotency_key": command.request_key,
                    "body": command.request["upstream_body"]}
        proven = (state.get("revision_intent") == intended
                  and state.get("revision_intent_applied") is True)
    else:
        intended = {"idempotency_key": command.request_key,
                    "body": command.request["upstream_body"]}
        proven = state.get("input_intent") == intended and state.get("input_intent_applied") is True
    return public_media_state("video", state) if proven else None


def command_response(command):
    from app.agents.media_http import MediaServiceError

    if "command_error" in command.response:
        error = MediaServiceError(command.response["command_error"],
                                  public_message="原操作已被服务拒绝，请刷新任务后修改输入。")
        error.command_rejected = True
        raise error
    return command.response


def execute_command(id, operation, body, key, request, session, principal):
    from app.agents.media_http import MediaServiceError

    try:
        validate_command_key(key)
    except ValueError:
        raise HTTPException(422) from None
    authenticate(session, principal)
    task = session.scalar(select(GenerationTask).where(
        GenerationTask.id == str(id), GenerationTask.user_id == str(principal.user_id)
    ).with_for_update())
    snapshot = session.get(TaskSnapshot, str(id)) if task is not None else None
    if task is None or task.user_id != str(principal.user_id):
        raise HTTPException(404)
    if snapshot is None or snapshot.agent_snapshot.get("protocol_version") != "video-agent-v1":
        raise HTTPException(409)
    execution = session.get(MediaExecution, task.id)
    if execution is None or execution.kind != "video":
        raise HTTPException(409)
    command = session.scalar(select(MediaCommand).where(
        MediaCommand.task_id == task.id, MediaCommand.operation == operation,
        MediaCommand.request_key == key).with_for_update())
    if command is not None:
        if command.request_hash != command_digest(operation, body):
            raise HTTPException(409, detail="原操作标识对应其他内容，请核对原操作。")
        if command.response is not None:
            return command_response(command)
        recovered = recover_command_response(command, execution.state)
        if recovered is not None:
            command.response = recovered
            session.commit()
            return recovered
    else:
        pending = session.scalar(select(MediaCommand).where(
            MediaCommand.task_id == task.id, MediaCommand.response.is_(None)).limit(1))
        if pending is not None:
            recovered = recover_command_response(pending, execution.state)
            if recovered is None:
                raise HTTPException(409, detail="原操作结果尚未确认，请使用原请求继续核对。")
            pending.response = recovered
        try:
            assert_video_command_task(task, snapshot, principal.user_id)
            validate_new_command(execution.state, operation, body)
        except HTTPException as rejected:
            error = MediaServiceError(rejected.status_code,
                                      public_message="任务或方案已更新，请刷新任务后重新操作。")
            error.command_rejected = True
            raise error from None
        if operation == "inputs":
            text = body["text"].strip()
            if not text:
                raise HTTPException(422)
            original = execution.state.get("input_overrides", {}).get(
                "user_prompt", execution.state.get("request_body", {}).get("user_prompt", ""))
            upstream_body = {"user_prompt": original + "\n补充资料：" + text}
        else:
            upstream_body = body
        command = new_command(task.id, operation, key, body)
        command.request = {"input": body, "upstream_body": upstream_body}
        session.add(command)
    assert_video_command_task(task, snapshot, principal.user_id)
    task_id, command_id = task.id, command.id
    from app.agents.video_commands import queue_authorized_command

    queue_authorized_command(session, task, execution, command_id)
    # Persist before transport, including the exact expanded input command body.
    # An uncertain commit is never retried as a new operation.
    session.commit()
    settings = request.app.state.settings
    if not settings.storage_persistent or settings.storage_root is None:
        raise MediaServiceError(503)
    factory = sessionmaker(request.app.state.engine, expire_on_commit=False)
    leases = LeaseManager(factory)
    lease = leases.claim_task(task_id, "video-command:" + command_id)
    if lease is None:
        raise MediaServiceError(409, public_message="原任务正在更新，请稍后使用原操作重试。")
    try:
        registry = AgentRegistry.from_settings(settings, session_factory=factory,
                                               store=LocalStore(settings.storage_root))
        from app.agents.upstream import UpstreamService

        upstream = UpstreamService(factory, registry)
        from app.agents.video_commands import execute_video_command

        return execute_video_command(upstream, task_id, lease, command_id)
    except MediaServiceError as error:
        # A structured rejection completes this command only. It does not prove
        # the generation failed and never releases credits or starts a new job.
        if error.status_code in {404, 409, 413, 422}:
            with factory() as target, target.begin():
                locked_execution(target, task_id, lease)
                target.get(MediaCommand, command_id).response = {
                    "command_error": error.status_code}
                current = target.get(MediaExecution, task_id, with_for_update=True)
                state = dict(current.state)
                field = {"confirm": "confirmation_intent", "revise": "revision_intent"}.get(
                    operation, "input_intent")
                if (state.get(field, {}).get("idempotency_key") == key
                        and not state.get("generation_id")):
                    state.pop(field, None)
                    state.pop("input_intent_applied", None)
                    state.pop("revision_intent_applied", None)
                    current.state = state
                    current.revision += 1
            error.command_rejected = True
        raise
    except LookupError:
        raise MediaServiceError(503) from None
    finally:
        leases.release(lease, retry_seconds=1)


@router.post("/{id}/video/confirm", response_model=dict, operation_id="confirm_video_plan",
             dependencies=[Depends(require_csrf)])
def confirm_video_plan(
    id: UUID, dto: VideoConfirm, request: Request, session: DB, principal: PrincipalDep,
    key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
):
    return execute_command(id, "confirm", dto.model_dump(), key, request, session, principal)


@router.post("/{id}/video/inputs", response_model=dict, operation_id="supplement_video_inputs",
             dependencies=[Depends(require_csrf)])
def supplement_video_inputs(
    id: UUID, dto: VideoInputs, request: Request, session: DB, principal: PrincipalDep,
    key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
):
    return execute_command(id, "inputs", dto.model_dump(), key, request, session, principal)


@router.post("/{id}/video/plan-revisions", response_model=dict, operation_id="revise_video_plan",
             dependencies=[Depends(require_csrf)])
def revise_video_plan(
    id: UUID, dto: VideoPlanRevision, request: Request, session: DB, principal: PrincipalDep,
    key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
):
    return execute_command(id, "revise", dto.model_dump(exclude_none=True),
                           key, request, session, principal)
