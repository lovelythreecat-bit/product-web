from types import SimpleNamespace

import pytest


def test_media_inputs_are_explicit_and_do_not_restore_text_settings():
    from app.agents.media_execution import validate_media_input

    value = SimpleNamespace(parameters={"platform": "taobao", "output_type": "main_image"},
                            material_versions=[SimpleNamespace(file_id="image-1")])
    validate_media_input("image", value)
    value.parameters = {"platform": "taobao", "output_type": "pdd_white_background"}
    validate_media_input("image", value)
    value.parameters = {"platform": "taobao", "output_type": "long_image"}
    validate_media_input("image", value)
    value.parameters = {"first_frame_file_id": "other"}
    with pytest.raises(ValueError):
        validate_media_input("video", value)
    value.parameters = {"first_frame_file_id": "image-1"}
    validate_media_input("video", value)
    with pytest.raises(ValueError):
        validate_media_input("copy", value)


def test_execution_state_retains_original_request_and_upload_identity():
    from app.agents.media_execution import merge_execution_state

    current = {"request_body": {"asset": "a"}, "uploads": {"f:v": {"asset_id": "a"}}}
    assert merge_execution_state(current, {"status": "planning"})["request_body"] == {"asset": "a"}
    for patch in ({"request_body": {"asset": "b"}}, {"uploads": {"f:v": {"asset_id": "b"}}}):
        with pytest.raises(ValueError):
            merge_execution_state(current, patch)
    assert current == {"request_body": {"asset": "a"}, "uploads": {"f:v": {"asset_id": "a"}}}


def test_public_stage_never_returns_private_request_or_uploads():
    from app.agents.media_execution import public_media_state

    state = {"status": "awaiting_confirmation", "questions": ["补充用途"],
             "request_body": {"private": "original"}, "uploads": {"key": "private"},
             "api_key": "private", "head_plan_version": 2}
    value = public_media_state("video", state)
    assert value["status"] == "awaiting_confirmation"
    assert value["head_plan_version"] == 2
    assert not {"request_body", "uploads", "api_key"} & value.keys()


def test_command_key_replay_requires_identical_intent():
    from app.agents.media_execution import command_digest, validate_command_key

    validate_command_key("confirm-a")
    assert command_digest("confirm", {"plan_version": 2}) == command_digest(
        "confirm", {"plan_version": 2})
    assert command_digest("confirm", {"plan_version": 2}) != command_digest(
        "confirm", {"plan_version": 3})
    for key in ("", "with space", "中文", "x" * 129):
        with pytest.raises(ValueError):
            validate_command_key(key)


def test_video_commands_check_owner_and_existing_frozen_task():
    from fastapi import HTTPException

    from app.tasks.media_routes import assert_video_command_task

    task = SimpleNamespace(user_id="owner", state="RUNNING", settlement_state="FROZEN",
                           upstream_id="video-1")
    snapshot = SimpleNamespace(agent_snapshot={"protocol_version": "video-agent-v1"})
    assert_video_command_task(task, snapshot, "owner")
    with pytest.raises(HTTPException) as error:
        assert_video_command_task(task, snapshot, "other")
    assert error.value.status_code == 404
    task.settlement_state = "RELEASED"
    with pytest.raises(HTTPException) as error:
        assert_video_command_task(task, snapshot, "owner")
    assert error.value.status_code == 409


def test_media_result_manifest_requires_fixed_persisted_identity():
    from app.agents.contracts import ResultItem, ResultManifest
    from app.results.manifest import validate_manifest
    from app.tasks.state_machine import TransitionError

    item = ResultItem(item_key="original-1", locator="/api/v1/artifacts/a/content",
                      media_type="video/mp4", sha256="a" * 64, byte_length=20)
    value = ResultManifest(complete=True, expected_items=1, items=(item,))
    rule = {"media_kind": "video", "expected_item_keys": ["original-1"],
            "expected_manifest": value.model_dump(mode="json")}
    assert validate_manifest(value, rule, None, "task-1") == value
    wrong = value.model_copy(update={"items": (item.model_copy(
        update={"locator": "/api/v1/artifacts/b/content"}),)})
    with pytest.raises(TransitionError):
        validate_manifest(wrong, rule, None, "task-1")


def test_lost_receipt_recovers_only_durable_original_media_id():
    from app.agents.media_execution import saved_media_task_id

    adapter = SimpleNamespace(protocol_version="image-agent-v1", load_state=lambda: {
        "external_submission_id": "original", "upstream_task_id": "image-accepted"})
    assert saved_media_task_id(adapter, "original") == "image-accepted"
    assert saved_media_task_id(adapter, "other") is None


def test_media_store_cannot_write_without_claimed_lease():
    from app.agents.media_execution import MediaTaskStore

    with pytest.raises(LookupError):
        MediaTaskStore(None, "task", "video").save({"status": "planning"})


def test_original_command_can_recover_without_reposting_after_task_completion():
    from fastapi import HTTPException

    from app.tasks.media_routes import recover_command_response, validate_new_command

    state = {"confirmation_intent": {"idempotency_key": "original", "plan_version": 2},
             "confirmed_plan_version": 2, "generation_id": "generated", "status": "succeeded"}
    command = SimpleNamespace(operation="confirm", request_key="original",
                              request={"upstream_body": {"plan_version": 2}})
    assert recover_command_response(command, state)["generation_id"] == "generated"
    command.request_key = "other"
    assert recover_command_response(command, state) is None
    with pytest.raises(HTTPException):
        validate_new_command({"status": "awaiting_confirmation", "head_plan_version": 3},
                             "confirm", {"plan_version": 2})


def test_plan_revision_requires_the_current_unconfirmed_plan_and_valid_fields():
    from fastapi import HTTPException
    from pydantic import ValidationError

    from app.tasks.media_routes import VideoPlanRevision, validate_new_command

    value = VideoPlanRevision(plan_version=2, instruction="重新规划镜头")
    state = {"status": "awaiting_confirmation", "head_plan_version": 2,
             "plan": {"plan_version": 2}}
    validate_new_command(state, "revise", value.model_dump(exclude_none=True))
    for invalid in ({**state, "status": "generating"}, {**state, "head_plan_version": 3}):
        with pytest.raises(HTTPException):
            validate_new_command(invalid, "revise", value.model_dump(exclude_none=True))
    for body in ({}, {"instruction": " "}, {"patch": {"first_frame_asset_id": "other"}},
                 {"patch": {"shot_texts": [{"shot_id": "s1", "start_frame": 99}]}},
                 {"instruction": "修改", "patch": {"music_direction": "轻快"}}):
        with pytest.raises(ValidationError):
            VideoPlanRevision(plan_version=2, **body)


def test_plan_revision_receipt_recovers_only_the_exact_applied_intent():
    from app.tasks.media_routes import recover_command_response

    body = {"plan_version": 2, "instruction": "重新规划"}
    command = SimpleNamespace(operation="revise", request_key="revision-one",
                              request={"upstream_body": body})
    state = {"revision_intent": {"idempotency_key": "revision-one", "body": body},
             "revision_intent_applied": True, "status": "planning"}
    assert recover_command_response(command, state)["status"] == "planning"
    state["revision_intent_applied"] = False
    assert recover_command_response(command, state) is None
