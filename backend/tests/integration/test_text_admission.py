"""Real HTTP admission must reject invalid text inputs before committing a freeze."""

from copy import deepcopy
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.admin.models import TextServiceConnection
from app.agents.text import PROTOCOL
from app.agents.text_runtime import DATABASE_PROFILE, managed_agent_id
from app.catalog.schemas import InputSupport, support_ref
from app.policies.schemas import DecisionVersion
from app.policies.service import PolicyService
from app.tasks.models import TaskSnapshot
from tests.integration.test_task_admission import (
    admission,
    catalog,
    counts,
    request_body,
    submit,
)
from tests.integration.test_text_service_connection import text_server

__all__ = ["admission", "catalog", "text_server"]


@pytest.fixture
def text_catalog(admission, text_server):
    c = admission
    c.agent_id = c.spec_id = str(managed_agent_id("mock"))
    c.input_support = dict(c.input_support, max_materials=4)
    c.set_policies()
    settings = c.client.app.state.settings
    settings.text_service_encryption_key = SecretStr(Fernet.generate_key().decode())
    settings.text_agent_profiles = {}
    url, calls, remote = text_server
    c.model_id = remote["id"]
    with Session(c.engine) as session, session.begin():
        policies = PolicyService(session)
        payload = deepcopy(
            policies._read("D-01", settings.generation_policy_versions["D-01"]).payload
        )
        payload["agents"][c.agent_id] = dict(
            next(iter(payload["agents"].values())), protocol_version=PROTOCOL
        )
        for decision, value in {
            "D-01": payload,
            "D-03": {
                "agents": {
                    c.agent_id: dict(
                        protocol_version=PROTOCOL,
                        validation_ref="TEST_ONLY_text_mapping",
                        supported_inputs_ref=support_ref(InputSupport(**c.input_support)),
                    )
                }
            },
        }.items():
            version = "TEST_ONLY_text_" + uuid4().hex
            policies.add_draft(
                DecisionVersion(
                    decision_id=decision,
                    version=version,
                    mode="mock",
                    test_only=True,
                    payload=value,
                )
            )
            c.policies[decision] = version
    settings.generation_policy_versions.update({k: c.policies[k] for k in ("D-01", "D-03")})
    settings.generation_capacity_estimates[c.spec_id] = dict(
        next(iter(settings.generation_capacity_estimates.values()))
    )
    connection = c.client.get("/api/v1/admin/text-service-connection").json()
    response = c.client.patch(
        "/api/v1/admin/text-service-connection",
        json={
            "base_url": url,
            "service_key": "TEST_ONLY_service_key",
            "expected_revision": connection["revision"],
            "reason": "TEST_ONLY text connection",
        },
    )
    assert response.status_code == 200, response.text
    preference = c.client.get("/api/v1/admin/text-default-model").json()
    response = c.client.patch(
        "/api/v1/admin/text-default-model",
        json={
            "model_config_id": c.model_id,
            "expected_revision": preference["revision"],
            "expected_connection_revision": preference["connection_revision"],
            "reason": "TEST_ONLY choose default",
        },
    )
    assert response.status_code == 200, response.text
    agent = next(
        a for a in c.client.get("/api/v1/admin/agents").json() if a["agent_id"] == c.agent_id
    )
    settings.generation_capacity_estimates[c.agent_id]["spec_version"] = agent["version"]
    assert c.price().status_code == 200
    return c


def test_missing_text_credentials_never_freezes(text_catalog):
    c = text_catalog
    body = request_body(c)
    with Session(c.engine) as session, session.begin():
        session.get(TextServiceConnection, "text").key_ciphertext = b"damaged"
    before = counts(c)
    response = submit(c, body)
    assert response.status_code == 503, response.text
    assert counts(c) == before


def test_invalid_upstream_product_field_never_freezes(text_catalog):
    c = text_catalog
    response = c.client.post(
        "/api/v1/products/versions",
        json={
            "product": {"name": "cup", "category": None},
        },
    )
    assert response.status_code == 201, response.text
    c.input["product_version"] = response.json()["version"]
    c.input["product"] = response.json()["product"]
    body = request_body(c)
    # request_body creates a fresh product version, so bind the actual invalid version again.
    body["input"]["product_version"] = response.json()["version"]
    body["input"]["product"] = response.json()["product"]
    quote = c.client.post("/api/v1/quotes", json={"agent_id": c.agent_id, "input": body["input"]})
    assert quote.status_code == 200, quote.text
    body["confirmed_quote"] = quote.json()
    before = counts(c)
    response = submit(c, body)
    assert response.status_code == 422, response.text
    assert counts(c) == before


def test_http_admission_pins_model_configuration(text_catalog):
    c = text_catalog
    body = request_body(c)
    response = submit(c, body)
    assert response.status_code == 201, response.text
    with Session(c.engine) as session:
        snapshot = session.get(TaskSnapshot, response.json()["task"]["task_id"])
        routing = snapshot.routing_snapshot
        assert routing["model_config_id"] == c.model_id
        assert routing["profile"] == DATABASE_PROFILE
        assert not c.client.app.state.settings.text_agent_profiles
        assert "service_key" not in routing


def test_text_only_default_rejects_images_before_any_freeze(text_catalog):
    c = text_catalog
    body = request_body(c)
    body["input"]["material_versions"] = [{"file_id": str(uuid4()), "version": "TEST_ONLY_v1"}]
    quote = c.client.post(
        "/api/v1/quotes",
        json={
            "agent_id": c.agent_id,
            "input": body["input"],
        },
    )
    assert quote.status_code == 200, quote.text
    body["confirmed_quote"] = quote.json()
    before = counts(c)
    response = submit(c, body)
    assert response.status_code == 422
    assert "不支持图片" in response.json()["error"]["message"]
    assert counts(c) == before
