"""Two-model settings must publish a complete graph without editing historical resources."""

from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr, ValidationError

from app.admin.image_model_settings import read_image_models, save_image_models
from app.admin.media_schemas import ImageModelsUpdate, MediaConnectionUpdate
from app.agents.media_connection import (
    MediaConnectionHead,
    read_media_connection,
    update_media_connection,
)
from app.agents.media_http import MediaServiceError


class Session:
    def __init__(self):
        self.rows = {}
        self.add(MediaConnectionHead(kind="image", revision=0))

    def get(self, model, key, **kwargs):
        return self.rows.get((model, key))

    def add(self, row):
        self.rows[type(row), getattr(row, "id", None) or row.kind] = row

    def flush(self):
        pass


class Upstream:
    def __init__(self):
        self.rows, self.writes = {}, []
        self.fail_resource = None

    def json(self, method, path, body=None):
        resource = path.split("/")[3]
        if method == "GET":
            return 200, deepcopy(self.rows[path])
        assert method == "POST", "Settings must never mutate old resources"
        if resource == self.fail_resource:
            raise MediaServiceError()
        self.writes.append((resource, deepcopy(body)))
        value = dict(
            id=str(uuid4()),
            version=1,
            enabled=True,
            created_at="2026-10-16T00:00:00Z",
            updated_at="2026-10-16T00:00:00Z",
        )
        value.update(body)
        if resource == "services":
            value.update(
                has_api_key=True,
                generation_path=body.get("generation_path"),
                edit_path=body.get("edit_path"),
                chat_path=body.get("chat_path", "/chat/completions"),
            )
            value.pop("api_key", None)
        if resource == "model-configs":
            value.setdefault("description", None)
        self.rows[path + "/" + value["id"]] = deepcopy(value)
        return 201, value


@pytest.fixture
def setup():
    session, upstream = Session(), Upstream()
    settings = SimpleNamespace(
        text_service_encryption_key=SecretStr(Fernet.generate_key().decode())
    )
    actor = uuid4()
    update_media_connection(
        session,
        settings,
        "image",
        MediaConnectionUpdate(
            expected_revision=0, base_url="https://agent.example", service_key="agent-private"
        ),
        actor,
    )
    return session, settings, upstream, actor


def draft(view, **changes):
    body = dict(
        expected_revision=view["revision"],
        expected_versions=view["versions"],
        text_model=dict(
            base_url="https://text.example/v1",
            model="vision-model",
            protocol="chat_completions",
            api_key="text-private",
        ),
        image_model=dict(
            base_url="https://image.example/v1",
            model="image-model",
            protocol="openai_images",
            api_key="image-private",
        ),
    )
    body.update(changes)
    return ImageModelsUpdate.model_validate(body)


def test_saves_only_two_models_and_automatically_binds_them(setup):
    session, settings, upstream, actor = setup
    initial = read_image_models(session, settings, upstream)
    assert initial["text_model"] is None and initial["image_model"] is None
    result = save_image_models(session, settings, upstream, draft(initial), actor)
    assert result["revision"] == 2
    assert result["text_model"]["model"] == "vision-model"
    assert result["image_model"]["model"] == "image-model"
    scheme = upstream.writes[-1][1]
    assert set(scheme["stages"]) == {"vision"}
    assert set(scheme["image_models"]) == {"fast"}
    assert scheme["stages"]["vision"] != scheme["image_models"]["fast"]
    assert "private" not in str(result)


def configured(setup):
    session, settings, upstream, actor = setup
    initial = read_image_models(session, settings, upstream)
    return save_image_models(session, settings, upstream, draft(initial), actor)


def test_blank_keys_reuse_services_preserve_paths_parameters_and_historical_graph(setup):
    session, settings, upstream, actor = setup
    view = configured(setup)
    old = read_media_connection(session, settings, "image")
    scheme = upstream.rows["/api/v1/agent-configs/" + str(old.default_config_id)]
    scheme["parameters"]["request_timeout_seconds"] = 360
    for path, row in upstream.rows.items():
        if path.startswith("/api/v1/services/"):
            row["chat_path"] = "/custom/chat"
    view = read_image_models(session, settings, upstream)
    before = deepcopy(upstream.rows)
    text, image = dict(view["text_model"]), dict(view["image_model"])
    for row in (text, image):
        row.pop("has_api_key")
        row.pop("enabled")
    text["model"] = "new-vision"
    upstream.writes.clear()
    saved = save_image_models(
        session, settings, upstream, draft(view, text_model=text, image_model=image), actor
    )
    assert [kind for kind, _ in upstream.writes] == ["model-configs", "agent-configs"]
    assert all(upstream.rows[key] == value for key, value in before.items())
    assert upstream.writes[-1][1]["parameters"]["request_timeout_seconds"] == 360
    assert saved["text_model"]["model"] == "new-vision"
    assert read_media_connection(session, settings, "image", old.id) == old


@pytest.mark.parametrize("failure", ["services", "model-configs", "agent-configs"])
def test_partial_failure_never_publishes_a_new_default(setup, failure):
    session, settings, upstream, actor = setup
    view = configured(setup)
    before = read_media_connection(session, settings, "image")
    upstream.fail_resource = failure
    with pytest.raises(MediaServiceError):
        save_image_models(session, settings, upstream, draft(view), actor)
    assert read_media_connection(session, settings, "image") == before


def test_origin_change_without_key_and_stale_resource_rejected_before_writes(setup):
    session, settings, upstream, actor = setup
    view = configured(setup)
    upstream.writes.clear()
    bad = dict(base_url="https://other.example", model="model", protocol="chat_completions")
    with pytest.raises(MediaServiceError) as error:
        save_image_models(session, settings, upstream, draft(view, text_model=bad), actor)
    assert error.value.status_code == 422 and upstream.writes == []
    upstream.rows[next(iter(upstream.rows))]["version"] += 1
    with pytest.raises(MediaServiceError) as error:
        save_image_models(session, settings, upstream, draft(view), actor)
    assert error.value.status_code == 409 and upstream.writes == []


def test_stale_connection_and_wrong_identity_rejected(setup):
    session, settings, upstream, actor = setup
    view = configured(setup)
    update_media_connection(
        session,
        settings,
        "image",
        MediaConnectionUpdate(expected_revision=2, service_key="rotated"),
        actor,
    )
    upstream.writes.clear()
    with pytest.raises(MediaServiceError) as error:
        save_image_models(session, settings, upstream, draft(view), actor)
    assert error.value.status_code == 409 and upstream.writes == []
    upstream.rows[next(iter(upstream.rows))]["id"] = str(uuid4())
    with pytest.raises(MediaServiceError):
        read_image_models(session, settings, upstream)


def test_roles_enforce_protocol_and_nonblank_model_and_key(setup):
    session, settings, upstream, _ = setup
    view = read_image_models(session, settings, upstream)
    for change in ({"protocol": "openai_images"}, {"model": " "}, {"api_key": " "}):
        text = dict(base_url="https://text.example", model="vision", protocol="chat_completions")
        text.update(change)
        with pytest.raises(ValidationError):
            draft(view, text_model=text)
