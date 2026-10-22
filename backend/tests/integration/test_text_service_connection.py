"""Real web MySQL persistence and controlled HTTP textAgent model configuration calls."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select, text

from app.admin.models import TextServiceConnection
from app.agents.service_connection import read_service_connection
from app.audit.models import AuditEvent
from app.auth.routes import get_session, require_active_principal, require_csrf
from app.common.types import Principal
from app.config import Settings
from app.main import create_app
from tests.integration.test_admin_access import identity
from tests.unit.test_text_model_configs import model_view

ROOT = "/api/v1/admin/text-service-connection"
MODELS = "/api/v1/admin/text-model-configs"


@pytest.fixture
def platform(db_session):
    actor = identity(db_session)
    # Reset only inside the fixture's rollback transaction; prior test state is restored.
    row = db_session.get(TextServiceConnection, "text")
    row.base_url = row.key_ciphertext = row.updated_at = row.updated_by = None
    row.default_model_id = None
    row.revision = row.default_revision = 0
    db_session.flush()
    settings = Settings(text_service_encryption_key=Fernet.generate_key().decode())
    app = create_app(settings)
    principal = Principal(
        user_id=UUID(actor["id"]), session_id=UUID(actor["sid"]), role="admin", auth_version=0,
    )
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[require_active_principal] = lambda: principal
    app.dependency_overrides[require_csrf] = lambda: None
    with TestClient(app) as client:
        yield client, db_session, settings, actor


@pytest.fixture
def text_server():
    calls = []
    result = model_view()

    class Handler(BaseHTTPRequestHandler):
        def handle_request(self):
            payload = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            calls.append((self.command, self.path, self.headers, payload))
            listing = self.command == "GET" and self.path.split("?")[0] == "/v1/model-configs"
            body = {"items": [result], "next_cursor": None} if listing else result
            raw = json.dumps(body).encode()
            self.send_response(201 if self.command == "POST" else 200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        do_GET = do_POST = do_PATCH = handle_request

        def log_message(self, *a):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", calls, result
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def save(client, url, revision=0, key="TEST_ONLY_service_key"):
    return client.patch(ROOT, json={
        "base_url": url, "expected_revision": revision,
        "service_key": key, "reason": "TEST_ONLY configure service",
    })


def test_connection_persists_only_in_web_and_is_read_after_session_expiry(platform, text_server):
    client, session, settings, actor = platform
    url, calls, _ = text_server
    assert save(client, url).status_code == 200
    assert not calls  # Saving a connection does not create or modify any remote model.
    session.expire_all()
    row = session.get(TextServiceConnection, "text")
    assert row.base_url == url
    assert row.updated_by == actor["id"]
    assert b"TEST_ONLY_service_key" not in row.key_ciphertext
    assert read_service_connection(session, settings).service_key.get_secret_value() == (
        "TEST_ONLY_service_key"
    )
    assert client.get(ROOT).json()["has_service_key"] is True
    assert "TEST_ONLY_service_key" not in client.get(ROOT).text
    audits = session.scalars(select(AuditEvent).where(AuditEvent.actor_id == actor["id"])).all()
    assert len(audits) == 1
    assert audits[0].changes == {"revision": 1, "key_changed": True}


def test_database_key_rotation_immediately_changes_remote_calls_without_model_copies(
    platform, text_server,
):
    client, session, _, actor = platform
    url, calls, result = text_server
    assert save(client, url).status_code == 200
    assert client.get(MODELS).status_code == 200
    assert calls[-1][2]["Authorization"] == "Bearer TEST_ONLY_service_key"
    assert save(client, url, revision=1, key="TEST_ONLY_rotated").status_code == 200
    assert client.get(MODELS).status_code == 200
    assert calls[-1][2]["Authorization"] == "Bearer TEST_ONLY_rotated"
    created = client.post(MODELS, json={
        "reason": "TEST_ONLY remote model create",
        "config": {"name": "TEST_ONLY", "model": "model", "base_url": "https://model.example",
                   "api_key": "TEST_ONLY_model_key"},
    })
    assert created.status_code == 201
    assert created.json()["id"] == result["id"]
    assert json.loads(calls[-1][3])["api_key"] == "TEST_ONLY_model_key"
    assert client.patch(MODELS + "/" + result["id"], json={
        "reason": "TEST_ONLY remote disable", "expected_revision": 2,
        "config": {"enabled": False},
    }).status_code == 200
    assert calls[-1][0] == "PATCH"
    assert calls[-1][2]["If-Match"] == '"2"'
    assert json.loads(calls[-1][3]) == {"enabled": False}
    rows = session.execute(text("SELECT * FROM text_service_connections")).mappings().all()
    assert len(rows) == 1
    assert "TEST_ONLY_model_key" not in repr(rows)
    audits = session.scalars(select(AuditEvent).where(AuditEvent.actor_id == actor["id"])).all()
    assert len(audits) == 4
    assert "TEST_ONLY_model_key" not in repr([a.changes for a in audits])


def test_corrupt_ciphertext_does_not_fall_back_to_an_environment_service(platform, text_server):
    client, session, settings, _ = platform
    url, calls, _ = text_server
    assert save(client, url).status_code == 200
    row = session.get(TextServiceConnection, "text")
    row.key_ciphertext = b"corrupt"
    session.flush()
    settings.text_model_service = {"base_url": url, "service_key": "TEST_ONLY_old_env_key"}
    response = client.get(MODELS)
    assert response.status_code == 503
    assert "解密" in response.json()["error"]["message"]
    assert not calls


def test_wrong_master_key_cannot_silently_accept_a_blank_key_update(platform, text_server):
    client, _, settings, _ = platform
    url, _, _ = text_server
    assert save(client, url).status_code == 200
    settings.text_service_encryption_key = SecretStr(Fernet.generate_key().decode())
    response = client.patch(ROOT, json={
        "base_url": url, "expected_revision": 1, "reason": "TEST_ONLY blank key update",
    })
    assert response.status_code == 503
    assert client.get(ROOT).json()["revision"] == 1


def test_default_model_provisions_internal_agent_and_origin_change_clears_selection(
    platform, text_server,
):
    from app.agents.text_runtime import DATABASE_PROFILE, resolve_text_profile
    from app.catalog.models import AgentRecord

    client, session, settings, _ = platform
    url, calls, model = text_server
    assert save(client, url).status_code == 200
    response = client.patch("/api/v1/admin/text-default-model", json={
        "model_config_id": model["id"], "expected_revision": 0,
        "expected_connection_revision": 1, "reason": "TEST_ONLY default selection",
    })
    assert response.status_code == 200, response.text
    session.expire_all()
    assert client.get("/api/v1/admin/text-default-model").json()["model_config_id"] == model["id"]
    assert resolve_text_profile(session, settings).model_config_id == UUID(model["id"])
    assert calls[-1][2]["Authorization"] == "Bearer TEST_ONLY_service_key"
    records = session.scalars(select(AgentRecord).where(
        AgentRecord.secret_ref == DATABASE_PROFILE,
    )).all()
    assert records
    assert all(record.endpoint == DATABASE_PROFILE for record in records)
    original_head = next(a for a in client.get('/api/v1/admin/agents').json()
                         if a['kind'] == 'copy')
    model['supports_images'] = True
    response = client.patch('/api/v1/admin/text-default-model', json={
        'model_config_id': model['id'], 'expected_revision': 1,
        'expected_connection_revision': 1, 'reason': 'TEST_ONLY capability switch',
    })
    assert response.status_code == 200, response.text
    updated_head = next(a for a in client.get('/api/v1/admin/agents').json()
                        if a['agent_id'] == original_head['agent_id'])
    assert updated_head['version'] == original_head['version']
    assert save(client, "http://127.0.0.1:19999", revision=1).status_code == 200
    assert client.get("/api/v1/admin/text-default-model").json()["model_config_id"] is None
