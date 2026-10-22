"""Offline video contract tests; no provider or database is contacted."""

import importlib
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image
from pydantic import SecretStr


def video():
    assert importlib.util.find_spec("app.agents.video") is not None, "Video adapter is missing"
    return importlib.import_module("app.agents.video")


def source():
    file_id = str(uuid4())
    return {
        "user_id": str(uuid4()),
        "input_snapshot": {
            "product": {
                "name": "茶杯",
                "category": "日用",
                "sellingPoints": "耐热\n带盖",
                "material": "陶瓷",
            },
            "instruction": "不要编造促销",
            "parameters": {"first_frame_file_id": file_id},
            "material_versions": [{"file_id": file_id, "version": "v1"}],
        },
    }


def prepare(monkeypatch, state=None):
    module = video()
    state = {} if state is None else state
    profile = module.VideoAgentProfile(
        base_url="http://127.0.0.1:8080",
        service_key=SecretStr("test-secret"),
        max_result_bytes=1024,
    )
    adapter = module.VideoAgentAdapter(
        profile=profile,
        external_submission_id=str(uuid4()),
        load_state=lambda: deepcopy(state),
        save_state=lambda patch: state.update(deepcopy(patch)),
    )
    snap = source()
    asset = str(uuid4())
    body = module.build_video_request(
        snap,
        {snap["input_snapshot"]["material_versions"][0]["file_id"] + ":v1": {"asset_id": asset}},
    )
    body.update(
        external_user_id=snap["user_id"], external_request_id=adapter.external_submission_id
    )
    state["request_body"] = body
    task_id = str(uuid4())
    state["upstream_task_id"] = task_id
    view = {"task_id": task_id, "status": "planning", "questions": [], **deepcopy(body)}
    view["image_asset_ids"] = view.pop("images")
    return module, adapter, state, snap, view


def test_plan_revision_keeps_original_task_and_unknown_receipts_never_repost(monkeypatch):
    module, adapter, state, _, view = prepare(monkeypatch)
    state.update(status="awaiting_confirmation", head_plan_version=2,
                 plan={"task_id": view["task_id"], "plan_version": 2})
    body = {"plan_version": 2, "instruction": "重新规划，保留原商品事实和首帧"}
    posts = []
    def transport(method, path, payload=None, **kwargs):
        posts.append((method, path, payload))
        raise module.MediaServiceError(503)
    monkeypatch.setattr(adapter.client, "json", transport)
    with pytest.raises(module.MediaServiceError):
        adapter.revise_plan(body, "revision-key")
    assert posts == [("POST", f'/api/v1/tasks/{view["task_id"]}/plan-revisions',
                      {"instruction": body["instruction"]})]
    def query(task_id):
        assert task_id == view["task_id"]
    monkeypatch.setattr(adapter, "query", query)
    with pytest.raises(module.MediaServiceError):
        adapter.revise_plan(body, "revision-key")
    assert len(posts) == 1
    state["revision_intent_applied"] = True
    assert adapter.revise_plan(body, "revision-key")["revision_intent_applied"] is True
    assert len(posts) == 1


def test_request_requires_explicit_frozen_first_frame_and_preserves_facts():
    module = video()
    snap = source()
    body = module.build_video_request(snap, validate_only=True)
    assert body["product_info"]["selling_points"] == ["耐热\n带盖"]
    assert body["product_info"]["extra"] == {"material": "陶瓷"}
    assert body["user_prompt"] == "不要编造促销"
    assert body["video_options"]["voiceover"] is False
    assert body["video_options"]["music"] is False
    for invalid in ({}, {"first_frame_file_id": str(uuid4())}):
        snap["input_snapshot"]["parameters"] = invalid
        with pytest.raises(ValueError):
            module.build_video_request(snap, validate_only=True)


def test_audio_preference_is_explicit_and_legacy_tasks_remain_silent():
    module = video()
    snap = source()
    options = module.build_video_request(snap, validate_only=True)["video_options"]
    assert options["voiceover"] is False
    snap["routing_snapshot"] = {"video_audio_enabled": True}
    body = module.build_video_request(snap, validate_only=True)
    assert body["video_options"]["voiceover"] is True
    assert body["video_options"]["music"] is True


def test_selected_video_seconds_and_ratio_reach_upstream_without_mutating_snapshot():
    module = video()
    snap = source()
    snap["input_snapshot"]["parameters"].update(duration_seconds=12, aspect_ratio="16:9")
    original = deepcopy(snap)
    body = module.build_video_request(snap, validate_only=True)
    assert body["video_options"]["duration_seconds"] == 12
    assert body["video_options"]["aspect_ratio"] == "16:9"
    assert snap == original


@pytest.mark.parametrize("parameter,value", [
    ("duration_seconds", True), ("duration_seconds", 1.5),
    ("duration_seconds", 0), ("duration_seconds", 31),
    ("aspect_ratio", "5:5"), ("aspect_ratio", 1),
])
def test_video_options_reject_invalid_types_ranges_and_ratios(parameter, value):
    snap = source()
    snap["input_snapshot"]["parameters"][parameter] = value
    with pytest.raises(ValueError):
        video().build_video_request(snap, validate_only=True)


def test_public_video_options_use_live_business_capabilities_and_project_only_choices(monkeypatch):
    assert importlib.util.find_spec("app.agents.video_options") is not None
    module = importlib.import_module("app.agents.video_options")
    from types import SimpleNamespace
    calls = []
    connection = SimpleNamespace(base_url="https://video.example", service_key=SecretStr("business"))
    monkeypatch.setattr(module, "read_media_connection", lambda *args: connection)
    class Client:
        def __init__(self, base_url, key, **kwargs):
            assert base_url == "https://video.example"
            assert key.get_secret_value() == "business"
        def json(self, method, path):
            calls.append((method, path))
            return {"duration_tiers": [6, 12], "default_duration": 12,
                    "aspect_ratios": ["9:16", "16:9"], "adapters": {"private": "discard"}}
    monkeypatch.setattr(module, "MediaClient", Client)
    assert module.read_video_options(None, None).model_dump() == {
        "duration_tiers": [6, 12], "default_duration": 12, "aspect_ratios": ["9:16", "16:9"]}
    assert calls == [("GET", "/api/v1/capabilities")]


@pytest.mark.parametrize("patch", [
    {"duration_tiers": []}, {"duration_tiers": [6, 6]},
    {"default_duration": 10}, {"duration_tiers": [True, 12]},
    {"aspect_ratios": ["unknown"]}, {"aspect_ratios": []},
])
def test_public_video_options_reject_malformed_capabilities(monkeypatch, patch):
    from app.agents import video_options as module
    payload = {"duration_tiers": [6, 12], "default_duration": 12,
               "aspect_ratios": ["9:16", "16:9"], **patch}
    monkeypatch.setattr(module, "read_media_connection", lambda *args: type(
        "Connection", (), {"base_url": "https://video.example", "service_key": "key"})())
    monkeypatch.setattr(module.MediaClient, "json", lambda *args: payload)
    with pytest.raises(module.MediaServiceError):
        module.read_video_options(None, None)


def test_video_options_route_requires_an_authenticated_account():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.catalog import routes
    from app.db import get_session
    from types import SimpleNamespace
    app = FastAPI()
    app.state.settings = SimpleNamespace(mode="mock")
    app.include_router(routes.router)
    app.dependency_overrides[get_session] = lambda: object()
    with TestClient(app) as client:
        response = client.get("/api/v1/video-options")
    assert response.status_code == 401


@pytest.mark.parametrize("audio_enabled", [False, True])
def test_submission_persists_upload_and_exact_body_before_post(monkeypatch, audio_enabled):
    module = video()
    snap = source()
    state, events = {}, []
    image = BytesIO()
    Image.new("RGB", (2, 2), "white").save(image, "PNG")
    data, asset_id, task_id, external = image.getvalue(), str(uuid4()), str(uuid4()), str(uuid4())
    material = {
        **snap["input_snapshot"]["material_versions"][0],
        "content": data,
        "media_type": "image/png",
        "sha256": sha256(data).hexdigest(),
    }
    profile = module.VideoAgentProfile(
        base_url="http://127.0.0.1:8080",
        service_key=SecretStr("test-secret"),
        max_result_bytes=1024,
        video_audio_enabled=audio_enabled,
    )
    adapter = module.VideoAgentAdapter(
        profile=profile,
        material_loader=lambda: [material],
        load_state=lambda: deepcopy(state),
        save_state=lambda patch: state.update(deepcopy(patch)),
    )
    monkeypatch.setattr(
        adapter.client,
        "upload",
        lambda *a, **k: {
            "asset_id": asset_id,
            "kind": "image",
            "media_type": "image/png",
            "byte_size": len(data),
            "filename": "image.png",
        },
    )

    def request(method, path, body=None, idempotency_key=None):
        assert state["request_body"] == body
        assert body["video_options"]["voiceover"] is audio_enabled
        assert body["video_options"]["music"] is audio_enabled
        assert state["uploads"][material["file_id"] + ":v1"]["asset_id"] == asset_id
        assert idempotency_key == external
        events.append(method)
        return 201, {
            "task_id": task_id,
            "status": "pending",
            **body,
            "image_asset_ids": body["images"],
        }

    monkeypatch.setattr(adapter.client, "json", request)
    outcome = adapter.submit(snap, external)
    assert outcome.status == "ACCEPTED"
    assert state["upstream_task_id"] == task_id
    assert state["request_body"]["first_frame_asset_id"] == asset_id
    assert adapter.submit(snap, external).status == "ACCEPTED"
    assert events == ["POST"]


@pytest.mark.parametrize("phase", ["awaiting_input", "awaiting_confirmation"])
def test_waiting_user_keeps_running_and_never_confirms(monkeypatch, phase):
    _, adapter, state, _, view = prepare(monkeypatch)
    view.update(status=phase, questions=["请补充人群"])
    calls = []

    def request(method, path, body=None, idempotency_key=None):
        calls.append(method)
        return 200, view

    monkeypatch.setattr(adapter.client, "json", request)
    result = adapter.query(view["task_id"])
    assert result.status == "FOUND" and result.state == "RUNNING"
    assert state["status"] == phase
    assert state["questions"] == ["请补充人群"]
    assert calls == ["GET"]


def test_confirm_posts_fixed_version_and_rejects_old_head(monkeypatch):
    module, adapter, state, _, view = prepare(monkeypatch)
    state.update(
        status="awaiting_confirmation",
        head_plan_version=2,
        plan={
            "task_id": view["task_id"],
            "plan_version": 2,
            "document": {"first_frame_source": "selected"},
        },
    )
    with pytest.raises(module.MediaServiceError):
        adapter.confirm(1, "confirm-key")
    generation = str(uuid4())

    def request(method, path, body=None, idempotency_key=None):
        assert (method, path, body, idempotency_key) == (
            "POST",
            f"/api/v1/tasks/{view['task_id']}/confirm",
            {"plan_version": 2},
            "confirm-key",
        )
        return 202, {
            **view,
            "status": "generating",
            "generation_id": generation,
            "confirmed_plan_version": 2,
        }

    monkeypatch.setattr(adapter.client, "json", request)
    adapter.confirm(2, "confirm-key")
    assert state["generation_id"] == generation and state["confirmed_plan_version"] == 2


def test_input_patch_preserves_original_request_and_replays_exact_key(monkeypatch):
    module, adapter, state, _, view = prepare(monkeypatch)
    original = deepcopy(state["request_body"])
    state["status"] = "awaiting_input"
    body = {"user_prompt": "面向通勤人群"}

    def request(method, path, body=None, idempotency_key=None):
        assert method == "PATCH" and path.endswith("/inputs")
        assert idempotency_key == "input-key"
        return 202, {**view, **body, "status": "pending"}

    monkeypatch.setattr(adapter.client, "json", request)
    adapter.update_inputs(body, "input-key")
    assert state["request_body"] == original
    assert state["input_overrides"] == body
    with pytest.raises(module.MediaServiceError):
        adapter.update_inputs({"images": ["http://unsafe.invalid"]}, "other")


def test_external_lookup_rejects_duplicates_and_empty_is_not_absence_proof(monkeypatch):
    _, adapter, state, _, view = prepare(monkeypatch)
    monkeypatch.setattr(
        adapter.client,
        "json",
        lambda *a, **k: (
            200,
            {"items": [{"task_id": view["task_id"]}, {"task_id": str(uuid4())}], "total": 2},
        ),
    )
    assert adapter.query_by_external(adapter.external_submission_id).status == "UNAVAILABLE"
    monkeypatch.setattr(adapter.client, "json", lambda *a, **k: (200, {"items": [], "total": 0}))
    outcome = adapter.query_by_external(adapter.external_submission_id)
    assert outcome.status == "NOT_FOUND" and outcome.absence_proof is None
    assert state["upstream_task_id"] == view["task_id"]


@pytest.mark.parametrize(
    "bad", ["wrong-task", "wrong-plan", "flagged", "duplicate", "unchecked", "check-failed"]
)
def test_succeeded_generation_does_not_deliver_unbound_or_unapproved_artifacts(monkeypatch, bad):
    _, adapter, state, _, view = prepare(monkeypatch)
    generation, artifact_id = str(uuid4()), str(uuid4())
    state.update(generation_id=generation, confirmed_plan_version=2)
    view.update(status="succeeded", generation_id=generation, confirmed_plan_version=2)
    artifact = {
        "task_id": view["task_id"],
        "generation_id": generation,
        "plan_version": 2,
        "artifact_id": artifact_id,
        "quality_status": "passed",
    }
    if bad == "wrong-task":
        artifact["task_id"] = str(uuid4())
    elif bad == "wrong-plan":
        artifact["plan_version"] = 3
    elif bad == "flagged":
        artifact["quality_status"] = "flagged"
        artifact["visual_check_enabled"] = False
    elif bad in {"unchecked", "check-failed"}:
        artifact["quality_status"] = "not_assessed"
        if bad == "check-failed":
            artifact["visual_check_enabled"] = True

    def request(method, path, **kwargs):
        if path.endswith("/artifacts"):
            return 200, [artifact, artifact] if bad == "duplicate" else [artifact]
        if "/generations/" in path:
            return 200, {
                "task_id": view["task_id"],
                "generation_id": generation,
                "plan_version": 2,
                "status": "succeeded",
            }
        return 200, view

    monkeypatch.setattr(adapter.client, "json", request)
    monkeypatch.setattr(adapter.client, "download", lambda path: pytest.fail("Unsafe download"))
    assert adapter.query(view["task_id"]).status == "UNAVAILABLE"


@pytest.mark.parametrize("quality,visual_enabled", [("passed", True), ("not_assessed", False)])
def test_exact_artifact_bytes_define_manifest_and_original_recovery(
    monkeypatch, quality, visual_enabled
):
    _, adapter, state, _, view = prepare(monkeypatch)
    generation, artifact_id = str(uuid4()), str(uuid4())
    state.update(generation_id=generation, confirmed_plan_version=2)
    view.update(status="succeeded", generation_id=generation, confirmed_plan_version=2)
    artifact = {
        "task_id": view["task_id"],
        "generation_id": generation,
        "plan_version": 2,
        "artifact_id": artifact_id,
        "quality_status": quality,
        "visual_check_enabled": visual_enabled,
    }

    def request(method, path, **kwargs):
        if path.endswith("/artifacts"):
            return 200, [{**artifact, "generation_id": str(uuid4())}, artifact]
        if "/generations/" in path:
            return 200, {
                "task_id": view["task_id"],
                "generation_id": generation,
                "plan_version": 2,
                "status": "succeeded",
            }
        return 200, view

    monkeypatch.setattr(adapter.client, "json", request)
    data = b"full-video-content"
    monkeypatch.setattr(adapter.client, "download", lambda path: (data, "video/mp4"))
    result = adapter.query(view["task_id"])
    assert result.state == "RESULT_READY"
    item = result.result.items[0]
    assert item.locator == f"/api/v1/artifacts/{artifact_id}/content"
    assert item.sha256 == sha256(data).hexdigest() and item.byte_length == len(data)
    assert adapter.retrieve_original(item.locator).content == data
    monkeypatch.setattr(adapter.client, "download", lambda path: (b"changed", "video/mp4"))
    assert adapter.retrieve_original(item.locator).status == "UNAVAILABLE"
    assert adapter.retrieve_original("https://evil.invalid/asset").status == "UNSUPPORTED"


def test_unknown_create_is_never_posted_again(monkeypatch):
    _, adapter, state, snap, _ = prepare(monkeypatch)
    state.pop("upstream_task_id")
    state["submission_attempted"] = True
    monkeypatch.setattr(adapter.client, "json", lambda *a, **k: pytest.fail("Duplicate create"))
    assert adapter.submit(snap, adapter.external_submission_id).status == "UNKNOWN"


def test_unknown_input_command_cannot_be_replaced_with_new_key(monkeypatch):
    module, adapter, state, _, _ = prepare(monkeypatch)
    state.update(
        status="awaiting_input",
        input_intent={"body": {"user_prompt": "先前补充"}, "idempotency_key": "original-key"},
    )
    monkeypatch.setattr(
        adapter.client, "json", lambda *a, **k: pytest.fail("Replaced unknown PATCH")
    )
    with pytest.raises(module.MediaServiceError) as error:
        adapter.update_inputs({"user_prompt": "新补充"}, "new-key")
    assert error.value.status_code == 409


def test_queued_generation_keeps_polling_without_new_submission(monkeypatch):
    _, adapter, state, _, view = prepare(monkeypatch)
    generation = str(uuid4())
    state.update(generation_id=generation, confirmed_plan_version=2)
    view.update(status="generating", generation_id=generation, confirmed_plan_version=2)

    def request(method, path, **kwargs):
        if "/generations/" in path:
            return 200, {
                "generation_id": generation,
                "task_id": view["task_id"],
                "plan_version": 2,
                "status": "queued",
            }
        return 200, view

    monkeypatch.setattr(adapter.client, "json", request)
    outcome = adapter.query(view["task_id"])
    assert outcome.status == "FOUND" and outcome.state == "RUNNING"


def test_missing_explicit_user_uses_persisted_owner(monkeypatch):
    module, adapter, state, snap, view = prepare(monkeypatch)
    state.pop("upstream_task_id")
    state.pop("request_body")
    state["user_id"] = snap.pop("user_id")
    ref = snap["input_snapshot"]["material_versions"][0]
    state["uploads"] = {ref["file_id"] + ":v1": {"asset_id": view["first_frame_asset_id"]}}

    def request(method, path, body=None, **kwargs):
        assert body["external_user_id"] == state["user_id"]
        return 201, {**view, **body, "image_asset_ids": body["images"]}

    monkeypatch.setattr(adapter.client, "json", request)
    assert adapter.submit(snap, adapter.external_submission_id).status == "ACCEPTED"


def plan_view(view):
    return {
        "task_id": view["task_id"],
        "plan_version": 1,
        "is_head": True,
        "confirmed": False,
        "abandoned": False,
        "document": {
            "creative": "日常好物",
            "audience": "通勤人群",
            "selling_points": ["耐热"],
            "shared_visual": {
                "product_reference": "原商品",
                "scene": "办公室",
                "lighting": "自然光",
                "palette": "米色",
                "style": "写实",
            },
            "shots": [
                {
                    "shot_id": "s1",
                    "content": "展示茶杯",
                    "action": "放置",
                    "shot_size": "近景",
                    "camera": "固定",
                    "scene_id": "a",
                    "start_frame": 0,
                    "end_frame": 150,
                    "subtitle_text": "耐热",
                }
            ],
            "duration_seconds": 5,
            "aspect_ratio": "9:16",
            "fit": "native",
            "subtitles": True,
            "voiceover": False,
            "music": False,
            "first_frame_source": "selected",
            "first_frame_asset_id": view["first_frame_asset_id"],
            "model_capabilities": "视频",
            "unknown_secret": "must-not-project",
        },
    }


@pytest.mark.parametrize("lost_receipt", [False, True])
def test_structured_plan_edit_publishes_and_recovers_exact_new_version(monkeypatch, lost_receipt):
    _, adapter, state, _, view = prepare(monkeypatch)
    state.update(status="awaiting_confirmation", head_plan_version=1, plan=plan_view(view))
    body = {"plan_version": 1,
            "patch": {"shot_texts": [{"shot_id": "s1", "content": "新版茶杯近景"}]}}
    plan = plan_view(view)
    plan["plan_version"] = 2
    plan["document"]["shots"][0]["content"] = "新版茶杯近景"
    view.update(status="awaiting_confirmation", head_plan_version=2)
    posts = []
    def transport(method, path, payload=None, **kwargs):
        if method == "POST":
            posts.append(payload)
            assert state["revision_intent_applied"] is False
            if lost_receipt:
                raise video().MediaServiceError(503)
            return 200, view
        return 200, plan if "/plans/" in path else view
    monkeypatch.setattr(adapter.client, "json", transport)
    if lost_receipt:
        with pytest.raises(video().MediaServiceError):
            adapter.revise_plan(body, "edit-key")
    result = adapter.revise_plan(body, "edit-key")
    assert result["plan"]["plan_version"] == 2
    assert result["revision_intent_applied"] is True
    assert posts == [{"patch": body["patch"]}]
    assert state["plan"]["document"]["first_frame_asset_id"] == view["first_frame_asset_id"]


@pytest.mark.parametrize("bad", ["non-string", "unsupported-voice", "wrong-task", None])
def test_plan_projection_preserves_usable_fields_and_rejects_unsafe_options(monkeypatch, bad):
    _, adapter, state, _, view = prepare(monkeypatch)
    view.update(status="awaiting_confirmation", head_plan_version=1)
    plan = plan_view(view)
    if bad == "non-string":
        plan["document"]["shared_visual"]["scene"] = {"untrusted": "nested"}
    elif bad == "unsupported-voice":
        plan["document"]["voiceover"] = True
    elif bad == "wrong-task":
        plan["task_id"] = str(uuid4())
    monkeypatch.setattr(
        adapter.client, "json", lambda method, path, **k: (200, plan if "/plans/" in path else view)
    )
    outcome = adapter.query(view["task_id"])
    if bad is None:
        assert outcome.status == "FOUND" and outcome.state == "RUNNING"
        assert state["plan"]["document"]["duration_seconds"] == 5
        assert "unknown_secret" not in state["plan"]["document"]
    else:
        assert outcome.status == "UNAVAILABLE"
        assert "plan" not in state


def test_confirmation_timeout_is_recovered_from_original_generation(monkeypatch):
    _, adapter, state, _, view = prepare(monkeypatch)
    generation = str(uuid4())
    state["confirmation_intent"] = {"plan_version": 2, "idempotency_key": "original-key"}
    view.update(status="generating", confirmed_plan_version=2, generation_id=generation)

    def request(method, path, body=None, **kwargs):
        assert method == "GET"
        if "/generations/" in path:
            return 200, {
                "task_id": view["task_id"],
                "generation_id": generation,
                "plan_version": 2,
                "status": "running",
            }
        return 200, view

    monkeypatch.setattr(adapter.client, "json", request)
    assert adapter.query(view["task_id"]).state == "RUNNING"
    assert state["generation_id"] == generation


@pytest.mark.parametrize("recovered", [True, False])
def test_uncertain_input_update_queries_without_second_patch(monkeypatch, recovered):
    from app.agents.media_http import MediaServiceError

    _, adapter, state, _, view = prepare(monkeypatch)
    state["status"] = "awaiting_input"
    body, calls = {"user_prompt": "补充后的原始要求"}, []

    def request(method, path, supplied=None, **kwargs):
        calls.append(method)
        if method == "PATCH" or not recovered:
            raise MediaServiceError(503)
        return 200, dict(view, status="planning", user_prompt=body["user_prompt"])

    monkeypatch.setattr(adapter.client, "json", request)
    with pytest.raises(MediaServiceError):
        adapter.update_inputs(body, "TEST_ONLY_original_input")
    if recovered:
        assert adapter.update_inputs(body, "TEST_ONLY_original_input")["input_intent_applied"]
        adapter.update_inputs(body, "TEST_ONLY_original_input")
    else:
        with pytest.raises(MediaServiceError):
            adapter.update_inputs(body, "TEST_ONLY_original_input")
    assert calls.count("PATCH") == 1
    assert calls.count("GET") == 1


@pytest.mark.parametrize("method", ["query", "external"])
def test_invalid_response_shapes_are_unavailable(monkeypatch, method):
    _, adapter, _, _, view = prepare(monkeypatch)
    monkeypatch.setattr(adapter.client, "json", lambda *a, **k: (200, []))
    outcome = (
        adapter.query(view["task_id"])
        if method == "query"
        else adapter.query_by_external(adapter.external_submission_id)
    )
    assert outcome.status == "UNAVAILABLE"


def test_download_size_limit_never_creates_result_manifest(monkeypatch):
    _, adapter, state, _, view = prepare(monkeypatch)
    generation, artifact_id = str(uuid4()), str(uuid4())
    state.update(generation_id=generation, confirmed_plan_version=2)
    view.update(status="generating", confirmed_plan_version=2, generation_id=generation)

    def request(method, path, **kwargs):
        if path.endswith("/artifacts"):
            return 200, [
                {
                    "task_id": view["task_id"],
                    "generation_id": generation,
                    "plan_version": 2,
                    "artifact_id": artifact_id,
                    "quality_status": "passed",
                }
            ]
        if "/generations/" in path:
            return 200, {
                "task_id": view["task_id"],
                "generation_id": generation,
                "plan_version": 2,
                "status": "succeeded",
            }
        return 200, view

    monkeypatch.setattr(adapter.client, "json", request)
    monkeypatch.setattr(adapter.client, "download", lambda path: (b"x" * 1025, "video/mp4"))
    outcome = adapter.query(view["task_id"])
    assert outcome.status == "UNAVAILABLE" and outcome.result is None
    assert state["artifact_id"] == artifact_id
    assert "artifact_sha256" not in state


def test_nested_plan_metadata_cannot_be_projected_as_text(monkeypatch):
    _, adapter, state, _, view = prepare(monkeypatch)
    view.update(status="awaiting_confirmation", head_plan_version=1)
    plan = plan_view(view)
    plan["document"]["voice_preference"] = {"secret": "must-not-project"}
    monkeypatch.setattr(
        adapter.client, "json", lambda method, path, **k: (200, plan if "/plans/" in path else view)
    )
    assert adapter.query(view["task_id"]).status == "UNAVAILABLE"
    assert "plan" not in state


def test_confirm_rejects_plan_from_different_task_before_network(monkeypatch):
    module, adapter, state, _, _ = prepare(monkeypatch)
    state.update(
        status="awaiting_confirmation",
        head_plan_version=1,
        plan={"task_id": str(uuid4()), "plan_version": 1},
    )
    monkeypatch.setattr(adapter.client, "json", lambda *a, **k: pytest.fail("Wrong plan confirmed"))
    with pytest.raises(module.MediaServiceError) as error:
        adapter.confirm(1, "key")
    assert error.value.status_code == 409


def test_invalid_command_keys_return_controlled_error(monkeypatch):
    module, adapter, state, _, view = prepare(monkeypatch)
    state.update(
        status="awaiting_confirmation",
        head_plan_version=1,
        plan={"task_id": view["task_id"], "plan_version": 1},
    )
    with pytest.raises(module.MediaServiceError) as error:
        adapter.confirm(1, "invalid key")
    assert error.value.status_code == 422


def test_submit_cannot_relabel_existing_task_with_different_external_identity(monkeypatch):
    _, adapter, _, snap, _ = prepare(monkeypatch)
    adapter.external_submission_id = None
    outcome = adapter.submit(snap, str(uuid4()))
    assert outcome.status == "UNKNOWN" and outcome.upstream_task_id is None


def test_confirm_wrong_upstream_identity_returns_controlled_error(monkeypatch):
    module, adapter, state, _, view = prepare(monkeypatch)
    state.update(
        status="awaiting_confirmation",
        head_plan_version=1,
        plan={"task_id": view["task_id"], "plan_version": 1},
    )
    monkeypatch.setattr(adapter.client, "json", lambda *a, **k: (202, {"task_id": str(uuid4())}))
    with pytest.raises(module.MediaServiceError) as error:
        adapter.confirm(1, "key")
    assert error.value.status_code == 503
    assert "generation_id" not in state


@pytest.mark.parametrize("status", [429, 503])
def test_uncertain_confirmation_is_queried_without_repeating_post(monkeypatch, status):
    module, adapter, state, _, view = prepare(monkeypatch)
    state.update(
        status="awaiting_confirmation",
        head_plan_version=1,
        plan={"task_id": view["task_id"], "plan_version": 1},
    )
    requests = []

    def request(method, path, body=None, idempotency_key=None):
        requests.append((method, path))
        if method == "POST":
            raise module.MediaServiceError(status)
        raise module.MediaServiceError(503)

    monkeypatch.setattr(adapter.client, "json", request)
    with pytest.raises(module.MediaServiceError):
        adapter.confirm(1, "original-confirm")
    with pytest.raises(module.MediaServiceError):
        adapter.confirm(1, "original-confirm")
    assert [method for method, _ in requests] == ["POST", "GET"]
    assert state["confirmation_intent"] == {
        "plan_version": 1, "idempotency_key": "original-confirm"
    }
    assert state["confirmation_attempted"] is True


def test_unknown_legacy_confirmation_recovers_original_generation_without_post(monkeypatch):
    _, adapter, state, _, view = prepare(monkeypatch)
    state.update(
        status="awaiting_confirmation",
        head_plan_version=2,
        plan={"task_id": view["task_id"], "plan_version": 2},
        confirmation_intent={"plan_version": 2, "idempotency_key": "original-confirm"},
    )
    generation = str(uuid4())
    view.update(status="generating", generation_id=generation, confirmed_plan_version=2)

    def request(method, path, body=None, **kwargs):
        assert method == "GET"
        if "/generations/" in path:
            return 200, {
                "task_id": view["task_id"], "generation_id": generation,
                "plan_version": 2, "status": "queued",
            }
        return 200, view

    monkeypatch.setattr(adapter.client, "json", request)
    recovered = adapter.confirm(2, "original-confirm")
    assert recovered["generation_id"] == generation
    assert recovered["confirmed_plan_version"] == 2


def test_confirmed_original_command_returns_without_network(monkeypatch):
    _, adapter, state, _, view = prepare(monkeypatch)
    generation = str(uuid4())
    state.update(
        status="generating", head_plan_version=2,
        plan={"task_id": view["task_id"], "plan_version": 2},
        confirmation_intent={"plan_version": 2, "idempotency_key": "original-confirm"},
        generation_id=generation, confirmed_plan_version=2,
    )
    monkeypatch.setattr(adapter.client, "json", lambda *a, **k: pytest.fail("Repeated confirm"))
    assert adapter.confirm(2, "original-confirm")["generation_id"] == generation


def test_create_429_is_unknown_without_upstream_nonacceptance_contract(monkeypatch):
    module, adapter, state, snap, _ = prepare(monkeypatch)
    state.pop("upstream_task_id")
    reference = snap["input_snapshot"]["material_versions"][0]
    state["uploads"] = {
        reference["file_id"] + ":v1": {
            "asset_id": state["request_body"]["first_frame_asset_id"]
        }
    }
    calls = []

    def request(method, path, body=None, **kwargs):
        calls.append((method, path))
        raise module.MediaServiceError(429)

    monkeypatch.setattr(adapter.client, "json", request)
    assert adapter.submit(snap, adapter.external_submission_id).status == "UNKNOWN"
    assert adapter.submit(snap, adapter.external_submission_id).status == "UNKNOWN"
    assert calls == [("POST", "/api/v1/tasks")]
    assert state["submission_attempted"] is True
