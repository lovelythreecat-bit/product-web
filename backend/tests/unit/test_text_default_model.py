from uuid import uuid4

import pytest

from app.auth.routes import require_csrf
from tests.unit.test_text_model_configs import gateway, model_view

__all__ = ["gateway"]
ROOT = "/api/v1/admin/text-default-model"


@pytest.fixture
def defaults(gateway, monkeypatch):
    client, calls, audits, result, app = gateway
    from app.admin import text_models
    from app.auth.routes import get_session
    session = app.dependency_overrides[get_session]()
    row = session.get(None)
    row.revision = 2
    row.default_model_id = None
    row.default_revision = 0
    monkeypatch.setattr(text_models, "sync_text_agent", lambda *a: None, raising=False)
    return client, calls, audits, result, app, row


def test_default_is_explicit_persistent_and_contains_no_model_secrets(defaults):
    client, calls, audits, result, _, row = defaults
    assert client.get(ROOT).json() == {
        "model_config_id": None, "revision": 0, "connection_revision": 2,
        "generation_policy_configured": False,
    }
    result["body"] = model_view()
    chosen = result["body"]["id"]
    response = client.patch(ROOT, json={"model_config_id": chosen, "expected_revision": 0,
        "expected_connection_revision": 2})
    assert response.status_code == 200, response.text
    assert row.default_model_id == chosen
    assert client.get(ROOT).json()["model_config_id"] == chosen
    assert calls[0].full_url.endswith("/v1/model-configs/" + chosen)
    assert audits[-1].action == "text_default_model"
    assert "api_key" not in response.text


@pytest.mark.parametrize("changes", [{"enabled": False}, {"has_api_key": False},
                                     {"id": str(uuid4())}])
def test_unusable_or_mismatched_model_is_never_selected(defaults, changes):
    client, _, audits, result, _, row = defaults
    result["body"] = model_view()
    chosen = result["body"]["id"]
    result["body"].update(changes)
    response = client.patch(ROOT, json={"model_config_id": chosen, "expected_revision": 0,
        "expected_connection_revision": 2, "reason": "选择"})
    assert response.status_code in (422, 503)
    assert row.default_model_id is None
    assert not audits


@pytest.mark.parametrize("versions", [(1, 2), (0, 1)])
def test_stale_selection_or_connection_never_overwrites(defaults, versions):
    client, calls, _, _, _, row = defaults
    response = client.patch(ROOT, json={"model_config_id": str(uuid4()),
        "expected_revision": versions[0], "expected_connection_revision": versions[1],
        "reason": "选择"})
    assert response.status_code == 409
    assert not calls
    assert row.default_model_id is None


def test_csrf_failure_does_not_contact_upstream(defaults):
    from fastapi import HTTPException

    client, calls, _, _, app, _ = defaults
    def deny():
        raise HTTPException(403)
    app.dependency_overrides[require_csrf] = deny
    assert client.patch(ROOT, json={}).status_code == 403
    assert not calls


def test_new_binding_uses_database_and_old_task_ignores_changed_default(defaults):
    from types import SimpleNamespace

    from app.agents.registry import AgentRegistry
    from app.agents.text import TextAgentRouting
    from app.agents.text_runtime import DATABASE_PROFILE
    from app.auth.routes import get_session
    from tests.unit.test_text_agent import agent_record

    _, calls, _, result, app, row = defaults
    result["body"] = model_view()
    row.default_model_id = result["body"]["id"]
    session = app.dependency_overrides[get_session]()
    registry = AgentRegistry.from_settings(app.state.settings)
    # No APP_TEXT_AGENT_PROFILES is configured; the DB key must be used.
    from app.agents.text_runtime import resolve_text_profile
    profile = resolve_text_profile(session, app.state.settings)
    record = agent_record(profile)
    record.snapshot["input_support"]["max_materials"] = 4
    binding = registry.bind_version(record, session=session)
    assert binding.adapter.profile.model_config_id == profile.model_config_id
    assert calls[-1].get_header("Authorization") == "Bearer private-service-key"
    fixed = TextAgentRouting(profile=DATABASE_PROFILE, base_url=profile.base_url,
        model_config_id=profile.model_config_id, supports_images=False).model_dump(mode="json")
    row.default_model_id = str(uuid4())
    result["body"]["id"] = row.default_model_id
    earlier_calls = len(calls)
    old = registry.bind_version(record, session=session,
        task=SimpleNamespace(external_submission_id=str(uuid4())), routing=fixed)
    assert old.adapter.profile.model_config_id == profile.model_config_id
    assert old.endpoint_digest == binding.endpoint_digest
    assert len(calls) == earlier_calls  # Worker never resolves a different default remotely.
    new = registry.bind_version(record, session=session)
    assert str(new.adapter.profile.model_config_id) == row.default_model_id


def test_old_routing_never_sends_credentials_to_a_changed_origin(defaults):
    from app.agents.text import TextAgentRouting
    from app.agents.text_runtime import DATABASE_PROFILE, resolve_text_profile
    from app.auth.routes import get_session

    _, calls, _, _, app, _ = defaults
    session = app.dependency_overrides[get_session]()
    fixed = TextAgentRouting(profile=DATABASE_PROFILE, base_url="https://another.example",
        model_config_id=uuid4(), supports_images=False).model_dump(mode="json")
    with pytest.raises(LookupError):
        resolve_text_profile(session, app.state.settings, routing=fixed)
    assert not calls


def test_administrator_is_required_before_model_lookup(defaults, monkeypatch):
    from fastapi import HTTPException

    from app.admin import text_models

    client, calls, _, _, _, _ = defaults
    def deny(*args):
        raise HTTPException(403)
    monkeypatch.setattr(text_models, "authorize_admin", deny)
    assert client.get(ROOT).status_code == 403
    assert client.patch(ROOT, json={"model_config_id": str(uuid4()), "expected_revision": 0,
        "expected_connection_revision": 2, "reason": "选择"}).status_code == 403
    assert not calls


def test_managed_text_contract_needs_no_second_manual_input_policy():
    from types import SimpleNamespace

    from app.agents.text import PROTOCOL
    from app.agents.text_runtime import managed_agent_id
    from app.catalog.schemas import AgentVersion
    from app.catalog.service import CatalogService

    value = AgentVersion(agent_id=managed_agent_id("mock"), version="text-agent-v1",
        kind="copy", name="文本创作", mode="mock", test_only=True, enabled=True,
        secret_configured=True, protocol_version=PROTOCOL, policy_versions={},
        input_support=dict(product_required_fields=["name"],instruction_required=False,
                           min_materials=0,max_materials=4))
    # Known server-managed protocol/input contract needs no manual per-agent policy setup.
    CatalogService(SimpleNamespace(), mode="mock")._agent_gate(value)
