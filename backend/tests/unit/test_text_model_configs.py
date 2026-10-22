import json
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.auth.routes import get_session, require_active_principal, require_csrf
from app.config import Settings
from app.main import create_app


def model_view():
    return dict(
        id=str(uuid4()),
        name="文本模型",
        provider="openai_chat",
        base_url="https://models.example/v1",
        model="chosen-model",
        supports_images=False,
        timeout_seconds=60,
        temperature=None,
        max_tokens=None,
        has_api_key=True,
        enabled=True,
        revision=3,
        created_at="2026-10-15T00:00:00Z",
        updated_at="2026-10-15T00:00:00Z",
    )


@pytest.fixture
def gateway(monkeypatch):
    from app.admin import text_models as routes
    from app.agents import model_configs as upstream

    calls, audits = [], []
    result = {"status": 200, "body": {"items": [model_view()], "next_cursor": None}}

    class Response(BytesIO):
        status = 200

        def __init__(self):
            super().__init__(json.dumps(result["body"]).encode())
            self.status = result["status"]

    def open_request(request, timeout):
        calls.append(request)
        return Response()

    monkeypatch.setattr(upstream, "build_opener", lambda *a: SimpleNamespace(open=open_request))
    monkeypatch.setattr(routes, "authorize_admin", lambda *a: None)
    session = SimpleNamespace(add=audits.append, commit=lambda: None)
    master = Fernet.generate_key()
    connection = SimpleNamespace(
        base_url="http://127.0.0.1:8000",
        key_ciphertext=Fernet(master).encrypt(json.dumps({
            "purpose": "text-service-connection", "base_url": "http://127.0.0.1:8000",
            "service_key": "private-service-key",
        }).encode()),
    )
    session.get = lambda *a, **kw: connection
    app = create_app(
        Settings(
            database_url=None,
            redis_url=None,
            text_model_service={
                "base_url": "http://127.0.0.1:8000",
                "service_key": SecretStr("private-service-key"),
            },
            text_service_encryption_key=SecretStr(master.decode()),
        )
    )
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[require_active_principal] = lambda: SimpleNamespace(user_id=uuid4())
    app.dependency_overrides[require_csrf] = lambda: None
    return TestClient(app), calls, audits, result, app


def test_list_is_server_authenticated_and_drops_unexpected_secrets(gateway):
    client, calls, _, result, _ = gateway
    result["body"]["items"][0]["api_key"] = "must-not-leak"
    response = client.get("/api/v1/admin/text-model-configs?cursor=a%2Fb")
    assert response.status_code == 200
    assert "must-not-leak" not in response.text
    assert calls[0].get_header("Authorization") == "Bearer private-service-key"
    assert calls[0].full_url == "http://127.0.0.1:8000/v1/model-configs?limit=20&cursor=a%2Fb"


@pytest.mark.parametrize("effort", [
    None, "none", "minimal", "low", "medium", "high", "xhigh", "max",
])
def test_reasoning_effort_round_trips_through_model_management(gateway, effort):
    client, calls, _, result, _ = gateway
    model = dict(model_view(), reasoning_effort=effort)
    result["body"] = model
    response = client.patch("/api/v1/admin/text-model-configs/" + model["id"], json={
        "expected_revision": 3, "config": {"reasoning_effort": effort},
    })
    assert response.status_code == 200, response.text
    assert response.json()["reasoning_effort"] == effort
    assert json.loads(calls[-1].data) == {"reasoning_effort": effort}
    response = client.get("/api/v1/admin/text-model-configs/" + model["id"])
    assert response.json()["reasoning_effort"] == effort
    result["body"] = {"items": [model], "next_cursor": None}
    page = client.get("/api/v1/admin/text-model-configs").json()
    assert page["items"][0]["reasoning_effort"] == effort


def test_reasoning_effort_is_forwarded_on_create_and_invalid_values_are_rejected(gateway):
    client, calls, _, result, _ = gateway
    model = dict(model_view(), reasoning_effort="low")
    result["body"] = model
    config = {key: model[key] for key in (
        "name", "base_url", "model", "reasoning_effort",
    )}
    response = client.post("/api/v1/admin/text-model-configs", json={
        "config": dict(config, api_key="TEST_ONLY_model_key"),
    })
    assert response.status_code == 201, response.text
    assert json.loads(calls[-1].data)["reasoning_effort"] == "low"
    count = len(calls)
    response = client.patch("/api/v1/admin/text-model-configs/" + model["id"], json={
        "expected_revision": 3, "config": {"reasoning_effort": "unsupported"},
    })
    assert response.status_code == 422
    assert len(calls) == count


def test_patch_uses_revision_omits_blank_key_and_audits_no_secrets(gateway):
    client, calls, audits, result, _ = gateway
    result["body"] = model_view()
    config_id = result["body"]["id"]
    response = client.patch(
        f"/api/v1/admin/text-model-configs/{config_id}",
        json={"expected_revision": 2, "config": {"model": "new-model"}},
    )
    assert response.status_code == 200
    assert calls[0].get_header("If-match") == '"2"'
    assert json.loads(calls[0].data) == {"model": "new-model"}
    assert audits[0].changes == {"revision": 3}
    assert audits[0].reason == "保存文本模型配置"


def test_create_sends_write_only_key_without_putting_it_in_audit(gateway):
    client, calls, audits, result, _ = gateway
    result.update(status=201, body=model_view())
    response = client.post(
        "/api/v1/admin/text-model-configs",
        json={
            "config": {
                "name": "测试",
                "base_url": "https://models.example/v1",
                "model": "model",
                "api_key": "private-model-key",
            },
        },
    )
    assert response.status_code == 201
    assert json.loads(calls[0].data)["api_key"] == "private-model-key"
    assert "private-model-key" not in response.text + repr(audits[0].changes)


@pytest.mark.parametrize("status,expected", [(412, 409), (401, 503), (502, 503), (422, 422)])
def test_upstream_errors_are_sanitized_and_not_retried(gateway, status, expected):
    client, calls, audits, result, _ = gateway
    result.update(status=status, body={"error": {"message": "private-key-from-upstream"}})
    response = client.patch(
        f"/api/v1/admin/text-model-configs/{uuid4()}",
        json={"expected_revision": 2, "reason": "调整", "config": {"enabled": False}},
    )
    assert response.status_code == expected
    assert "private-key" not in response.text
    assert len(calls) == 1
    assert not audits


@pytest.mark.parametrize("status,hint", [(401, "无效"), (403, "权限不足")])
@pytest.mark.parametrize("method", ["GET", "POST", "PATCH"])
def test_service_auth_failure_points_to_connection_without_logging_out_user(gateway, status, hint,
                                                                          method):
    client, calls, audits, result, _ = gateway
    result.update(status=status, body={"error": {"message": "private-key-from-upstream"}})
    path = "/api/v1/admin/text-model-configs"
    payload = None
    if method == "POST":
        payload = {"reason": "新增模型", "config": {
            "name": "测试", "base_url": "https://models.example/v1", "model": "model",
            "api_key": "private-model-key",
        }}
    elif method == "PATCH":
        path += f"/{uuid4()}"
        payload = {"expected_revision": 2, "reason": "调整", "config": {"enabled": False}}
    response = client.request(method, path, json=payload)
    # Upstream authentication is distinct from the platform user's login.
    assert response.status_code == 503
    message = response.json()["error"]["message"]
    assert "服务访问 Key" in message
    assert "配置服务连接" in message
    assert hint in message
    if status == 401:
        assert "模型密钥" in message
    else:
        assert "configs:read" in message and "configs:write" in message
    assert "private-key" not in response.text
    assert "private-model-key" not in response.text
    assert len(calls) == 1
    assert not audits


def test_admin_and_csrf_fail_before_any_upstream_call(gateway, monkeypatch):
    from app.admin import text_models as routes

    client, calls, _, _, app = gateway

    def denied(*a):
        raise HTTPException(403)

    monkeypatch.setattr(routes, "authorize_admin", denied)
    assert client.get("/api/v1/admin/text-model-configs").status_code == 403

    def csrf_denied():
        raise HTTPException(403)

    app.dependency_overrides[require_csrf] = csrf_denied
    assert client.post("/api/v1/admin/text-model-configs", json={}).status_code == 403
    assert not calls


def test_unconfigured_service_fails_closed():
    from app.agents.model_configs import TextModelClient, TextModelError

    with pytest.raises(TextModelError) as error:
        TextModelClient(None)
    assert error.value.status_code == 503


def test_read_latest_config_by_id_is_not_limited_to_the_first_page(gateway):
    client, calls, _, result, _ = gateway
    result["body"] = model_view()
    config_id = result["body"]["id"]
    response = client.get(f"/api/v1/admin/text-model-configs/{config_id}")
    assert response.status_code == 200
    assert calls[0].full_url == f"http://127.0.0.1:8000/v1/model-configs/{config_id}"


@pytest.mark.parametrize("config", [{}, {"api_key": None}, {"api_key": ""}, {"enabled": None}])
def test_invalid_patch_is_rejected_before_upstream(gateway, config):
    client, calls, _, _, _ = gateway
    response = client.patch(
        f"/api/v1/admin/text-model-configs/{uuid4()}",
        json={"expected_revision": 3, "reason": "校验配置", "config": config},
    )
    assert response.status_code == 422
    assert not calls
