"""Service connection API validation, encryption, permissions and conflict handling."""

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

ROOT = "/api/v1/admin/text-service-connection"


@pytest.fixture
def connection_api(monkeypatch):
    from app.admin import text_models

    monkeypatch.setattr(text_models, "authorize_admin", lambda *a: None)
    # The new routes use the same authorization boundary as the model gateway.
    app = create_app(Settings())
    row = SimpleNamespace(
        slot="text", base_url=None, key_ciphertext=None, revision=0,
        updated_at=None, updated_by=None,
    )
    records = []
    session = SimpleNamespace(get=lambda *a, **kw: row, add=records.append, commit=lambda: None)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[require_active_principal] = lambda: SimpleNamespace(user_id=uuid4())
    app.dependency_overrides[require_csrf] = lambda: None
    return TestClient(app), app, row, records


def body(**changes):
    return dict(
        expected_revision=0, base_url="http://127.0.0.1:8000",
        service_key="TEST_ONLY_service_key", reason="设置服务连接", **changes,
    )


def test_unconfigured_connection_is_readable_without_a_master_key(connection_api):
    client, _, _, _ = connection_api
    response = client.get(ROOT)
    assert response.status_code == 200
    assert response.json() == {
        "base_url": None, "has_service_key": False, "revision": 0, "updated_at": None,
    }


def test_missing_master_key_cannot_store_a_plaintext_credential(connection_api):
    client, _, row, records = connection_api
    response = client.patch(ROOT, json=body())
    assert response.status_code == 503
    assert "加密" in response.json()["error"]["message"]
    assert row.key_ciphertext is None
    assert not records
    assert "TEST_ONLY_service_key" not in response.text


def test_service_key_is_encrypted_write_only_and_retained_on_blank_edit(connection_api):
    client, app, row, records = connection_api
    app.state.settings.text_service_encryption_key = SecretStr(Fernet.generate_key().decode())
    response = client.patch(ROOT, json=body())
    assert response.status_code == 200
    assert response.json()["revision"] == 1
    assert response.json()["has_service_key"] is True
    assert b"TEST_ONLY_service_key" not in row.key_ciphertext
    assert "TEST_ONLY_service_key" not in response.text + repr(records)
    encrypted = row.key_ciphertext
    response = client.patch(ROOT, json={
        "base_url": "http://127.0.0.1:8000", "expected_revision": 1, "reason": "保持密钥",
    })
    assert response.status_code == 200
    assert row.key_ciphertext == encrypted
    assert response.json()["revision"] == 2


def test_stale_version_and_address_change_do_not_reuse_a_credential(connection_api):
    client, app, row, _ = connection_api
    app.state.settings.text_service_encryption_key = SecretStr(Fernet.generate_key().decode())
    assert client.patch(ROOT, json=body()).status_code == 200
    assert client.patch(ROOT, json=body()).status_code == 409
    response = client.patch(ROOT, json={
        "base_url": "http://127.0.0.1:9000", "expected_revision": 1, "reason": "改变地址",
    })
    assert response.status_code == 422
    assert row.base_url == "http://127.0.0.1:8000"
    assert row.revision == 1


@pytest.mark.parametrize("url", [
    "http://user:password@localhost:8000", "http://localhost:8000/v1", "http://localhost:bad",
])
def test_invalid_origin_is_rejected(connection_api, url):
    client, _, _, _ = connection_api
    payload = body()
    payload["base_url"] = url
    assert client.patch(ROOT, json=payload).status_code == 422


def test_admin_and_csrf_protect_service_settings(connection_api, monkeypatch):
    from app.admin import text_models

    client, app, _, records = connection_api

    def deny(*a):
        raise HTTPException(403)

    monkeypatch.setattr(text_models, "authorize_admin", deny)
    assert client.get(ROOT).status_code == 403
    assert client.patch(ROOT, json=body()).status_code == 403
    monkeypatch.setattr(text_models, "authorize_admin", lambda *a: None)

    def deny_csrf():
        raise HTTPException(403)

    app.dependency_overrides[require_csrf] = deny_csrf
    assert client.patch(ROOT, json=body()).status_code == 403
    assert not records
