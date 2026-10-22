"""Catalog contracts exercise actual MySQL publication, gates and HTTP authorization."""

import hashlib
import json
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.policies.schemas import DecisionVersion
from app.policies.service import PolicyService


def schema_ref(value):
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
    )


@pytest.fixture
def catalog(auth_client, mysql_engine):
    account = "cat_" + uuid4().hex
    response = auth_client.post(
        "/api/v1/auth/register",
        json={
            "account": account,
            "password": "TEST_ONLY_password",
            "request_key": uuid4().hex,
        },
    )
    assert response.status_code == 201
    auth_client.headers["X-CSRF-Token"] = auth_client.cookies["csrf_token"]
    user = response.json()["profile"]["user_id"]
    with mysql_engine.begin() as connection:
        connection.execute(text("UPDATE users SET role='admin' WHERE id=:id"), {"id": user})
    return CatalogFixture(auth_client, mysql_engine, user)


class CatalogFixture:
    def __init__(self, client, engine, user):
        self.client, self.engine, self.user = client, engine, user
        self.agent_id = str(uuid4())
        self.spec_id = self.agent_id  # Internal single-result envelope, never a published spec.
        self.input_support = {
            "product_required_fields": ["name"],
            "instruction_required": False,
            "min_materials": 0,
            "max_materials": 0,
        }
        self.parameter_schema = {"fields": {}, "combinations": []}
        self.input = {
            "product_version": "TEST_ONLY_product_v1",
            "product": {"name": "cup"},
            "instruction": "",
            "material_versions": [],
            "parameters": {},
        }
        self.policies = {}
        self.set_policies()

    def set_policies(self, credits=7, delivery="single", d04=False):
        payloads = {
            "D-03": {
                "agents": {
                    self.agent_id: {
                        "protocol_version": "TEST_ONLY_protocol_v1",
                        "validation_ref": "TEST_ONLY_validation",
                        "supported_inputs_ref": schema_ref(self.input_support),
                    }
                }
            },
            "D-02": {
                "specs": {
                    self.spec_id: {
                        "agent_id": self.agent_id,
                        "agent_version": "TEST_ONLY_v1",
                        "parameter_schema_ref": schema_ref(self.parameter_schema),
                        "validation_evidence_ref": "TEST_ONLY_evidence",
                        "delivery_kind": delivery,
                    }
                }
            },
            "D-05": {"prices": {self.spec_id: {"credits": credits}}},
        }
        if d04:
            payloads["D-04"] = {
                "specs": {
                    self.spec_id: {
                        key: "TEST_ONLY_" + key
                        for key in (
                            "delivery_ref",
                            "partial_failure_ref",
                            "billing_ref",
                            "missing_results_evidence_ref",
                        )
                    }
                }
            }
        with Session(self.engine) as session, session.begin():
            for decision, payload in payloads.items():
                version = "TEST_ONLY_" + uuid4().hex
                PolicyService(session).add_draft(
                    DecisionVersion(
                        decision_id=decision,
                        version=version,
                        mode="mock",
                        test_only=True,
                        payload=payload,
                    )
                )
                self.policies[decision] = version

    def agent(self, enabled=True, version="TEST_ONLY_v1", expected=None):
        return self.client.post(
            "/api/v1/admin/agents",
            json={
                "agent_id": self.agent_id,
                "version": version,
                "expected_version": expected,
                "mode": "mock",
                "test_only": True,
                "kind": "copy",
                "name": "TEST_ONLY Copy",
                "protocol_version": "TEST_ONLY_protocol_v1",
                "input_support": self.input_support,
                "endpoint": "https://secret-endpoint.invalid/private",
                "secret_ref": "TEST_ONLY_SECRET_REF",
                "enabled": enabled,
                "policy_versions": {"D-03": self.policies["D-03"]},
                "reason": "TEST_ONLY agent publication",
            },
        )

    def price(self, credits=7, version=None, expected=None):
        current = self.client.get("/api/v1/admin/parameter-config").json()
        return self.client.patch(
            "/api/v1/admin/parameter-config",
            json={
                "expected_version": current["version"],
                "text_price": credits,
                "image_price": current["image_price"],
                "video_price": current["video_price"],
            },
        )

    def publish(self):
        response = self.agent()
        assert response.status_code == 201, response.text
        response = self.price()
        assert response.status_code == 200, response.text

    def quote(self):
        return self.client.post(
            "/api/v1/quotes", json={"agent_id": self.agent_id, "input": self.input}
        )

    def validate(self, quote):
        from app.catalog.service import CatalogService
        from app.common.types import InputSnapshot, Quote

        with Session(self.engine) as session, session.begin():
            return CatalogService(session, mode="mock").validate_confirmed_quote(
                Quote.model_validate(quote), InputSnapshot.model_validate(self.input)
            )


def test_agent_listing_uses_bounded_queries_without_losing_visibility_or_transaction(catalog):
    from sqlalchemy import event

    from app.catalog.service import CatalogService

    assert catalog.agent().status_code == 201
    disabled = CatalogFixture(catalog.client, catalog.engine, catalog.user)
    assert disabled.agent(enabled=False).status_code == 201
    another = CatalogFixture(catalog.client, catalog.engine, catalog.user)
    assert another.agent().status_code == 201
    statements = []

    def count(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    with Session(catalog.engine) as session:
        session.execute(text("SELECT 1"))
        transaction = session.get_transaction()
        event.listen(catalog.engine, "before_cursor_execute", count)
        try:
            visible = CatalogService(session, mode="mock").list_agents()
        finally:
            event.remove(catalog.engine, "before_cursor_execute", count)
        ids = {str(agent.agent_id) for agent in visible}
        assert {catalog.agent_id, another.agent_id} <= ids
        assert disabled.agent_id not in ids
        assert all(agent.mode == "mock" and agent.enabled for agent in visible)
        assert session.get_transaction() is transaction
        assert len(statements) <= 3, f"Catalog list used {len(statements)} SELECTs"
        statements.clear()
        event.listen(catalog.engine, "before_cursor_execute", count)
        try:
            administrative = CatalogService(session, mode="mock").list_agents(admin=True)
        finally:
            event.remove(catalog.engine, "before_cursor_execute", count)
        assert disabled.agent_id in {str(agent.agent_id) for agent in administrative}
        assert len(statements) <= 2
        assert session.get_transaction() is transaction


def test_quote_stale_after_reprice_delist(catalog):
    catalog.publish()
    quote = catalog.quote().json()
    assert quote["credits"] == 7
    catalog.set_policies(credits=11)
    assert catalog.price(11).status_code == 200
    from app.catalog.service import CatalogError

    with pytest.raises(CatalogError) as error:
        catalog.validate(quote)
    assert error.value.status_code == 409 and error.value.code == "QUOTE_STALE"
    assert error.value.current_quotes[0].credits == 11
    assert catalog.agent(False, "TEST_ONLY_v2", "TEST_ONLY_v1").status_code == 201
    with pytest.raises(CatalogError) as error:
        catalog.validate(quote)
    assert error.value.code == "QUOTE_STALE" and error.value.current_quotes == []
    assert error.value.current_specs == []
    response = catalog.quote()
    assert response.status_code == 422 and response.json()["error"]["code"] == "SPEC_DISABLED"


def test_secret_redacted(catalog):
    response = catalog.agent()
    assert response.status_code == 201, response.text
    assert response.json()["secret_configured"] is True
    for response in (
        response,
        catalog.client.get("/api/v1/agents"),
        catalog.client.get("/api/v1/admin/agents"),
    ):
        assert "TEST_ONLY_SECRET_REF" not in response.text
        assert "secret-endpoint" not in response.text
    with catalog.engine.connect() as connection:
        changes = (
            connection.execute(
                text("SELECT changes FROM audit_events WHERE object_id=:id"),
                {"id": catalog.agent_id},
            )
            .scalars()
            .all()
        )
    assert changes and "TEST_ONLY_SECRET_REF" not in str(changes)
    assert "secret-endpoint" not in str(changes)


@pytest.mark.parametrize("change", ["credits", "digest", "policy", "input"])
def test_confirmation_never_trusts_client_amount_or_snapshot(catalog, change):
    catalog.publish()
    quote = catalog.quote().json()
    if change == "credits":
        quote["credits"] = 0
    elif change == "digest":
        quote["input_digest"] = "forged"
    elif change == "policy":
        quote["policy_versions"]["D-05"] = "unknown-version"
    else:
        catalog.input["product"]["name"] = "changed"
    from app.catalog.service import CatalogError

    with pytest.raises(CatalogError) as error:
        catalog.validate(quote)
    assert error.value.code == "QUOTE_STALE" and error.value.status_code == 409
    assert error.value.current_quotes[0].credits == 7


def test_permission_is_database_authoritative(catalog):
    from fastapi import HTTPException
    from sqlalchemy import select

    from app.auth.models import AuthSession
    from app.catalog.schemas import AgentDraft
    from app.catalog.service import CatalogService
    from app.common.types import Principal

    with catalog.engine.begin() as connection:
        connection.execute(text("UPDATE users SET role='user' WHERE id=:id"), {"id": catalog.user})
    response = catalog.agent()
    assert response.status_code == 403
    with Session(catalog.engine) as session:
        credential = session.scalar(select(AuthSession).where(AuthSession.user_id == catalog.user))
        actor = Principal(
            user_id=catalog.user, role="admin", session_id=credential.id, auth_version=0
        )
        dto = AgentDraft.model_validate(json.loads(response.request.content))
        with pytest.raises(HTTPException) as error:
            CatalogService(session, mode="mock").publish_agent_version(actor, dto)
        assert error.value.status_code == 403
    with catalog.engine.begin() as connection:
        connection.execute(
            text("UPDATE users SET role='admin',auth_version=1 WHERE id=:id"), {"id": catalog.user}
        )
    assert catalog.agent().status_code == 401
    with Session(catalog.engine) as session:
        with pytest.raises(HTTPException) as error:
            CatalogService(session, mode="mock").publish_agent_version(actor, dto)
        assert error.value.status_code == 401


def test_auth_headers_contract_and_runtime(catalog):
    schema = catalog.client.get("/openapi.json").json()
    for path in (
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/me",
        "/api/v1/auth/logout",
        "/api/v1/admin/agents",
        "/api/v1/quotes",
    ):
        method = "patch" if path.endswith("/me") else "post"
        params = {
            (p["in"], p["name"].lower()): p for p in schema["paths"][path][method]["parameters"]
        }
        for header in ("origin", "x-requested-with"):
            assert params[("header", header)]["required"]
        if "/auth/login" not in path and "/auth/register" not in path:
            for location, name in (
                ("header", "x-csrf-token"),
                ("cookie", "session"),
                ("cookie", "csrf_token"),
            ):
                assert params[(location, name)]["required"]
    for header in ("Origin", "X-Requested-With", "X-CSRF-Token"):
        saved = catalog.client.headers.pop(header)
        assert catalog.agent().status_code == 403
        catalog.client.headers[header] = saved
    catalog.client.cookies.delete("csrf_token")
    assert catalog.agent().status_code == 403


def test_unconfirmed_production_agent_cannot_publish(catalog):
    from app.auth.service import AuthService
    from app.catalog.schemas import AgentDraft
    from app.catalog.service import CatalogService
    from app.policies.service import PolicyGateError

    response = catalog.agent()
    dto = json.loads(response.request.content)
    dto.update(mode="production", test_only=False, agent_id=str(uuid4()))
    # The production policy exists but is still draft; no admin can self-confirm it.
    version = "production_draft_" + uuid4().hex
    with Session(catalog.engine) as session, session.begin():
        PolicyService(session).add_draft(
            DecisionVersion(
                decision_id="D-03",
                version=version,
                mode="production",
                test_only=False,
                payload={
                    "agents": {
                        dto["agent_id"]: {
                            "protocol_version": dto["protocol_version"],
                            "validation_ref": "pending",
                            "supported_inputs_ref": schema_ref(catalog.input_support),
                        }
                    }
                },
            )
        )
        actor = AuthService(session).require_active_principal(catalog.client.cookies["session"])
        dto["policy_versions"] = {"D-03": version}
        with pytest.raises(PolicyGateError):
            CatalogService(session, mode="production").publish_agent_version(
                actor, AgentDraft.model_validate(dto)
            )


@pytest.mark.parametrize(
    "kind,field,credits",
    [("copy", "text_price", 0), ("image", "image_price", 13), ("video", "video_price", 29)],
)
def test_kind_prices_need_no_published_generation_spec(catalog, monkeypatch, kind, field, credits):
    original = catalog.client.post

    def publish_kind(url, **kwargs):
        if url == "/api/v1/admin/agents":
            kwargs["json"]["kind"] = kind
        return original(url, **kwargs)

    monkeypatch.setattr(catalog.client, "post", publish_kind)
    assert catalog.agent().status_code == 201
    current = catalog.client.get("/api/v1/admin/parameter-config").json()
    body = dict(
        expected_version=current["version"], text_price=None, image_price=None, video_price=None
    )
    body[field] = credits
    response = catalog.client.patch("/api/v1/admin/parameter-config", json=body)
    assert response.status_code == 200
    quote = catalog.quote()
    assert quote.status_code == 200, quote.text
    assert quote.json()["credits"] == credits
    assert quote.json()["price_version"] == response.json()["version"]
    with catalog.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM generation_specs WHERE agent_id=:id"),
                {"id": catalog.agent_id},
            ).scalar_one()
            == 0
        )


def test_null_price_prevents_quotation_without_creating_any_task(catalog):
    assert catalog.agent().status_code == 201
    current = catalog.client.get("/api/v1/admin/parameter-config").json()
    assert (
        catalog.client.patch(
            "/api/v1/admin/parameter-config",
            json=dict(
                expected_version=current["version"],
                text_price=None,
                image_price=None,
                video_price=None,
            ),
        ).status_code
        == 200
    )
    response = catalog.quote()
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FEATURE_NOT_ENABLED"


@pytest.mark.parametrize("amount", [True, 1.5, "7", -1, 2**53])
def test_parameter_price_rejects_unsafe_amounts(catalog, amount):
    catalog.publish()
    current = catalog.client.get("/api/v1/admin/parameter-config").json()
    response = catalog.client.patch(
        "/api/v1/admin/parameter-config",
        json=dict(
            expected_version=current["version"],
            text_price=amount,
            image_price=None,
            video_price=None,
        ),
    )
    assert response.status_code == 422
    assert catalog.quote().json()["credits"] == 7


def test_legacy_parameters_and_spec_quote_requests_are_rejected(catalog):
    catalog.publish()
    catalog.input["parameters"] = {"tone": "plain"}
    assert catalog.quote().status_code == 422
    catalog.input["parameters"] = {}
    assert (
        catalog.client.post(
            "/api/v1/quotes", json={"spec_id": catalog.spec_id, "input": catalog.input}
        ).status_code
        == 422
    )
    for path in (
        "/api/v1/admin/specs",
        "/api/v1/admin/prices",
        f"/api/v1/agents/{catalog.agent_id}/specs",
    ):
        assert catalog.client.get(path).status_code == 404


def test_current_price_read_ignores_repeatable_read_snapshot(catalog):
    from app.auth.service import AuthService
    from app.catalog.service import CatalogService
    from app.common.types import InputSnapshot

    catalog.publish()
    with Session(catalog.engine) as session:
        before = session.execute(
            text("SELECT COUNT(*) FROM generation_parameter_configs")
        ).scalar_one()
        assert catalog.price(11).status_code == 200
        actor = AuthService(session).require_active_principal(catalog.client.cookies["session"])
        quote = CatalogService(session, mode="mock").quote_agent(
            actor, InputSnapshot.model_validate(catalog.input), catalog.agent_id
        )
        assert quote.credits == 11
        assert (
            session.execute(text("SELECT COUNT(*) FROM generation_parameter_configs")).scalar_one()
            == before
        )


def test_validation_locks_parameter_head_until_caller_ends_transaction(catalog):
    from sqlalchemy.exc import OperationalError

    from app.catalog.service import CatalogService
    from app.common.types import InputSnapshot, Quote

    catalog.publish()
    quote = Quote.model_validate(catalog.quote().json())
    with Session(catalog.engine) as session:
        assert (
            CatalogService(session, mode="mock")
            .validate_confirmed_quote(quote, InputSnapshot.model_validate(catalog.input))
            .quote.credits
            == 7
        )
        with catalog.engine.connect() as connection, connection.begin():
            connection.execute(text("SET SESSION innodb_lock_wait_timeout=1"))
            with pytest.raises(OperationalError) as error:
                connection.execute(
                    text("UPDATE generation_parameter_heads SET version=version WHERE mode='mock'")
                )
            assert error.value.orig.args[0] == 1205
        session.rollback()
    assert catalog.price(9).status_code == 200


def test_price_versions_are_append_only_and_stale_admin_cannot_overwrite(catalog):
    from sqlalchemy.exc import DBAPIError

    catalog.publish()
    previous = catalog.client.get("/api/v1/admin/parameter-config").json()
    assert catalog.price(11).status_code == 200
    response = catalog.client.patch(
        "/api/v1/admin/parameter-config",
        json=dict(
            expected_version=previous["version"], text_price=1, image_price=None, video_price=None
        ),
    )
    assert response.status_code == 409
    assert catalog.quote().json()["credits"] == 11
    for action in (
        "UPDATE generation_parameter_configs SET text_price=1",
        "DELETE FROM generation_parameter_configs",
    ):
        with catalog.engine.connect() as connection, connection.begin():
            with pytest.raises(DBAPIError):
                connection.execute(
                    text(action + " WHERE version=:version"), {"version": previous["version"]}
                )
