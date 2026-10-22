import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from pydantic import ValidationError

from app.catalog.models import ParameterConfig, ParameterHead
from app.catalog.parameters import ParameterConfigUpdate, read_parameters, update_parameters
from app.config import Settings


@pytest.fixture
def config_store():
    head, rows, audits = SimpleNamespace(version=None), {}, []

    def add(row):
        if isinstance(row, ParameterConfig):
            rows[row.version] = row
        else:
            audits.append(row)

    session = SimpleNamespace(
        get=lambda model, key, **kw: head if model is ParameterHead else rows.get(str(key)),
        add=add, flush=lambda: None,
    )
    settings = Settings(text_service_encryption_key=Fernet.generate_key().decode())
    return session, settings, rows, audits


def update(version=None, **kw):
    return ParameterConfigUpdate(
        expected_version=version, text_price=0, image_price=None, video_price=None, **kw,
    )


def test_assist_configuration_encrypts_preserves_and_clears_credentials(config_store):
    from app.assist.configuration import read_assist_connection

    session, settings, rows, audits = config_store
    saved = update_parameters(session, "mock", update(
        assist_base_url="https://models.example/v1/", assist_model="prompt-model",
        assist_api_key="private-assist-key",
    ), uuid4(), settings=settings)
    assert saved.assist_base_url == "https://models.example/v1"
    assert saved.has_assist_api_key is True
    assert "private-assist-key" not in saved.model_dump_json() + repr(audits[0].changes)
    assert b"private-assist-key" not in rows[str(saved.version)].assist_key_ciphertext
    connection = read_assist_connection(session, settings)
    assert connection.api_key.get_secret_value() == "private-assist-key"
    assert connection.model == "prompt-model"

    changed = update_parameters(session, "mock", update(
        saved.version, assist_model="new-model",
    ), uuid4(), settings=settings)
    assert read_assist_connection(session, settings).api_key == connection.api_key
    assert changed.assist_model == "new-model"
    assert len(rows) == 2
    with pytest.raises(HTTPException) as conflict:
        update_parameters(session, "mock", update(saved.version), uuid4(), settings=settings)
    assert conflict.value.status_code == 409
    cleared = update_parameters(session, "mock", update(
        changed.version, assist_base_url=None, assist_model=None,
    ), uuid4(), settings=settings)
    assert not cleared.has_assist_api_key and cleared.assist_model is None
    assert read_parameters(session, "mock").text_price == 0
    with pytest.raises(HTTPException) as unavailable:
        read_assist_connection(session, settings)
    assert unavailable.value.status_code == 503


def test_new_origin_requires_new_key_and_invalid_urls_are_rejected(config_store):
    session, settings, _, _ = config_store
    saved = update_parameters(session, "mock", update(
        assist_base_url="http://127.0.0.1:9000/v1", assist_model="model",
        assist_api_key="private-key",
    ), uuid4(), settings=settings)
    with pytest.raises(HTTPException) as denied:
        update_parameters(session, "mock", update(
            saved.version, assist_base_url="https://different.example/v1",
        ), uuid4(), settings=settings)
    assert denied.value.status_code == 422
    for url in ("file:///tmp/key", "https://key@host/v1", "https://host/v1?q=key",
                "http://169.254.169.254/latest", "https://host/../secret", "https://host:bad/v1"):
        with pytest.raises(ValidationError):
            update(assist_base_url=url)
    with pytest.raises(ValidationError):
        update(assist_api_key="bad\nkey")


def provider_request():
    from app.assist.provider import ProviderRequest
    from app.catalog.schemas import AgentVersion, single_spec

    agent = AgentVersion(
        agent_id=uuid4(), version="v1", kind="copy", name="文本", mode="mock",
        test_only=True, enabled=True, protocol_version="v1", secret_configured=True,
        policy_versions={}, input_support=dict(product_required_fields=["name"],
        instruction_required=False, min_materials=0, max_materials=3),
    )
    return ProviderRequest(draft=dict(
        agent_id=agent.agent_id, agent_version="v1", original="写一条简洁文案",
        product={"name": "杯子"}, parameters={}, material_versions=[],
    ), agent=agent, spec=single_spec(agent))


@pytest.mark.parametrize("complete", [
    "请围绕杯子写简洁文案。",
    "围绕提供的商品写简洁介绍，无需补充商品价格和材质。",
    "围绕提供的商品写简洁介绍，不需要用户补充信息。",
])
def test_provider_posts_only_to_admin_configured_endpoint_with_grounding(monkeypatch, complete):
    from app.assist import provider
    from app.assist.configuration import AssistConnection

    requests = []

    def send(request):
        requests.append(request)
        body = {"choices": [{"message": {"content": complete}}]}
        return httpx.Response(200, json=body)

    client = httpx.AsyncClient
    monkeypatch.setattr(provider.httpx, "AsyncClient", lambda **kw: client(
        **kw, transport=httpx.MockTransport(send),
    ))
    connection = AssistConnection(version=uuid4(), base_url="https://models.example/v1",
                                  model="chosen-model", api_key="secret-assist-key")
    result = asyncio.run(provider.OpenAIPromptAssistProvider(connection, timeout=2).prepare(
        provider_request(),
    ))
    assert result.proposed == complete
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://models.example/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer secret-assist-key"
    payload = json.loads(request.content)
    assert payload["model"] == "chosen-model" and payload["stream"] is False
    assert "不得" in payload["messages"][0]["content"]
    user = json.loads(payload["messages"][1]["content"])
    assert user["product"] == {"name": "杯子"} and user["original"] == "写一条简洁文案"
    assert "secret-assist-key" not in request.content.decode()


@pytest.mark.parametrize("status,body,expected", [
    (401, {"error": "secret-from-upstream"}, 503),
    (429, {}, 429), (302, {}, 503), (200, {"choices": []}, 503),
    (200, {"choices": [{"message": {"content": "   "}}]}, 503),
    (200, {"choices": [{"message": {"content": "x" * 20001}}]}, 503),
])
def test_provider_failures_are_sanitized(monkeypatch, status, body, expected):
    from app.assist import provider
    from app.assist.configuration import AssistConnection

    client = httpx.AsyncClient
    monkeypatch.setattr(provider.httpx, "AsyncClient", lambda **kw: client(
        **kw, transport=httpx.MockTransport(lambda request: httpx.Response(status, json=body)),
    ))
    connection = AssistConnection(version=uuid4(), base_url="https://models.example",
                                  model="model", api_key="private-key")
    with pytest.raises(HTTPException) as rejected:
        asyncio.run(provider.OpenAIPromptAssistProvider(connection, timeout=2).prepare(
            provider_request(),
        ))
    assert rejected.value.status_code == expected
    assert "secret" not in str(rejected.value.detail)


@pytest.mark.parametrize("mode", ["mock", "production"])
@pytest.mark.parametrize("product,missing", [
    ({"name": "杯子"}, []),
    ({}, ["name"]),
])
def test_configured_live_service_uses_database_model_without_policy_or_billing(config_store,
                                                                      monkeypatch, mode,
                                                                      product, missing):
    from app.assist import service
    from app.assist.models import AssistRecord
    from app.assist.provider import ProviderResponse

    session, settings, _, _ = config_store
    settings = settings.model_copy(update={"mode": mode, "test_only": mode == "mock"})
    # No D-05 or environment provider setting is present: the explicit saved
    # independent connection enables assistance, without choosing a quota policy.
    saved = update_parameters(session, mode, update(
        assist_base_url="https://models.example/v1", assist_model="prompt-model",
        assist_api_key="private-assist-key",
    ), uuid4(), settings=settings)
    context = provider_request()
    context.draft.product = product
    receipt = []
    session.rollback = lambda: None
    session.scalar = lambda *a, **kw: receipt[0] if receipt else None
    session.add = receipt.append
    monkeypatch.setattr(service, "authenticate", lambda *a: None)
    monkeypatch.setattr(service, "CatalogService", lambda *a, **kw: SimpleNamespace(
        single_context=lambda *a: (context.spec, context.agent),
    ))
    calls = []

    async def prepare(self, request):
        calls.append(self.connection.model)
        return ProviderResponse(proposed="请围绕提供的商品写一条简洁自然的介绍文案。")

    monkeypatch.setattr(service.OpenAIPromptAssistProvider, "prepare", prepare)
    principal = SimpleNamespace(user_id=uuid4())
    result = service.AssistService(session, settings).prepare_prompt(
        principal, context.draft, None, key="same-request",
    )
    assert result.original == "写一条简洁文案"
    assert result.test_only is False and result.policy_version == str(saved.version)
    assert result.missing_facts == missing
    assert len(receipt) == 1 and isinstance(receipt[0], AssistRecord)
    replay = service.AssistService(session, settings).prepare_prompt(
        principal, context.draft, None, key="same-request",
    )
    assert replay == result and calls == ["prompt-model"]


@pytest.mark.parametrize("kind", ["copy", "image", "video"])
@pytest.mark.parametrize("incomplete", [
    "请介绍杯子。材质：待用户补充。",
    "请介绍杯子。目标受众：[待补充]。",
    "请补充商品价格后再完善指令。",
    "请介绍杯子。品牌：待填写。",
    "请介绍杯子。价格：TBD。",
    "请提供商品材质后再创作。",
    "商品材质 TODO 内容稍后填写。",
])
def test_provider_repairs_incomplete_instructions_before_returning(monkeypatch, kind, incomplete):
    from app.assist import provider
    from app.assist.configuration import AssistConnection

    requests = []
    complete = "围绕提供的商品创作，突出主体，保持表达清晰自然。"

    def send(request):
        requests.append(json.loads(request.content))
        content = incomplete if len(requests) == 1 else complete
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    client = httpx.AsyncClient
    monkeypatch.setattr(provider.httpx, "AsyncClient", lambda **kw: client(
        **kw, transport=httpx.MockTransport(send),
    ))
    connection = AssistConnection(version=uuid4(), base_url="https://models.example/v1",
                                  model="model", api_key="private-key")
    request = provider_request()
    request.agent = request.agent.model_copy(update={"kind": kind})
    result = asyncio.run(
        provider.OpenAIPromptAssistProvider(connection, timeout=2).prepare(request),
    )
    assert result.proposed == complete
    assert len(requests) == 2
    assert json.loads(requests[1]["messages"][1]["content"])["product"] == {"name": "杯子"}


def test_provider_rejects_persistent_placeholders(monkeypatch):
    from app.assist import provider
    from app.assist.configuration import AssistConnection

    requests = []

    def send(request):
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {
            "content": "商品材质：待用户补充。",
        }}]})

    client = httpx.AsyncClient
    monkeypatch.setattr(provider.httpx, "AsyncClient", lambda **kw: client(
        **kw, transport=httpx.MockTransport(send),
    ))
    connection = AssistConnection(version=uuid4(), base_url="https://models.example/v1",
                                  model="model", api_key="private-key")
    with pytest.raises(HTTPException) as rejected:
        asyncio.run(provider.OpenAIPromptAssistProvider(connection, timeout=2).prepare(
            provider_request(),
        ))
    assert rejected.value.status_code == 503
    assert len(requests) == 2


@pytest.mark.parametrize("repair_first", [False, True])
def test_slow_response_is_cancelled_and_closed_at_total_deadline(monkeypatch, repair_first):
    from time import monotonic

    from app.assist import provider
    from app.assist.configuration import AssistConnection

    closed = []
    requests = []

    class SlowStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            while True:
                yield b" "
                await asyncio.sleep(0.01)

        async def aclose(self):
            closed.append(True)

    def send(request):
        requests.append(request)
        if repair_first and len(requests) == 1:
            return httpx.Response(200, json={"choices": [{"message": {
                "content": "商品材质：待用户补充。",
            }}]})
        return httpx.Response(200, stream=SlowStream())

    client = httpx.AsyncClient
    monkeypatch.setattr(provider.httpx, "AsyncClient", lambda **kw: client(
        **kw, transport=httpx.MockTransport(send),
    ))
    connection = AssistConnection(version=uuid4(), base_url="https://models.example/v1",
                                  model="model", api_key="private-key")
    started = monotonic()
    with pytest.raises(HTTPException) as timeout:
        asyncio.run(provider.OpenAIPromptAssistProvider(connection, timeout=0.05).prepare(
            provider_request(),
        ))
    assert timeout.value.status_code == 504
    assert monotonic() - started < 0.5
    assert closed == [True]
    assert len(requests) == (2 if repair_first else 1)


@pytest.mark.parametrize("kind,parameters,allowed", [
    ("image", {}, True), ("image", {"platform": "pinduoduo"}, True),
    ("image", {"output_type": "detail_page"}, True),
    ("image", {"platform": "taobao", "output_type": "pdd_white_background"}, True),
    ("image", {"platform": "unknown"}, False), ("copy", {"platform": "taobao"}, False),
    ("video", {}, True), ("video", {"first_frame_file_id": "missing"}, False),
])
def test_assistance_validates_only_supplied_media_choices(kind, parameters, allowed):
    from app.assist.service import validate_draft_parameters

    request = provider_request()
    request.agent = request.agent.model_copy(update={"kind": kind})
    request.draft.parameters = parameters
    if allowed:
        validate_draft_parameters(request.draft, request.agent, request.spec)
    else:
        with pytest.raises(HTTPException) as rejected:
            validate_draft_parameters(request.draft, request.agent, request.spec)
        assert rejected.value.status_code == 422
