"""Video configuration must follow the upstream model/binding transaction contract."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.admin.media_schemas import VideoModelUpdate
from app.admin.video_model_settings import save_video_model
from app.agents.media_http import MediaServiceError


class Upstream:
    def __init__(self):
        self.revision = 4
        self.bindings = {
            role: dict(adapter="none" if role == "visual" else "fake", profile_id=None)
            for role in ("planner", "video", "visual", "voice", "music")
        }
        self.profiles = {}
        self.writes = []
        self.fail_binding = False

    def json(self, method, path, body=None, **kwargs):
        resource = path.rsplit("/", 1)[-1]
        if method == "GET" and resource == "adapter-bindings":
            return 200, dict(configuration_revision=self.revision, **deepcopy(self.bindings))
        if method == "GET":
            return 200, deepcopy(self.profiles[resource])
        self.writes.append((method, path, deepcopy(body)))
        if resource == "adapter-bindings":
            assert body["expected_version"] == self.revision
            if self.fail_binding:
                raise MediaServiceError(409)
            for role, target in body.items():
                if role == "expected_version":
                    continue
                identity = target.get("profile_id")
                self.bindings[role] = dict(
                    profile_id=identity,
                    adapter=self.profiles[identity]["adapter"] if identity else target["adapter"],
                )
            self.revision += 1
            return 200, dict(configuration_revision=self.revision, **deepcopy(self.bindings))
        if method == "POST":
            identity = "new-profile"
            value = dict(
                profile_id=identity,
                version=1,
                has_api_key=bool(body.get("secrets")),
                secret_presence={"api_key": bool(body.get("secrets"))},
                created_at="now",
                updated_at="now",
                **{key: value for key, value in body.items() if key != "secrets"},
            )
            self.profiles[identity] = value
        else:
            identity = resource
            assert body["expected_version"] == self.profiles[identity]["version"]
            self.profiles[identity].update(
                {key: value for key, value in body.items() if key != "expected_version"}
            )
            self.profiles[identity]["version"] += 1
        self.revision += 1
        return 200, deepcopy(self.profiles[identity])


@pytest.fixture
def context(monkeypatch):
    from app.admin import video_model_settings as service

    monkeypatch.setattr(service, "connection_head", lambda *args, **kw: SimpleNamespace(revision=2))
    monkeypatch.setattr(
        service, "current_connection_view", lambda *args: SimpleNamespace(revision=2)
    )
    return Upstream()


def update(**changes):
    return VideoModelUpdate.model_validate(
        {
            "expected_revision": 2,
            "expected_configuration_revision": 4,
            "expected_profile_id": None,
            "expected_profile_version": None,
            "enabled": True,
            "adapter": "wan",
            "base_url": "https://wan.example/api/v1",
            "model": "wan2.2-i2v-flash",
            "api_key": "private-key",
            "max_segment_seconds": 5,
            **changes,
        }
    )


def test_create_video_model_binds_only_after_profile_is_created(context):
    result = save_video_model(None, None, context, "video", update())
    assert context.bindings["video"] == dict(adapter="wan", profile_id="new-profile")
    assert context.writes[0][2]["parameters"] == {"max_segment_seconds": 5}
    assert context.writes[0][2]["secrets"] == {"api_key": "private-key"}
    assert result["models"]["video"]["has_api_key"] is True
    assert "private-key" not in str(result)
    assert result["configuration_revision"] == 6


def test_failed_binding_keeps_previous_active_configuration(context):
    context.fail_binding = True
    with pytest.raises(MediaServiceError):
        save_video_model(None, None, context, "video", update())
    assert context.bindings["video"]["profile_id"] is None


def test_stale_configuration_is_rejected_before_mutation(context):
    context.revision = 5
    with pytest.raises(MediaServiceError) as error:
        save_video_model(None, None, context, "video", update())
    assert error.value.status_code == 409
    assert context.writes == []


@pytest.mark.parametrize(
    "changes", [dict(api_key=None), dict(max_segment_seconds=None), dict(adapter="openai_chat")]
)
def test_incomplete_or_wrong_role_model_cannot_be_activated(context, changes):
    with pytest.raises(MediaServiceError):
        save_video_model(None, None, context, "video", update(**changes))
    assert not context.writes


def test_blank_key_reuses_bound_secret_and_preserves_parameters(context):
    save_video_model(None, None, context, "video", update())
    context.profiles["new-profile"]["parameters"]["custom"] = "preserved"
    context.writes.clear()
    dto = update(
        api_key=None,
        expected_configuration_revision=6,
        expected_profile_id="new-profile",
        expected_profile_version=1,
        model="wan3.0-video",
        max_segment_seconds=10,
    )
    result = save_video_model(None, None, context, "video", dto)
    assert len(context.writes) == 1
    assert context.writes[0][2] == dict(
        expected_version=1,
        model="wan3.0-video",
        parameters={"max_segment_seconds": 10, "custom": "preserved"},
    )
    assert result["models"]["video"]["model"] == "wan3.0-video"


def test_address_change_requires_new_key(context):
    save_video_model(None, None, context, "video", update())
    context.writes.clear()
    with pytest.raises(MediaServiceError):
        save_video_model(
            None,
            None,
            context,
            "video",
            update(
                api_key=None,
                expected_configuration_revision=6,
                expected_profile_id="new-profile",
                expected_profile_version=1,
                base_url="https://other.example/api/v1",
            ),
        )
    assert not context.writes


def test_concurrent_rebinding_during_profile_update_is_reported_as_conflict(context):
    save_video_model(None, None, context, "video", update())
    original_json = context.json

    def concurrent(method, path, body=None, **kwargs):
        if method == "PATCH" and "model-profiles/" in path:
            context.profiles["replacement"] = {
                **deepcopy(context.profiles["new-profile"]),
                "profile_id": "replacement",
                "model": "another-admins-model",
            }
            context.bindings["video"] = dict(profile_id="replacement", adapter="wan")
            context.revision += 1
        return original_json(method, path, body, **kwargs)

    context.json = concurrent
    with pytest.raises(MediaServiceError) as error:
        save_video_model(
            None,
            None,
            context,
            "video",
            update(
                api_key=None,
                expected_configuration_revision=6,
                expected_profile_id="new-profile",
                expected_profile_version=1,
                model="my-edit",
            ),
        )
    assert error.value.status_code == 409
    assert context.profiles["replacement"]["model"] == "another-admins-model"


def test_visual_can_be_disabled_without_deleting_saved_profile(context):
    dto = update(adapter="openai_vision", max_segment_seconds=None)
    save_video_model(None, None, context, "visual", dto)
    dto = update(
        enabled=False,
        adapter="openai_vision",
        api_key=None,
        expected_configuration_revision=6,
        expected_profile_id="new-profile",
        expected_profile_version=1,
    )
    save_video_model(None, None, context, "visual", dto)
    assert context.bindings["visual"] == dict(adapter="none", profile_id=None)
    assert "new-profile" in context.profiles
