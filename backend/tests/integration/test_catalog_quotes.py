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
        self.agent_id, self.spec_id = str(uuid4()), str(uuid4())
        self.input_support = {
            "product_required_fields": ["name"],
            "instruction_required": False,
            "min_materials": 0,
            "max_materials": 0,
        }
        self.parameter_schema = {
            "fields": {"tone": {"kind": "string", "required": True, "choices": ["plain", "warm"]}},
            "combinations": [],
        }
        self.input = {
            "product_version": "TEST_ONLY_product_v1",
            "product": {"name": "cup"},
            "instruction": "",
            "material_versions": [],
            "parameters": {"tone": "plain"},
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

    def spec(self, delivery="single", version="TEST_ONLY_v1", expected=None, enabled=True):
        return self.client.post(
            "/api/v1/admin/specs",
            json={
                "spec_id": self.spec_id,
                "version": version,
                "expected_version": expected,
                "agent_id": self.agent_id,
                "agent_version": "TEST_ONLY_v1",
                "name": "TEST_ONLY spec",
                "parameter_schema": self.parameter_schema,
                "delivery_kind": delivery,
                "enabled": enabled,
                "policy_versions": self.policies,
                "reason": "TEST_ONLY spec publication",
            },
        )

    def price(self, credits=7, version="TEST_ONLY_v1", expected=None):
        return self.client.post(
            "/api/v1/admin/prices",
            json={
                "spec_id": self.spec_id,
                "version": version,
                "expected_version": expected,
                "credits": credits,
                "policy_version": self.policies["D-05"],
                "enabled": True,
                "reason": "TEST_ONLY price publication",
            },
        )

    def publish(self):
        for response in (self.agent(), self.spec(), self.price()):
            assert response.status_code == 201, response.text

    def quote(self):
        return self.client.post(
            "/api/v1/quotes", json={"spec_id": self.spec_id, "input": self.input}
        )

    def validate(self, quote):
        from app.catalog.service import CatalogService
        from app.common.types import InputSnapshot, Quote

        with Session(self.engine) as session, session.begin():
            return CatalogService(session, mode="mock").validate_confirmed_quote(
                Quote.model_validate(quote), InputSnapshot.model_validate(self.input)
            )


def test_quote_stale_after_reprice_delist(catalog):
    catalog.publish()
    quote = catalog.quote().json()
    assert quote["credits"] == 7
    catalog.set_policies(credits=11)
    assert catalog.price(11, "TEST_ONLY_v2", "TEST_ONLY_v1").status_code == 201
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


def test_multi_result_requires_d04(catalog):
    assert catalog.agent().status_code == 201
    catalog.set_policies(delivery="multiple")
    response = catalog.spec("multiple")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "FEATURE_NOT_ENABLED"
    catalog.set_policies(delivery="multiple", d04=True)
    assert catalog.spec("multiple").status_code == 201


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


def test_unknown_parameters_material_support_and_new_spec(catalog):
    catalog.publish()
    catalog.input["parameters"]["unsupported"] = "anything"
    assert catalog.quote().status_code == 422
    del catalog.input["parameters"]["unsupported"]
    catalog.input["parameters"]["tone"] = "invalid"
    assert catalog.quote().status_code == 422
    catalog.input["parameters"]["tone"] = "plain"
    catalog.input["material_versions"] = [{"file_id": str(uuid4()), "version": "v1"}]
    assert catalog.quote().status_code == 422
    catalog.input["material_versions"] = []
    quote = catalog.quote().json()
    catalog.parameter_schema["fields"]["tone"]["choices"] = ["new"]
    catalog.set_policies()
    assert catalog.spec(version="TEST_ONLY_v2", expected="TEST_ONLY_v1").status_code == 201
    from app.catalog.service import CatalogError

    with pytest.raises(CatalogError) as error:
        catalog.validate(quote)
    assert error.value.code == "QUOTE_STALE"
    assert error.value.current_quotes == []
    assert error.value.current_specs[0].version == "TEST_ONLY_v2"


def test_d05_amount_and_exact_version_gate(catalog):
    assert catalog.agent().status_code == 201
    assert catalog.spec().status_code == 201
    assert catalog.price(credits=99).status_code == 403
    catalog.policies["D-05"] = "nonexistent-version"
    assert catalog.price().status_code == 403
    catalog.policies["D-03"] = "nonexistent-version"
    assert catalog.agent(version="TEST_ONLY_v2", expected="TEST_ONLY_v1").status_code == 403


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


def test_history_immutable_cas_and_rollback(catalog):
    from sqlalchemy.exc import DBAPIError

    catalog.publish()
    assert catalog.agent(version="TEST_ONLY_v2", expected="wrong").status_code == 409
    assert catalog.agent(version="TEST_ONLY_v1", expected="TEST_ONLY_v1").status_code == 409
    for table, key in (
        ("agent_versions", "agent_id"),
        ("generation_specs", "spec_id"),
        ("price_versions", "spec_id"),
    ):
        for action in (f"UPDATE {table} SET version='overwritten'", f"DELETE FROM {table}"):
            with catalog.engine.connect() as connection, connection.begin():
                with pytest.raises(DBAPIError):
                    connection.execute(
                        text(action + f" WHERE {key}=:id"),
                        {"id": catalog.agent_id if key == "agent_id" else catalog.spec_id},
                    )
    from app.auth.service import AuthService
    from app.catalog.schemas import PriceDraft
    from app.catalog.service import CatalogService

    with Session(catalog.engine) as session:
        actor = AuthService(session).require_active_principal(catalog.client.cookies["session"])
        CatalogService(session, mode="mock").set_price_version(
            actor,
            PriceDraft(
                spec_id=catalog.spec_id,
                version="TEST_ONLY_rollback",
                expected_version="TEST_ONLY_v1",
                credits=7,
                policy_version=catalog.policies["D-05"],
                enabled=True,
                reason="TEST_ONLY rollback",
            ),
        )
        session.rollback()
    assert catalog.quote().json()["price_version"] == "TEST_ONLY_v1"
    with catalog.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM price_versions WHERE spec_id=:id"),
                {"id": catalog.spec_id},
            ).scalar_one()
            == 1
        )


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


@pytest.mark.parametrize("amount", [True, 1.5, "7", -1])
def test_price_rejects_noninteger_or_negative_amount(catalog, amount):
    catalog.publish()
    assert catalog.price(amount, "TEST_ONLY_v2", "TEST_ONLY_v1").status_code == 422
    assert catalog.quote().json()["credits"] == 7


def test_parameter_schema_enforces_integer_boolean_and_combinations(catalog):
    catalog.parameter_schema = {
        "fields": {
            "length": {"kind": "integer", "required": True, "minimum": 1, "maximum": 5},
            "music": {"kind": "boolean", "required": True},
        },
        "combinations": [{"length": 3, "music": False}, {"length": 5, "music": True}],
    }
    catalog.set_policies()
    catalog.publish()
    for parameters in (
        {"length": True, "music": False},
        {"length": 3.0, "music": False},
        {"length": 3, "music": "false"},
        {"length": 3, "music": True},
    ):
        catalog.input["parameters"] = parameters
        assert catalog.quote().status_code == 422
    catalog.input["parameters"] = {"length": 3, "music": False}
    assert catalog.quote().status_code == 200


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


def test_spec_schema_must_match_reviewed_policy(catalog):
    assert catalog.agent().status_code == 201
    catalog.parameter_schema["fields"]["unreviewed"] = {"kind": "boolean", "required": False}
    assert catalog.spec().status_code == 403


def test_public_catalog_hides_disabled_specs(catalog):
    catalog.publish()
    assert (
        catalog.client.get(f"/api/v1/agents/{catalog.agent_id}/specs").json()[0]["spec_id"]
        == catalog.spec_id
    )
    assert (
        catalog.spec(version="TEST_ONLY_v2", expected="TEST_ONLY_v1", enabled=False).status_code
        == 201
    )
    assert catalog.client.get(f"/api/v1/agents/{catalog.agent_id}/specs").json() == []
    assert catalog.quote().status_code == 422


def test_current_price_read_ignores_repeatable_read_snapshot(catalog):
    from app.auth.service import AuthService
    from app.catalog.service import CatalogService
    from app.common.types import InputSnapshot

    catalog.publish()
    with Session(catalog.engine) as session:
        # Establish an old MVCC snapshot before the administrator commits a new version.
        assert (
            session.execute(
                text("SELECT COUNT(*) FROM price_versions WHERE spec_id=:id"),
                {"id": catalog.spec_id},
            ).scalar_one()
            == 1
        )
        catalog.set_policies(credits=11)
        assert catalog.price(11, "TEST_ONLY_v2", "TEST_ONLY_v1").status_code == 201
        actor = AuthService(session).require_active_principal(catalog.client.cookies["session"])
        quote = CatalogService(session, mode="mock").quote_generation(
            actor, InputSnapshot.model_validate(catalog.input), catalog.spec_id
        )
        assert quote.credits == 11 and quote.price_version == "TEST_ONLY_v2"


def test_validation_holds_price_until_caller_transaction_ends(catalog):
    from sqlalchemy.exc import OperationalError

    from app.catalog.service import CatalogService
    from app.common.types import InputSnapshot, Quote

    catalog.publish()
    quote = Quote.model_validate(catalog.quote().json())
    with Session(catalog.engine) as session:
        result = CatalogService(session, mode="mock").validate_confirmed_quote(
            quote, InputSnapshot.model_validate(catalog.input)
        )
        assert result.quote.credits == 7
        with catalog.engine.connect() as connection, connection.begin():
            connection.execute(text("SET SESSION innodb_lock_wait_timeout=1"))
            with pytest.raises(OperationalError) as error:
                connection.execute(
                    text("UPDATE price_heads SET version=version WHERE spec_id=:id"),
                    {"id": catalog.spec_id},
                )
            assert error.value.orig.args[0] == 1205
        session.rollback()
    assert catalog.price(version="TEST_ONLY_v2", expected="TEST_ONLY_v1").status_code == 201


def test_stale_error_wire_contract(catalog):
    from fastapi import Request

    from app.auth.routes import DB, PrincipalDep
    from app.catalog.service import CatalogService
    from app.common.types import InputSnapshot, Quote

    catalog.publish()
    quote = catalog.quote().json()
    catalog.set_policies(credits=0)
    assert catalog.price(0, "TEST_ONLY_v2", "TEST_ONLY_v1").status_code == 201

    @catalog.client.app.post("/TEST_ONLY/confirm")
    def confirm(
        quote: Quote, input: InputSnapshot, request: Request, session: DB, principal: PrincipalDep
    ):
        return CatalogService(session, mode="mock").validate_confirmed_quote(quote, input)

    response = catalog.client.post(
        "/TEST_ONLY/confirm", json={"quote": quote, "input": catalog.input}
    )
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "QUOTE_STALE"
    assert error["current_quotes"][0]["credits"] == 0
    assert error["current_specs"][0]["spec_id"] == catalog.spec_id
    assert "secret-endpoint" not in response.text and "TEST_ONLY_SECRET_REF" not in response.text


def test_rr_new_spec_identity_is_current(catalog):
    from app.auth.service import AuthService
    from app.catalog.service import CatalogService
    from app.common.types import InputSnapshot

    with Session(catalog.engine) as session:
        assert (
            session.execute(
                text("SELECT COUNT(*) FROM generation_specs WHERE spec_id=:id"),
                {"id": catalog.spec_id},
            ).scalar_one()
            == 0
        )
        transaction = session.get_transaction()
        catalog.publish()
        actor = AuthService(session).require_active_principal(catalog.client.cookies["session"])
        quote = CatalogService(session, mode="mock").quote_generation(
            actor, InputSnapshot.model_validate(catalog.input), catalog.spec_id
        )
        assert quote.credits == 7 and str(quote.spec_id) == catalog.spec_id
        assert session.get_transaction() is transaction
        # A successful current quote must not refresh or replace the caller's RR snapshot.
        assert (
            session.execute(
                text("SELECT COUNT(*) FROM generation_specs WHERE spec_id=:id"),
                {"id": catalog.spec_id},
            ).scalar_one()
            == 0
        )


def test_rr_stale_quote_includes_new_replacement(catalog):
    from app.catalog.service import CatalogError, CatalogService
    from app.common.types import InputSnapshot, Quote

    catalog.publish()
    quote = Quote.model_validate(catalog.quote().json())
    old_id = catalog.spec_id
    with Session(catalog.engine) as session:
        assert (
            session.execute(
                text("SELECT COUNT(*) FROM generation_specs WHERE spec_id=:id"), {"id": old_id}
            ).scalar_one()
            == 1
        )
        transaction = session.get_transaction()
        assert (
            catalog.spec(version="TEST_ONLY_v2", expected="TEST_ONLY_v1", enabled=False).status_code
            == 201
        )
        catalog.spec_id = str(uuid4())
        catalog.set_policies()
        assert catalog.spec().status_code == 201
        assert catalog.price().status_code == 201
        available = catalog.client.get(f"/api/v1/agents/{catalog.agent_id}/specs").json()
        assert any(item["spec_id"] == catalog.spec_id for item in available)
        with pytest.raises(CatalogError) as error:
            CatalogService(session, mode="mock").validate_confirmed_quote(
                quote, InputSnapshot.model_validate(catalog.input)
            )
        assert error.value.status_code == 409 and error.value.code == "QUOTE_STALE"
        assert [str(spec.spec_id) for spec in error.value.current_specs] == [catalog.spec_id]
        assert [str(item.spec_id) for item in error.value.current_quotes] == [catalog.spec_id]
        assert error.value.current_quotes[0].credits == 7
        assert session.get_transaction() is transaction
        assert (
            session.execute(
                text("SELECT COUNT(*) FROM generation_specs WHERE spec_id=:id"),
                {"id": catalog.spec_id},
            ).scalar_one()
            == 0
        )


def test_rr_agent_enumeration_and_historical_price_discovery_are_current(catalog):
    from app.catalog.service import CatalogService

    with Session(catalog.engine) as session:
        assert (
            session.execute(
                text("SELECT COUNT(*) FROM agent_heads WHERE agent_id=:id"),
                {"id": catalog.agent_id},
            ).scalar_one()
            == 0
        )
        transaction = session.get_transaction()
        catalog.publish()
        service = CatalogService(session, mode="mock")
        assert any(str(agent.agent_id) == catalog.agent_id for agent in service.list_agents())
        price = service.read_price_version(catalog.spec_id, "TEST_ONLY_v1")
        assert price is not None and price.credits == 7
        assert any(str(spec.spec_id) == catalog.spec_id for spec in service.list_specs())
        assert session.get_transaction() is transaction
        assert (
            session.execute(
                text("SELECT COUNT(*) FROM agent_heads WHERE agent_id=:id"),
                {"id": catalog.agent_id},
            ).scalar_one()
            == 0
        )


def test_current_identity_and_earlier_version_publication_do_not_deadlock(catalog):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from sqlalchemy.exc import OperationalError

    from app.auth.service import AuthService
    from app.catalog.models import AgentHead
    from app.catalog.schemas import SpecDraft
    from app.catalog.service import CatalogService

    catalog.publish()
    identity_read, publisher_has_head = Event(), Event()

    class Reader(CatalogService):
        def _head(self, table, key, id, **kwargs):
            if table is AgentHead:
                identity_read.set()
                assert publisher_has_head.wait(8)
            return super()._head(table, key, id, **kwargs)

    class Publisher(CatalogService):
        def _append(self, *args, **kwargs):
            publisher_has_head.set()
            return super()._append(*args, **kwargs)

    def read():
        with Session(catalog.engine) as session:
            session.execute(text("SET SESSION innodb_lock_wait_timeout=4"))
            assert (
                session.execute(
                    text("SELECT COUNT(*) FROM generation_specs WHERE spec_id=:id"),
                    {"id": catalog.spec_id},
                ).scalar_one()
                == 1
            )
            transaction = session.get_transaction()
            try:
                spec, _ = Reader(session, mode="mock")._current_spec(catalog.spec_id)
                assert spec.version == "A_TEST_ONLY_v2"
                assert session.get_transaction() is transaction
                assert (
                    session.execute(
                        text("SELECT COUNT(*) FROM generation_specs WHERE spec_id=:id"),
                        {"id": catalog.spec_id},
                    ).scalar_one()
                    == 1
                )
                return {"role": "reader", "ok": True}
            except OperationalError as error:
                return {"role": "reader", "mysql_code": error.orig.args[0]}

    def publish():
        assert identity_read.wait(8)
        with Session(catalog.engine) as session:
            session.execute(text("SET SESSION innodb_lock_wait_timeout=4"))
            actor = AuthService(session).require_active_principal(catalog.client.cookies["session"])
            draft = SpecDraft(
                spec_id=catalog.spec_id,
                agent_id=catalog.agent_id,
                agent_version="TEST_ONLY_v1",
                version="A_TEST_ONLY_v2",
                expected_version="TEST_ONLY_v1",
                enabled=True,
                name="TEST_ONLY earlier version",
                parameter_schema=catalog.parameter_schema,
                delivery_kind="single",
                policy_versions=catalog.policies,
                reason="TEST_ONLY deterministic identity lock regression",
            )
            try:
                Publisher(session, mode="mock").publish_spec_version(actor, draft)
                session.commit()
                return {"role": "publisher", "ok": True}
            except OperationalError as error:
                return {"role": "publisher", "mysql_code": error.orig.args[0]}

    with ThreadPoolExecutor(max_workers=2) as pool:
        reader = pool.submit(read)
        publisher = pool.submit(publish)
        results = [reader.result(timeout=15), publisher.result(timeout=15)]
    assert all(result.get("ok") for result in results), results


def test_stable_identity_preserves_history_and_rejects_reassignment(catalog):
    from sqlalchemy import inspect
    from sqlalchemy.exc import DBAPIError

    assert inspect(catalog.engine).has_table("spec_identities")
    catalog.publish()
    with catalog.engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM generation_specs s LEFT JOIN spec_identities i "
                    "ON s.spec_id=i.spec_id AND s.agent_id=i.agent_id WHERE i.spec_id IS NULL"
                )
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                text("SELECT agent_id FROM spec_identities WHERE spec_id=:id"),
                {"id": catalog.spec_id},
            ).scalar_one()
            == catalog.agent_id
        )
    for statement in (
        "UPDATE spec_identities SET agent_id=agent_id WHERE spec_id=:id",
        "DELETE FROM spec_identities WHERE spec_id=:id",
    ):
        with catalog.engine.connect() as connection, connection.begin():
            with pytest.raises(DBAPIError):
                connection.execute(text(statement), {"id": catalog.spec_id})

    original_agent = catalog.agent_id
    catalog.agent_id = str(uuid4())
    catalog.set_policies()
    assert catalog.agent().status_code == 201
    assert catalog.spec(version="TEST_ONLY_wrong_owner", expected="TEST_ONLY_v1").status_code == 409
    with catalog.engine.connect() as connection, connection.begin():
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    "INSERT INTO generation_specs(spec_id,version,agent_id,agent_version,snapshot) "
                    "SELECT spec_id,'TEST_ONLY_direct_wrong_owner',:other,agent_version,snapshot "
                    "FROM generation_specs WHERE spec_id=:id AND version='TEST_ONLY_v1'"
                ),
                {"id": catalog.spec_id, "other": catalog.agent_id},
            )
    with catalog.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT agent_id FROM spec_identities WHERE spec_id=:id"),
                {"id": catalog.spec_id},
            ).scalar_one()
            == original_agent
        )


def test_concurrent_first_publications_share_one_stable_identity(catalog):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy.exc import OperationalError

    from app.auth.service import AuthService
    from app.catalog.schemas import SpecDraft
    from app.catalog.service import CatalogError, CatalogService

    assert catalog.agent().status_code == 201
    first_token = catalog.client.cookies["session"]
    registration = catalog.client.post(
        "/api/v1/auth/register",
        json={
            "account": "cat_" + uuid4().hex,
            "password": "TEST_ONLY_password",
            "request_key": uuid4().hex,
        },
    )
    assert registration.status_code == 201
    second_user = registration.json()["profile"]["user_id"]
    assert second_user != catalog.user
    with catalog.engine.begin() as connection:
        connection.execute(text("UPDATE users SET role='admin' WHERE id=:id"), {"id": second_user})
    second_token = catalog.client.cookies["session"]
    publishers_ready = Barrier(2, timeout=8)

    class ConcurrentPublisher(CatalogService):
        def _spec_gate(self, spec):
            super()._spec_gate(spec)
            # Both independent admins reach actual publication before either can
            # insert the new identity. SQL and transaction ownership are unchanged.
            publishers_ready.wait()

    def publish(token):
        with Session(catalog.engine) as session:
            session.execute(text("SET SESSION innodb_lock_wait_timeout=4"))
            actor = AuthService(session).require_active_principal(token)
            draft = SpecDraft(
                spec_id=catalog.spec_id,
                agent_id=catalog.agent_id,
                agent_version="TEST_ONLY_v1",
                version="TEST_ONLY_v1",
                expected_version=None,
                enabled=True,
                name="TEST_ONLY spec",
                parameter_schema=catalog.parameter_schema,
                delivery_kind="single",
                policy_versions=catalog.policies,
                reason="TEST_ONLY first publication race",
            )
            try:
                ConcurrentPublisher(session, mode="mock").publish_spec_version(actor, draft)
                session.commit()
                return 201
            except CatalogError as error:
                session.rollback()
                return error.status_code
            except OperationalError as error:
                session.rollback()
                return error.orig.args[0]

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(publish, first_token)
        second = pool.submit(publish, second_token)
        assert sorted([first.result(timeout=15), second.result(timeout=15)]) == [201, 409]
    with catalog.engine.connect() as connection:
        for table in ("spec_identities", "generation_specs", "spec_heads"):
            assert (
                connection.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE spec_id=:id"), {"id": catalog.spec_id}
                ).scalar_one()
                == 1
            )
        assert (
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM audit_events "
                    "WHERE object_id=:id AND action='catalog_spec'"
                ),
                {"id": catalog.spec_id},
            ).scalar_one()
            == 1
        )
