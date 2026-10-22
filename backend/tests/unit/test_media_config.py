import inspect
import json
from io import BytesIO
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from app.admin.media_schemas import MediaConnectionUpdate, project_resource, resource_body
from app.agents.media_connection import (
    MediaConnectionHead,
    MediaConnectionRecord,
    connection_view,
    read_media_connection,
    update_media_connection,
)
from app.agents.media_http import MediaClient, MediaServiceError


class MemorySession:
    def __init__(self):
        self.rows = {}
        for kind in ("image", "video"):
            self.add(MediaConnectionHead(kind=kind, revision=0))

    def get(self, model, key, **kwargs):
        return self.rows.get((model, key))

    def add(self, row):
        self.rows[type(row), getattr(row, "id", None) or row.kind] = row

    def flush(self):
        pass


@pytest.fixture
def connection():
    return MemorySession(), SimpleNamespace(
        text_service_encryption_key=SecretStr(Fernet.generate_key().decode())
    )


def save(connection, kind="image", **changes):
    session, settings = connection
    dto = MediaConnectionUpdate(**changes)
    return update_media_connection(session, settings, kind, dto, uuid4())


def test_connection_versions_are_encrypted_and_old_identity_still_reads(connection):
    first = save(
        connection,
        expected_revision=0,
        base_url="https://media.example",
        service_key="private-service",
        default_config_id=uuid4(),
        image_model="fast",
    )
    assert b"private-service" not in first.key_ciphertext
    second = save(connection, expected_revision=1, image_model="base")
    assert first.id != second.id
    old = read_media_connection(*connection, "image", first.id)
    current = read_media_connection(*connection, "image")
    assert old.image_model == "fast" and current.image_model == "base"
    assert old.service_key.get_secret_value() == "private-service"
    assert "private-service" not in connection_view(second).model_dump_json()
    assert connection[0].get(MediaConnectionRecord, first.id) is first


def test_video_audio_preference_is_versioned_with_connection(connection):
    first = save(connection, kind="video", expected_revision=0,
                 base_url="https://video.example", service_key="key")
    save(connection, kind="video", expected_revision=1, video_audio_enabled=True)
    assert read_media_connection(*connection, "video").video_audio_enabled is True
    assert read_media_connection(*connection, "video", first.id).video_audio_enabled is False
    save(connection, kind="video", expected_revision=2, service_key="rotated-key")
    assert read_media_connection(*connection, "video").video_audio_enabled is True


def test_stale_connection_and_origin_change_require_fresh_keys(connection):
    save(
        connection,
        kind="video",
        expected_revision=0,
        base_url="https://media.example",
        service_key="business-key",
        management_key="admin-key",
    )
    with pytest.raises(MediaServiceError) as error:
        save(connection, kind="video", expected_revision=0, service_key="other")
    assert error.value.status_code == 409
    for changes in ({}, {"service_key": "new-business"}):
        with pytest.raises(MediaServiceError):
            save(
                connection,
                kind="video",
                expected_revision=1,
                base_url="https://other.example",
                **changes,
            )
    saved = save(
        connection,
        kind="video",
        expected_revision=1,
        base_url="https://other.example",
        service_key="new",
        management_key="new-admin",
    )
    assert saved.revision == 2


def test_ciphertext_cannot_be_rebound_to_origin_or_kind(connection):
    row = save(connection, expected_revision=0, base_url="https://media.example", service_key="key")
    row.base_url = "https://evil.example"
    with pytest.raises(MediaServiceError):
        read_media_connection(*connection, "image", row.id)
    with pytest.raises(MediaServiceError):
        read_media_connection(*connection, "video", row.id)


def test_connection_status_is_readable_and_replaceable_after_master_key_rotation(connection):
    from app.agents.media_connection import current_connection_view

    save(
        connection,
        kind="video",
        expected_revision=0,
        base_url="https://media.example",
        service_key="old",
        management_key="old-admin",
    )
    connection[1].text_service_encryption_key = SecretStr(Fernet.generate_key().decode())
    assert current_connection_view(*connection, "video").has_management_key is True
    row = save(
        connection, kind="video", expected_revision=1, service_key="new", management_key="new-admin"
    )
    assert row.revision == 2
    assert read_media_connection(*connection, "video").service_key.get_secret_value() == "new"


def test_resource_versions_and_secret_semantics_remain_distinct():
    assert resource_body("image", "services", {"version": 3, "name": "new"}, patch=True) == {
        "version": 3,
        "name": "new",
    }
    for key in ("", None):
        with pytest.raises(MediaServiceError):
            resource_body("image", "services", {"version": 3, "api_key": key}, patch=True)
    assert resource_body(
        "video", "model-profiles", {"expected_version": 4, "secrets": {"api_key": ""}}, patch=True
    )["secrets"] == {"api_key": ""}
    with pytest.raises(MediaServiceError):
        resource_body("video", "model-profiles", {"version": 4}, patch=True)
    with pytest.raises(MediaServiceError):
        resource_body(
            "video",
            "model-profiles",
            {"expected_version": 4, "secrets": {"api_key": "new"}, "clear_secrets": ["api_key"]},
            patch=True,
        )
    with pytest.raises(MediaServiceError):
        resource_body(
            "image",
            "agent-configs",
            {"version": 1, "parameters": {"api_key": "secret"}},
            patch=True,
        )


def test_response_projection_scrubs_nested_secrets_and_preserves_page_contract():
    item = dict(
        profile_id="p",
        name="n",
        role="video",
        adapter="wan",
        base_url=None,
        model=None,
        parameters={
            "max_segment_seconds": 5,
            "api_key": "nested-secret",
            "nested": {"service_key": "must-not-leak"},
        },
        enabled=True,
        version=3,
        has_api_key=True,
        secret_presence={"api_key": True},
        created_at="now",
        updated_at="now",
        secrets={"api_key": "secret"},
    )
    page = project_resource(
        "video",
        "model-profiles",
        {"items": [item], "limit": 20, "offset": 0, "total": 1, "api_key": "outer"},
        listing=True,
    )
    assert page["total"] == 1
    assert page["items"][0]["secret_presence"] == {"api_key": True}
    assert page["items"][0]["parameters"] == {"max_segment_seconds": 5, "nested": {}}
    assert "secret" not in json.dumps(page).replace("secret_presence", "")


@pytest.fixture
def transport(monkeypatch):
    from app.agents import media_http

    state = dict(status=200, body=b'{"ok":true}', headers={"Content-Type": "application/json"})
    calls = []

    class Response(BytesIO):
        def __init__(self):
            super().__init__(state["body"])
            self.status = state["status"]
            self.headers = state["headers"]

    def open_request(request, timeout):
        calls.append(request)
        return Response()

    monkeypatch.setattr(media_http, "build_opener", lambda *a: SimpleNamespace(open=open_request))
    return MediaClient("https://media.example", SecretStr("private-key")), state, calls


@pytest.mark.parametrize(
    "path",
    [
        "https://evil.example/x",
        "//evil.example/x",
        "/a/../x",
        "/%2e%2e/x",
        "/a%2fb",
        "/a\\b",
        "/x#frag",
    ],
)
def test_http_rejects_uncontrolled_paths_before_sending(transport, path):
    client, _, calls = transport
    with pytest.raises(MediaServiceError):
        client.json("GET", path)
    assert not calls


@pytest.mark.parametrize("status", [301, 302, 307, 308, 401, 403, 409, 422, 500])
def test_http_non_success_is_normalized_without_raw_body_or_retry(transport, status):
    client, state, calls = transport
    state.update(status=status, body=b"provider-key-must-not-leak")
    with pytest.raises(MediaServiceError) as error:
        client.json("PATCH", "/api/v1/settings", body={"expected_version": 1})
    assert "provider-key" not in str(error.value)
    assert len(calls) == 1
    assert error.value.status_code in {409, 422, 503}


def test_http_bounds_reads_and_controls_multipart_filename(transport):
    client, state, calls = transport
    client.max_response_bytes = 3
    with pytest.raises(MediaServiceError):
        client.json("GET", "/api/v1/settings")
    client.max_response_bytes = 1000
    state["body"] = b'{"asset_id":"a"}'
    assert client.upload("/api/v1/assets/images", b"bytes", "image/png")["asset_id"] == "a"
    assert b'name="file"; filename="upload.png"' in calls[-1].data
    assert calls[-1].get_header("Authorization") == "Bearer private-key"


def test_http_rejects_truncated_content(transport):
    client, state, _ = transport
    state.update(body=b"abc", headers={"Content-Length": "6", "Content-Type": "video/mp4"})
    with pytest.raises(MediaServiceError):
        client.download("/api/v1/artifacts/a/content")


@pytest.mark.parametrize("status,explanation", [(401, "访问 Key"), (403, "管理 Key")])
def test_http_auth_failure_explains_connection_fix_without_leaking_upstream_body(transport, status, explanation):
    client, state, _ = transport
    state.update(status=status, body=b"private-upstream-secret")
    with pytest.raises(MediaServiceError) as error:
        client.json("GET", "/api/v1/admin/settings")
    assert error.value.status_code == 503
    assert explanation in (error.value.public_message or "")
    assert "private-upstream" not in str(error.value)


def test_http_preserves_upload_size_rejection(transport):
    client, state, _ = transport
    state.update(status=413)
    with pytest.raises(MediaServiceError) as error:
        client.upload("/api/v1/assets", b"bytes", "image/png", fields={"kind": "image"})
    assert error.value.status_code == 413


def test_video_cannot_clear_and_retain_same_secret():
    with pytest.raises(MediaServiceError):
        resource_body(
            "video",
            "model-profiles",
            {"expected_version": 1, "secrets": {"api_key": ""}, "clear_secrets": ["api_key"]},
            patch=True,
        )


def test_managed_identity_contract_is_code_owned():
    from app.agents.media_runtime import managed_media_agent_id, managed_media_input_support

    assert managed_media_agent_id("mock", "image") != managed_media_agent_id("mock", "video")
    assert managed_media_input_support("image") == dict(
        product_required_fields=["name", "category"],
        instruction_required=False,
        min_materials=1,
        max_materials=8,
    )


@pytest.fixture
def gateway(connection, monkeypatch):
    from fastapi import HTTPException

    from app.admin import media_agents as routes
    from app.auth.routes import require_csrf

    session, settings = connection
    settings.mode, settings.test_only = "mock", True
    calls, audits = [], []
    state = {"body": [], "status": 200, "commits": 0, "syncs": []}
    original_add = session.add

    def add(row):
        if hasattr(row, "changes"):
            audits.append(row)
        else:
            original_add(row)

    def commit():
        state["commits"] += 1

    session.add, session.commit = add, commit

    class Client:
        def __init__(self, base_url, key):
            self.key = key.get_secret_value()

        def json(self, method, path, body=None, idempotency_key=None):
            calls.append((self.key, method, path, body, idempotency_key))
            if state["status"] >= 400:
                raise MediaServiceError(state["status"])
            return state["status"], state["body"]

    monkeypatch.setattr(routes, "MediaClient", Client)
    monkeypatch.setattr(routes, "authorize_admin", lambda *a: None)
    monkeypatch.setattr(routes, "sync_media_agent", lambda *a: state["syncs"].append(a[-1]))
    app = SimpleNamespace(
        state=SimpleNamespace(settings=settings), dependency_overrides={require_csrf: lambda: None}
    )

    def request(method, path, **kwargs):
        # Invoke the registered endpoint and its declared CSRF dependency directly.
        # Windows' portable Python blocks creating an asyncio self-pipe before ASGI runs.
        parts = urlsplit(path)
        route = next(
            r
            for r in routes.router.routes
            if method in r.methods and r.path_regex.fullmatch(parts.path)
        )
        values = route.path_regex.fullmatch(parts.path).groupdict()
        parameters = inspect.signature(route.endpoint).parameters
        values.update(
            request=SimpleNamespace(app=app, headers=kwargs.get("headers", {})),
            session=session,
            principal=SimpleNamespace(user_id=uuid4()),
        )
        if "config_id" in values:
            from uuid import UUID

            values["config_id"] = UUID(values["config_id"])
        query = parse_qs(parts.query)
        for key in ("limit", "offset"):
            if key in parameters:
                values[key] = int(query.get(key, [20 if key == "limit" else 0])[0])
        try:
            for dependency in route.dependencies:
                app.dependency_overrides[dependency.dependency]()
            if "dto" in parameters:
                from app.admin.media_schemas import (
                    ImageModelsUpdate, MediaResourceWrite, VideoModelUpdate, VideoAudioUpdate,
                )

                schema = (
                    MediaConnectionUpdate if path.endswith("/connection") else
                    VideoAudioUpdate if path.endswith("/video/audio") else
                    VideoModelUpdate if "/video/models/" in path else
                    ImageModelsUpdate if path.endswith("/models") else MediaResourceWrite
                )
                values["dto"] = schema.model_validate(kwargs.get("json", {}))
            payload = route.endpoint(**values)
            if hasattr(payload, "model_dump"):
                payload = payload.model_dump(mode="json")
            status = route.status_code or 200
        except (MediaServiceError, HTTPException) as error:
            status, payload = error.status_code, {"error": "request failed"}
        return SimpleNamespace(status_code=status, json=lambda: payload, text=json.dumps(payload))

    save(
        connection,
        kind="video",
        expected_revision=0,
        base_url="https://video.example",
        service_key="business-key",
        management_key="management-key",
    )
    save(
        connection,
        kind="image",
        expected_revision=0,
        base_url="https://image.example",
        service_key="image-key",
    )
    return request, calls, audits, state, app


ROOT = "/api/v1/admin/media-agents"


def video_profile():
    return dict(
        profile_id=str(uuid4()),
        name="model",
        role="video",
        adapter="wan",
        base_url="https://provider.example/v1",
        model="chosen-model",
        parameters={},
        enabled=True,
        version=4,
        has_api_key=True,
        secret_presence={"api_key": True},
        created_at="2026-10-15T00:00:00Z",
        updated_at="2026-10-15T00:00:00Z",
    )


def image_service():
    return dict(
        id=str(uuid4()),
        name="images",
        base_url="https://provider.example/v1",
        protocol="openai_images",
        generation_path=None,
        edit_path=None,
        chat_path="/chat",
        enabled=True,
        version=3,
        has_api_key=True,
        created_at="2026-10-15T00:00:00Z",
        updated_at="2026-10-15T00:00:00Z",
    )


def test_gateway_uses_management_key_and_native_pagination(gateway):
    request, calls, _, state, _ = gateway
    state["body"] = {"items": [video_profile()], "limit": 5, "offset": 7, "total": 18}
    response = request("GET", ROOT + "/video/resources/model-profiles?limit=5&offset=7")
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 18
    assert calls[-1][:3] == (
        "management-key",
        "GET",
        "/api/v1/admin/model-profiles?limit=5&offset=7",
    )
    state["body"] = [image_service()]
    response = request("GET", ROOT + "/image/resources/services?limit=5&offset=7")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert calls[-1][:3] == ("image-key", "GET", "/api/v1/services?limit=5&offset=7")


def test_gateway_patch_preserves_native_version_and_audits_only_metadata(gateway):
    request, calls, audits, state, _ = gateway
    state["body"] = image_service()
    identity = state["body"]["id"]
    response = request(
        "PATCH",
        ROOT + "/image/resources/services/" + identity,
        json={"config": {"version": 2, "api_key": "new-private-key"}},
    )
    assert response.status_code == 200, response.text
    assert calls[-1][3] == {"version": 2, "api_key": "new-private-key"}
    assert audits[-1].changes == {"kind": "image", "resource": "services", "version": 3}
    assert "new-private-key" not in str(audits[-1].changes) + response.text
    assert state["syncs"] == ["image"] and state["commits"] == 1


def test_gateway_conflict_and_unsupported_resource_do_not_commit(gateway):
    request, calls, audits, state, _ = gateway
    state["status"] = 409
    response = request(
        "PATCH",
        ROOT + "/video/resources/model-profiles/" + str(uuid4()),
        json={"config": {"expected_version": 2, "name": "draft"}},
    )
    assert response.status_code == 409
    assert not audits and state["commits"] == 0
    count = len(calls)
    assert request("GET", ROOT + "/video/resources/services").status_code == 404
    assert len(calls) == count


def test_gateway_admin_authorization_precedes_upstream(gateway, monkeypatch):
    from fastapi import HTTPException

    from app.admin import media_agents

    request, calls, _, _, _ = gateway

    def deny(*args):
        raise HTTPException(403)

    monkeypatch.setattr(media_agents, "authorize_admin", deny)
    assert request("GET", ROOT + "/video/resources/model-profiles").status_code == 403
    assert (
        request(
            "PATCH",
            ROOT + "/image/connection",
            json={"expected_revision": 1, "image_model": "base"},
        ).status_code
        == 403
    )
    assert not calls


def test_gateway_csrf_precedes_mutation(gateway):
    from fastapi import HTTPException

    from app.auth.routes import require_csrf

    request, calls, _, state, app = gateway

    def deny():
        raise HTTPException(403)

    app.dependency_overrides[require_csrf] = deny
    assert (
        request("PATCH", ROOT + "/image/connection", json={"expected_revision": 1}).status_code
        == 403
    )
    assert (
        request("POST", ROOT + "/image/resources/services", json={"config": {}}).status_code == 403
    )
    assert not calls and state["commits"] == 0


def test_gateway_connection_projection_and_publish(gateway):
    request, calls, audits, state, _ = gateway
    response = request("GET", ROOT + "/video/connection")
    assert response.status_code == 200
    assert response.json()["has_management_key"] is True
    assert "business-key" not in response.text and "management-key" not in response.text
    response = request("PATCH", ROOT + "/video/connection", json={"expected_revision": 1})
    assert response.status_code == 200
    assert response.json()["revision"] == 2
    assert state["syncs"] == ["video"]
    assert audits[-1].changes["key_changed"] is False
    assert not calls


def test_gateway_profile_write_empty_secret_and_singleton_revision(gateway):
    request, calls, _, state, _ = gateway
    state["body"] = video_profile()
    identity = state["body"]["profile_id"]
    response = request(
        "PATCH",
        ROOT + "/video/resources/model-profiles/" + identity,
        json={"config": {"expected_version": 3, "secrets": {"api_key": ""}}},
    )
    assert response.status_code == 200
    assert calls[-1][3] == {"expected_version": 3, "secrets": {"api_key": ""}}
    state["body"] = {
        "configuration_revision": 8,
        **{
            role: {"adapter": "fake", "profile_id": None}
            for role in ("planner", "video", "voice", "music", "visual")
        },
    }
    response = request(
        "PATCH",
        ROOT + "/video/resources/adapter-bindings",
        json={"config": {"expected_version": 7, "video": {"profile_id": identity}}},
    )
    assert response.status_code == 200, response.text
    assert calls[-1][2] == "/api/v1/admin/adapter-bindings"
    assert calls[-1][3]["expected_version"] == 7


def test_gateway_wrong_upstream_identity_rejected(gateway):
    request, _, audits, state, _ = gateway
    state["body"] = video_profile()
    response = request("GET", ROOT + "/video/resources/model-profiles/" + str(uuid4()))
    assert response.status_code == 503
    assert not audits


def test_two_model_gateway_checks_admin_csrf_and_records_only_revision(gateway, monkeypatch):
    from fastapi import HTTPException

    from app.admin import media_agents
    from app.auth.routes import require_csrf

    request, calls, audits, state, app = gateway
    result = dict(revision=2, versions={}, text_model=None, image_model=None)
    writes = []
    monkeypatch.setattr(media_agents, "save_image_models", lambda *args: (
        writes.append(args[3]) or result
    ))
    body = dict(expected_revision=1, expected_versions={},
                text_model=dict(base_url="https://text.example/v1", model="vision",
                                protocol="chat_completions", api_key="private-key"),
                image_model=dict(base_url="https://image.example/v1", model="image",
                                 protocol="openai_images", api_key="private-key"))
    response = request("PATCH", ROOT + "/image/models", json=body)
    assert response.status_code == 200 and len(writes) == 1
    assert audits[-1].changes == {"kind": "image", "revision": 2}
    assert "private-key" not in str(audits[-1].changes) + response.text
    assert state["commits"] == 1 and state["syncs"] == ["image"]

    def deny(*args):
        raise HTTPException(403)

    app.dependency_overrides[require_csrf] = deny
    assert request("PATCH", ROOT + "/image/models", json=body).status_code == 403
    app.dependency_overrides[require_csrf] = lambda: None
    monkeypatch.setattr(media_agents, "authorize_admin", deny)
    assert request("GET", ROOT + "/image/models").status_code == 403
    assert request("PATCH", ROOT + "/image/models", json=body).status_code == 403
    assert len(writes) == 1 and not calls and state["commits"] == 1


def test_sync_identity_has_no_policy_or_price_side_effects():
    from app.agents.media_runtime import sync_media_agent
    from app.catalog.models import AgentRecord

    added = []
    session = SimpleNamespace(get=lambda *a, **kw: None, add=added.append, flush=lambda: None)
    sync_media_agent(session, SimpleNamespace(mode="mock", test_only=True), "image")
    record = next(row for row in added if isinstance(row, AgentRecord))
    assert record.snapshot["policy_versions"] == {}
    assert record.snapshot["secret_configured"] is True
    assert record.snapshot["protocol_version"] == "image-agent-v1"


def test_video_model_gateway_audits_metadata_and_checks_csrf(gateway, monkeypatch):
    from fastapi import HTTPException
    from app.admin import media_agents
    from app.auth.routes import require_csrf

    request, _, audits, state, app = gateway
    writes = []
    result = dict(revision=1, configuration_revision=9, models={})
    monkeypatch.setattr(media_agents, "save_video_model", lambda *args: writes.append(args[-1]) or result)
    body = dict(expected_revision=1, expected_configuration_revision=8,
                expected_profile_id=None, expected_profile_version=None, adapter="wan",
                base_url="https://wan.example/api/v1", model="wan-model", max_segment_seconds=5,
                api_key="TEST_ONLY_private")
    response = request("PATCH", ROOT + "/video/models/video", json=body)
    assert response.status_code == 200
    assert audits[-1].changes == dict(kind="video", role="video", revision=9)
    assert "TEST_ONLY_private" not in response.text + str(audits[-1].changes)
    assert len(writes) == 1

    def deny():
        raise HTTPException(403)

    app.dependency_overrides[require_csrf] = deny
    assert request("PATCH", ROOT + "/video/models/video", json=body).status_code == 403
    assert len(writes) == 1


@pytest.mark.parametrize("enabled", [True, False])
def test_video_audio_updates_fallbacks_and_versions_connection(gateway, enabled):
    request, calls, audits, state, _ = gateway
    response = request("PATCH", ROOT + "/video/audio", json=dict(
        expected_revision=1, expected_configuration_revision=4, enabled=enabled
    ))
    assert response.status_code == 200, response.text
    assert response.json() == dict(revision=2, enabled=enabled)
    assert calls[-1][3] == dict(expected_version=4, voice={"adapter": "fake"}, music={"adapter": "fake"})
    assert request("GET", ROOT + "/video/audio").json()["enabled"] is enabled
    before = len(calls)
    response = request("PATCH", ROOT + "/video/audio", json=dict(
        expected_revision=1, expected_configuration_revision=4, enabled=False
    ))
    assert response.status_code == 409
    assert len(calls) == before


def test_runtime_save_rejects_replaced_service_connection_before_calling_upstream(gateway):
    request, calls, _, state, _ = gateway
    response = request("PATCH", ROOT + "/video/resources/settings", json=dict(
        expected_connection_revision=0,
        config=dict(expected_version=4, mode="real"),
    ))
    assert response.status_code == 409
    assert not calls and state["commits"] == 0
