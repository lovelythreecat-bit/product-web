"""The real text protocol is exercised with controlled HTTP responses, never a model."""

import json
from hashlib import sha256
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PIL import Image
from pydantic import SecretStr

from app.agents.text import (
    TextAgentAdapter,
    TextAgentProfile,
    build_copy_request,
    validate_text_image,
)


@pytest.fixture
def profile():
    return TextAgentProfile(
        base_url="http://127.0.0.1:8000",
        service_key=SecretStr("private-service-key"),
        model_config_id=uuid4(),
        supports_images=False,
    )


@pytest.fixture
def snapshot():
    return {
        "input_snapshot": {
            "product": {
                "name": "茶杯",
                "sellingPoints": "耐热\n带杯盖",
                "material": "陶瓷",
                "audience": "上班族",
                "scene": "办公室",
                "notes": "无优惠活动",
            },
            "instruction": "突出日常使用",
            "parameters": {"tone": "自然", "length": "短文案"},
            "material_versions": [],
        }
    }


def test_mapping_preserves_facts_and_does_not_invent_length(profile, snapshot):
    body = build_copy_request(snapshot, profile)
    assert body["product"]["selling_points"] == ["耐热", "带杯盖"]
    assert body["product"]["attributes"]["material"] == "陶瓷"
    assert body["product"]["attributes"]["scene"] == "办公室"
    assert body["product"]["attributes"]["notes"] == "无优惠活动"
    assert body["requirements"]["audience"] == "上班族"
    assert body["requirements"]["max_chars"] is None
    assert "短文案" in body["requirements"]["extra_instructions"]
    assert "突出日常使用" in body["requirements"]["extra_instructions"]


def test_explicit_concurrency_rejection_is_retryable(profile, snapshot, monkeypatch):
    adapter = TextAgentAdapter(profile=profile)
    monkeypatch.setattr(adapter, "_request", lambda *a, **kw: (
        429, {"error": {"code": "concurrency_limit"}, "record_id": None},
    ))
    outcome = adapter.submit(snapshot, str(uuid4()))
    assert outcome.status == "RATE_LIMITED"
    assert outcome.upstream_task_id is None
    assert outcome.retry_after_seconds >= 1


@pytest.mark.parametrize("status,payload", [
    (503, {"error": {"code": "concurrency_limit"}}),
    (429, {"error": {"code": "model_rate_limited"}}),
    (429, {"error": {"code": "concurrency_limit"}, "record_id": str(uuid4())}),
])
def test_only_unaccepted_concurrency_rejection_can_requeue(
    profile, snapshot, monkeypatch, status, payload,
):
    adapter = TextAgentAdapter(profile=profile)
    monkeypatch.setattr(adapter, "_request", lambda *a, **kw: (status, payload))
    assert adapter.submit(snapshot, str(uuid4())).status != "RATE_LIMITED"


@pytest.mark.parametrize("operation", ["submit", "query"])
def test_text_warnings_survive_submit_and_original_record_recovery(
    profile, snapshot, monkeypatch, operation,
):
    record_id = str(uuid4())
    result = {"text": "完整正文", "warnings": ["材质信息尚待核实", "优惠条件请确认"]}
    adapter = TextAgentAdapter(profile=profile)
    payload = ({"record_id": record_id, "result": result} if operation == "submit" else {
        "id": record_id, "model_config_id": str(profile.model_config_id),
        "status": "succeeded", "content_expired": False, "result_json": result,
    })
    monkeypatch.setattr(adapter, "_request", lambda *a, **kw: (200, payload))
    outcome = (adapter.submit(snapshot, str(uuid4())) if operation == "submit"
               else adapter.query(record_id))
    assert outcome.result is not None
    assert outcome.result.model_dump(mode="json")["warnings"] == result["warnings"]
    # Warnings are metadata; the downloadable and copied body must remain exact.
    assert outcome.result.items[0].byte_length == len("完整正文".encode())


def test_legacy_manifests_keep_their_original_serialization():
    from app.agents.contracts import ResultManifest

    original = TextAgentAdapter._manifest(str(uuid4()), {"text": "历史正文"}).model_dump(
        mode="json",
    )
    assert "warnings" not in original
    assert ResultManifest.model_validate(original).model_dump(mode="json") == original


def test_all_writing_requirements_reach_upstream_without_losing_instruction(profile, snapshot):
    snapshot["input_snapshot"]["parameters"] = {
        "copy_type": "直播口播", "platform": "自定义渠道", "audience": "通勤者",
        "tone": "轻松自然", "max_chars": 120, "language": "简体中文",
        "extra_instructions": "分三段，不用夸张口号",
    }
    body = build_copy_request(snapshot, profile, validate_only=True)
    assert body["requirements"] == {
        "copy_type": "直播口播", "platform": "自定义渠道", "audience": "通勤者",
        "tone": "轻松自然", "max_chars": 120, "language": "简体中文",
        "extra_instructions": "突出日常使用\n额外协作要求：分三段，不用夸张口号",
    }


@pytest.mark.parametrize("parameters", [
    {"max_chars": 0}, {"max_chars": -1}, {"max_chars": True},
    {"max_chars": 1.5}, {"max_chars": "120"}, {"audience": []},
    {"copy_type": None}, {"extra_instructions": {}},
])
def test_invalid_writing_requirements_are_rejected_before_submission(profile, snapshot, parameters):
    snapshot["input_snapshot"]["parameters"] = parameters
    with pytest.raises(ValueError):
        build_copy_request(snapshot, profile, validate_only=True)


@pytest.mark.parametrize("parameters", [{"count": 2}, {"unknown": "value"}])
def test_unsupported_parameters_are_rejected(profile, snapshot, parameters):
    snapshot["input_snapshot"]["parameters"] = parameters
    with pytest.raises(ValueError):
        build_copy_request(snapshot, profile)


def test_images_are_not_silently_dropped(profile, snapshot):
    snapshot["input_snapshot"]["material_versions"] = [{"file_id": str(uuid4()), "version": "v1"}]
    with pytest.raises(ValueError):
        build_copy_request(snapshot, profile)


def test_preflight_checks_image_capability_without_loading_bytes(profile, snapshot):
    enabled = profile.model_copy(update={"supports_images": True})
    snapshot["input_snapshot"]["material_versions"] = [{"file_id": str(uuid4()), "version": "v1"}]
    assert build_copy_request(snapshot, enabled, validate_only=True)["images"] == []
    with pytest.raises(ValueError):
        build_copy_request(snapshot, profile, validate_only=True)


@pytest.mark.parametrize(
    "field,value", [("category", None), ("brand", 1), ("material", {"nested": "invalid"})]
)
def test_preflight_rejects_values_outside_upstream_schema(profile, snapshot, field, value):
    snapshot["input_snapshot"]["product"][field] = value
    with pytest.raises(ValueError):
        build_copy_request(snapshot, profile, validate_only=True)


def test_explicit_attributes_are_mapped_as_attributes(profile, snapshot):
    snapshot["input_snapshot"]["product"]["attributes"] = {"容量": "300ml"}
    body = build_copy_request(snapshot, profile, validate_only=True)
    assert body["product"]["attributes"]["容量"] == "300ml"


def test_static_image_requirement_matches_upstream():
    first, second = Image.new("RGB", (4, 4), "red"), Image.new("RGB", (4, 4), "blue")
    static, animated = BytesIO(), BytesIO()
    first.save(static, format="PNG")
    first.save(animated, format="PNG", save_all=True, append_images=[second], duration=100)
    validate_text_image(static.getvalue(), "image/png")
    for data, mime in [
        (animated.getvalue(), "image/png"),
        (static.getvalue(), "video/mp4"),
        (b"not an image", "image/png"),
    ]:
        with pytest.raises(ValueError):
            validate_text_image(data, mime)


def test_sync_generation_uses_stable_key_and_complete_text(profile, snapshot, monkeypatch):
    adapter = TextAgentAdapter(profile=profile, external_submission_id=str(uuid4()))
    record_id = str(uuid4())
    calls = []

    def request(method, path, body=None, *, idempotency_key=None):
        calls.append((method, path, body, idempotency_key))
        return 200, {"record_id": record_id, "result": {"text": "完整文案"}}

    monkeypatch.setattr(adapter, "_request", request)
    outcome = adapter.submit(snapshot, adapter.external_submission_id)
    assert outcome.status == "COMPLETED"
    assert outcome.upstream_task_id == record_id
    assert outcome.test_only is False
    assert outcome.result.items[0].sha256 == sha256("完整文案".encode()).hexdigest()
    assert calls[0][3] == adapter.external_submission_id
    assert calls[0][2]["model_config_id"] == str(profile.model_config_id)
    assert adapter.capabilities.stream == "unsupported"


@pytest.mark.parametrize("payload", [{}, {"text": ""}, {"text": "  "}])
def test_incomplete_output_never_completes(profile, snapshot, monkeypatch, payload):
    adapter = TextAgentAdapter(profile=profile)
    monkeypatch.setattr(
        adapter,
        "_request",
        lambda *a, **kw: (
            200,
            {"record_id": str(uuid4()), "result": payload},
        ),
    )
    outcome = adapter.submit(snapshot, str(uuid4()))
    assert outcome.status == "ACCEPTED"
    assert outcome.upstream_task_id is not None
    assert outcome.result is None


def test_in_progress_preserves_record_identity(profile, snapshot, monkeypatch):
    adapter = TextAgentAdapter(profile=profile)
    record_id = str(uuid4())
    monkeypatch.setattr(
        adapter,
        "_request",
        lambda *a, **kw: (
            409,
            {"error": {"code": "request_in_progress"}, "record_id": record_id},
        ),
    )
    outcome = adapter.submit(snapshot, str(uuid4()))
    assert outcome.status == "ACCEPTED"
    assert outcome.upstream_task_id == record_id


def test_disconnect_does_not_retry_or_claim_failure(profile, snapshot, monkeypatch):
    adapter = TextAgentAdapter(profile=profile)
    calls = []

    def lost_reply(*args, **kwargs):
        calls.append(args)
        raise TimeoutError()

    monkeypatch.setattr(adapter, "_request", lost_reply)
    assert adapter.submit(snapshot, str(uuid4())).status == "UNKNOWN"
    assert len(calls) == 1
    assert adapter.query_by_external(str(uuid4())).status == "UNSUPPORTED"


@pytest.mark.parametrize(
    "state,expected",
    [
        ("running", "RUNNING"),
        ("succeeded", "RESULT_READY"),
        ("failed", "FAILED"),
        ("interrupted", None),
        ("unknown", None),
    ],
)
def test_query_original_record_and_no_generation(profile, monkeypatch, state, expected):
    external, record_id = str(uuid4()), str(uuid4())
    adapter = TextAgentAdapter(profile=profile, external_submission_id=external)
    calls = []

    def request(method, path, *args, **kwargs):
        calls.append((method, path))
        return 200, {
            "id": record_id,
            "model_config_id": str(profile.model_config_id),
            "status": state,
            "content_expired": False,
            "error_code": "model_output" if state == "failed" else None,
            "result_json": {"text": "文案"},
        }

    monkeypatch.setattr(adapter, "_request", request)
    outcome = adapter.query(record_id)
    assert outcome.state == expected
    assert outcome.external_submission_id == external
    assert calls == [("GET", f"/v1/call-records/{record_id}")]


def test_record_with_different_model_configuration_is_rejected(profile, monkeypatch):
    adapter = TextAgentAdapter(profile=profile, external_submission_id=str(uuid4()))
    record_id = str(uuid4())
    monkeypatch.setattr(
        adapter,
        "_request",
        lambda *a, **kw: (
            200,
            {
                "id": record_id,
                "model_config_id": str(uuid4()),
                "status": "succeeded",
                "result_json": {"text": "other configuration"},
            },
        ),
    )
    assert adapter.query(record_id).status == "UNAVAILABLE"


def test_retrieval_returns_bounded_original_bytes_only(profile, monkeypatch):
    adapter = TextAgentAdapter(profile=profile)
    record_id = str(uuid4())
    monkeypatch.setattr(
        adapter,
        "_request",
        lambda *a, **kw: (
            200,
            {
                "id": record_id,
                "model_config_id": str(profile.model_config_id),
                "status": "succeeded",
                "content_expired": False,
                "result_json": {"text": "原文案"},
            },
        ),
    )
    result = adapter.retrieve_original(f"/v1/copy/results/{record_id}")
    assert result.content == "原文案".encode()
    assert result.complete is True
    assert adapter.retrieve_original("https://other.invalid/result").status == "UNSUPPORTED"


def test_profile_hides_credentials_and_rejects_unsafe_endpoints(profile):
    assert "private-service-key" not in repr(profile)
    assert "private-service-key" not in json.dumps(profile.model_dump(mode="json"))
    for url in [
        "http://user:pass@localhost:8000",
        "http://localhost:8000/?x=1",
        "http://localhost:8000/#fragment",
        "ftp://localhost",
        "http://localhost/../x",
    ]:
        with pytest.raises(ValueError):
            TextAgentProfile(**{**profile.model_dump(), "base_url": url})


def agent_record(profile):
    from app.catalog.schemas import AgentVersion

    value = AgentVersion(
        agent_id=uuid4(),
        version="text-v1",
        kind="copy",
        name="文案 Agent",
        mode="mock",
        test_only=True,
        enabled=True,
        protocol_version="text-agent-v1",
        secret_configured=True,
        input_support=dict(
            product_required_fields=["name"],
            instruction_required=False,
            min_materials=0,
            max_materials=0,
        ),
        policy_versions={},
    )
    return SimpleNamespace(
        agent_id=str(value.agent_id),
        version=value.version,
        snapshot=value.model_dump(mode="json"),
        endpoint=profile.base_url,
        secret_ref="text-local-v1",
    )


def test_registry_requires_explicit_profile_and_exact_endpoint(profile):
    from app.agents.registry import AgentRegistry

    record = agent_record(profile)
    registry = AgentRegistry(mode="mock", test_only=True)
    with pytest.raises(LookupError):
        registry.bind_version(record)
    registry = AgentRegistry(mode="mock", test_only=True, text_profiles={"text-local-v1": profile})
    binding = registry.bind_version(record)
    assert isinstance(binding.adapter, TextAgentAdapter)
    assert binding.adapter.test_only is False
    record.endpoint = "https://other.invalid"
    with pytest.raises(LookupError):
        registry.bind_version(record)


def test_profile_change_does_not_reuse_original_binding_digest(profile):
    from app.agents.registry import AgentRegistry

    record = agent_record(profile)
    first = AgentRegistry(
        mode="mock", test_only=True, text_profiles={"text-local-v1": profile}
    ).bind_version(record)
    updated = profile.model_copy(update={"model_config_id": uuid4()})
    second = AgentRegistry(
        mode="mock", test_only=True, text_profiles={"text-local-v1": updated}
    ).bind_version(record)
    assert first.endpoint_digest != second.endpoint_digest


def test_runtime_settings_accept_named_secret_profiles(profile):
    from app.config import Settings

    settings = Settings(text_agent_profiles={"text-local-v1": profile})
    assert settings.text_agent_profiles["text-local-v1"].model_config_id == profile.model_config_id
    assert Settings().text_agent_profiles == {}
