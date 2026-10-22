"""T07 behavior on real MySQL; no adapter or Redis invocation during admission."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import uuid4

import pytest
import test_catalog_quotes as catalog_tests
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.policies.schemas import DecisionVersion
from app.policies.service import PolicyService

catalog = catalog_tests.catalog


@pytest.fixture
def admission(catalog):
    c = catalog
    versions = {}
    payloads = {
        "D-01": {
            "agents": {
                c.agent_id: {
                    "protocol_version": "TEST_ONLY_protocol_v1",
                    **{
                        k: "TEST_ONLY_evidence"
                        for k in (
                            "input_schema_ref",
                            "authentication_ref",
                            "execution_ref",
                            "completion_ref",
                            "recovery_ref",
                            "callback_ref",
                            "error_ref",
                            "usage_ref",
                            "capabilities_ref",
                        )
                    },
                }
            }
        },
        "D-05": {"generation": {"max_concurrent_tasks": 5, "enforcement_ref": "TEST_ONLY_db"}},
        "D-08": {
            "generation": {
                "investigation_deadline_seconds": 60,
                "deadline_is_failure": False,
                "requires_complete_delivery": True,
                **{
                    k: "TEST_ONLY_evidence"
                    for k in (
                        "responsible_party_ref",
                        "settlement_evidence_ref",
                        "late_delivery_ref",
                        "save_failure_ref",
                    )
                },
            }
        },
        "D-09": {
            "generation": {
                k: "TEST_ONLY_evidence"
                for k in (
                    "inflight_protection_ref",
                    "exception_handoff_ref",
                    "disabled_account_tasks_ref",
                )
            }
        },
        "D-10": {
            "generation": {
                "account_quota_bytes": 200,
                "server_budget_bytes": 100000000,
                "reservation_seconds": 120,
                "estimation_ref": "TEST_ONLY_all_results",
                "reclamation_ref": "TEST_ONLY_manual",
                "alert_ref": "TEST_ONLY_monitor",
                "allowed_download_sources": ["TEST_ONLY_source"],
                "max_download_bytes": 50,
                "download_timeout_seconds": 10,
                "max_redirects": 0,
                "link_validity_ref": "TEST_ONLY_evidence",
                "recovery_ref": "TEST_ONLY_evidence",
            },
            "upload": {
                "max_file_bytes": 180,
                "account_quota_bytes": 200,
                "allowed_types": ["image/png"],
                "reservation_seconds": 120,
                "reclamation_ref": "TEST_ONLY_manual",
                "alert_ref": "TEST_ONLY_monitor",
            },
        },
    }
    with Session(c.engine) as s, s.begin():
        for decision, payload in payloads.items():
            version = "TEST_ONLY_" + uuid4().hex
            PolicyService(s).add_draft(
                DecisionVersion(
                    decision_id=decision,
                    version=version,
                    mode="mock",
                    test_only=True,
                    payload=payload,
                )
            )
            versions[decision] = version
    settings = c.client.app.state.settings
    # Trusted runtime configuration, deliberately absent by default.
    settings = settings.model_copy(update={"generation_policy_versions": versions})
    settings = settings.model_copy(
        update={
            "generation_capacity_estimates": {
                c.agent_id: {
                    "spec_version": "TEST_ONLY_v1",
                    "policy_version": versions["D-10"],
                    "estimation_ref": "TEST_ONLY_all_results",
                    "total_bytes": 50,
                }
            }
        }
    )
    c.client.app.state.settings = settings
    settings.storage_policy_version = versions["D-10"]
    c.input_support["max_materials"] = 2
    c.set_policies()
    c.publish()
    return c


def request_body(c):
    conversation = c.client.post("/api/v1/conversations", json={"title": "TEST_ONLY conversation"})
    assert conversation.status_code == 201, conversation.text
    product = c.client.post("/api/v1/products/versions", json={"product": {"name": "cup"}})
    assert product.status_code == 201, product.text
    c.input["product_version"] = product.json()["version"]
    quote = c.quote()
    assert quote.status_code == 200, quote.text
    return {
        "conversation_id": conversation.json()["conversation_id"],
        "agent_id": c.agent_id,
        "input": deepcopy(c.input),
        "confirmed_quote": quote.json(),
    }


def submit(c, body, key=None):
    return c.client.post(
        "/api/v1/tasks", json=body, headers={"Idempotency-Key": key or uuid4().hex}
    )


def counts(c):
    with c.engine.connect() as conn:
        result = {}
        for table in (
            "generation_tasks",
            "task_snapshots",
            "credit_reservations",
            "capacity_reservations",
            "file_refs",
            "dispatch_outbox",
            "durable_events",
            "messages",
            "task_state_events",
        ):
            result[table] = conn.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE user_id=:u"), {"u": c.user}
            ).scalar_one()
        result["ledger"] = conn.execute(
            text("SELECT COUNT(*) FROM credit_ledger WHERE user_id=:u"), {"u": c.user}
        ).scalar_one()
        result["balances"] = tuple(
            conn.execute(
                text("SELECT available,frozen,consumed FROM credit_accounts WHERE user_id=:u"),
                {"u": c.user},
            ).one()
        )
        result["capacity"] = (
            conn.execute(
                text("SELECT reserved_bytes FROM storage_accounts WHERE user_id=:u"), {"u": c.user}
            ).scalar_one_or_none()
            or 0
        )
        return result


def test_same_key_same_body_one_task(admission):
    c = admission
    body, key = request_body(c), uuid4().hex
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda _: submit(c, body, key), range(3)))
    assert sorted(r.status_code for r in responses) == [200, 200, 201], [r.text for r in responses]
    assert len({r.json()["task"]["task_id"] for r in responses}) == 1
    assert counts(c) == {
        "generation_tasks": 1,
        "task_snapshots": 1,
        "credit_reservations": 1,
        "capacity_reservations": 1,
        "file_refs": 0,
        "dispatch_outbox": 1,
        "durable_events": 1,
        "ledger": 2,
        "balances": (93, 7, 0),
        "capacity": 50,
        "messages": 1,
        "task_state_events": 1,
    }


def test_same_key_changed_body_conflict(admission):
    c = admission
    body, key = request_body(c), uuid4().hex
    assert submit(c, body, key).status_code == 201
    before = counts(c)
    for change in ("instruction", "quote", "agent", "conversation"):
        other = deepcopy(body)
        if change == "instruction":
            other["input"]["instruction"] = "different"
        elif change == "quote":
            other["confirmed_quote"]["credits"] = 0
        else:
            other[change + "_id"] = str(uuid4())
        response = submit(c, other, key)
        assert (
            response.status_code == 409
            and response.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
        )
    assert counts(c) == before


def test_replay_after_reprice_returns_original(admission):
    c = admission
    body, key = request_body(c), uuid4().hex
    first = submit(c, body, key)
    assert first.status_code == 201, first.text
    c.set_policies(credits=11)
    assert c.price(11).status_code == 200
    response = submit(c, body, key)
    assert response.status_code == 200 and response.json()["task"] == first.json()["task"]
    before = counts(c)
    response = submit(c, body)
    assert response.status_code == 409 and response.json()["error"]["code"] == "QUOTE_STALE"
    assert counts(c) == before
    assert c.agent(False, "TEST_ONLY_v2", "TEST_ONLY_v1").status_code == 201
    assert submit(c, body, key).json()["task"] == first.json()["task"]
    assert submit(c, body).status_code == 409
    assert counts(c) == before


@pytest.mark.parametrize(
    "write",
    [
        "generation_tasks",
        "task_snapshots",
        "credit_reservations",
        "credit_ledger",
        "capacity_reservations",
        "dispatch_outbox",
        "durable_events",
        "messages",
        "task_state_events",
    ],
)
def test_insufficient_interrupt_no_side_effect(admission, write):
    c = admission
    body = request_body(c)
    before = counts(c)

    def interrupt(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO " + write + " "):
            raise RuntimeError("TEST_ONLY admission interrupted")

    engine = c.client.app.state.engine
    event.listen(engine, "before_cursor_execute", interrupt)
    try:
        assert submit(c, body).status_code == 500
    finally:
        event.remove(engine, "before_cursor_execute", interrupt)
    assert counts(c) == before
    assert submit(c, body).status_code == 201


def test_insufficient_credits_no_side_effect(admission):
    c = admission
    body = request_body(c)
    c.set_policies(credits=101)
    assert c.price(101).status_code == 200
    body["confirmed_quote"] = c.quote().json()
    before = counts(c)
    assert submit(c, body).status_code == 402
    assert counts(c) == before


def test_snapshot_immutable_after_edit(admission):
    c = admission
    body = request_body(c)
    result = submit(c, body)
    assert result.status_code == 201, result.text
    task_id = result.json()["task"]["task_id"]
    product = c.client.get("/api/v1/products/versions/" + body["input"]["product_version"]).json()
    assert (
        c.client.post(
            "/api/v1/products/versions",
            json={"product_id": product["product_id"], "product": {"name": "plate"}},
        ).status_code
        == 201
    )
    detail = c.client.get("/api/v1/tasks/" + task_id)
    assert detail.status_code == 200, detail.text
    assert detail.json()["input"] == body["input"]
    assert detail.json()["task"]["quote"] == body["confirmed_quote"]
    assert "secret-endpoint" not in detail.text and "TEST_ONLY_SECRET_REF" not in detail.text
    from sqlalchemy.exc import DBAPIError

    with c.engine.connect() as conn, conn.begin():
        with pytest.raises(DBAPIError):
            conn.execute(
                text("UPDATE task_snapshots SET input_snapshot=JSON_OBJECT() WHERE task_id=:t"),
                {"t": task_id},
            )
    assert submit(c, body).status_code == 201
    assert counts(c)["generation_tasks"] == 2


def test_owner_and_current_session_required_on_replay_and_reads(admission):
    c = admission
    body, key = request_body(c), uuid4().hex
    result = submit(c, body, key)
    assert result.status_code == 201, result.text
    task_id = result.json()["task"]["task_id"]
    old_cookies = dict(c.client.cookies)
    response = c.client.post(
        "/api/v1/auth/register",
        json={
            "account": "other_" + uuid4().hex,
            "password": "TEST_ONLY_password",
            "request_key": uuid4().hex,
        },
    )
    assert response.status_code == 201
    c.client.headers["X-CSRF-Token"] = c.client.cookies["csrf_token"]
    for url in (
        "/api/v1/tasks/" + task_id,
        "/api/v1/conversations/" + body["conversation_id"],
        "/api/v1/products/versions/" + body["input"]["product_version"],
        "/api/v1/tasks?conversation_id=" + body["conversation_id"],
    ):
        assert c.client.get(url).status_code == 404
    assert submit(c, body).status_code == 404
    c.client.cookies.clear()
    c.client.cookies.update(old_cookies)
    c.client.headers["X-CSRF-Token"] = old_cookies["csrf_token"]
    with c.engine.begin() as conn:
        conn.execute(text("UPDATE users SET status='disabled' WHERE id=:u"), {"u": c.user})
    assert submit(c, body, key).status_code == 401
    assert c.client.get("/api/v1/tasks/" + task_id).status_code == 401


def test_fail_closed_policy_capacity_and_product(admission, monkeypatch):
    c = admission
    body = request_body(c)
    before = counts(c)
    versions = c.client.app.state.settings.generation_policy_versions
    c.client.app.state.settings.generation_policy_versions = {}
    assert submit(c, body).status_code == 403
    c.client.app.state.settings.generation_policy_versions = versions
    from app.storage.local_store import LocalStore

    monkeypatch.setattr(LocalStore, "free_bytes", lambda self: 49)
    assert submit(c, body).status_code == 409
    monkeypatch.undo()
    body["input"]["product"]["name"] = "forged"
    c.input = deepcopy(body["input"])
    body["confirmed_quote"] = c.quote().json()
    assert submit(c, body).status_code == 422
    assert counts(c) == before


def material_body(c):
    from test_capacity import upload

    ref = upload(c.client)
    assert ref.status_code == 201, ref.text
    c.input["material_versions"] = [ref.json()]
    return request_body(c)


def test_material_exact_version_bytes_and_reference_rollback(admission):
    c = admission
    body = material_body(c)
    before = counts(c)

    def interrupt(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO file_refs "):
            raise RuntimeError("TEST_ONLY material interrupted")

    engine = c.client.app.state.engine
    event.listen(engine, "before_cursor_execute", interrupt)
    try:
        assert submit(c, body).status_code == 500
    finally:
        event.remove(engine, "before_cursor_execute", interrupt)
    assert counts(c) == before
    response = submit(c, body)
    assert response.status_code == 201, response.text
    assert counts(c)["file_refs"] == 1
    with c.engine.connect() as conn:
        row = conn.execute(
            text("SELECT ref_id,version FROM file_refs WHERE user_id=:u"), {"u": c.user}
        ).one()
        assert row.ref_id == response.json()["task"]["task_id"]
        assert row.version == body["input"]["material_versions"][0]["version"]


@pytest.mark.parametrize("change", ["version", "unknown", "missing", "corrupt"])
def test_bad_material_never_leaves_task(admission, change):
    c = admission
    body = material_body(c)
    file_id = body["input"]["material_versions"][0]["file_id"]
    expected = 404
    if change == "version":
        body["input"]["material_versions"][0]["version"] = str(uuid4())
    elif change == "unknown":
        body["input"]["material_versions"][0]["file_id"] = str(uuid4())
    else:
        from app.storage.local_store import LocalStore

        with c.engine.connect() as conn:
            path = conn.execute(
                text("SELECT internal_path FROM files WHERE id=:id"), {"id": file_id}
            ).scalar_one()
        path = LocalStore(c.client.app.state.settings.storage_root)._path(path, ".blob")
        if change == "missing":
            path.unlink()
        else:
            path.write_bytes(b"corrupt")
        expected = 422
    c.input = deepcopy(body["input"])
    body["confirmed_quote"] = c.quote().json()
    before = counts(c)
    assert submit(c, body).status_code == expected
    assert counts(c) == before


def test_concurrent_new_keys_obey_task_policy_without_account_quota(admission):
    c = admission
    body = request_body(c)
    with ThreadPoolExecutor(max_workers=6) as pool:
        responses = list(pool.map(lambda _: submit(c, body), range(6)))
    assert sorted(r.status_code for r in responses) == [201, 201, 201, 201, 201, 429], [
        r.text for r in responses
    ]
    assert counts(c)["balances"] == (65, 35, 0)
    assert counts(c)["capacity"] == 250
    with c.engine.connect() as conn:
        assert list(
            conn.execute(
                text("SELECT event_seq FROM durable_events WHERE user_id=:u ORDER BY event_seq"),
                {"u": c.user},
            ).scalars()
        ) == [1, 2, 3, 4, 5]


@pytest.mark.parametrize("max_tasks,expected", [(1, [201, 429]), (None, [201, 201])])
def test_concurrency_gate_with_adequate_capacity(admission, max_tasks, expected):
    c = admission
    body = request_body(c)
    settings = c.client.app.state.settings
    version = "TEST_ONLY_" + uuid4().hex
    with Session(c.engine) as s, s.begin():
        PolicyService(s).add_draft(
            DecisionVersion(
                decision_id="D-05",
                version=version,
                mode="mock",
                test_only=True,
                payload={
                    "generation": {"max_concurrent_tasks": max_tasks,
                                   "enforcement_ref": "TEST_ONLY_db"}
                },
            )
        )
    settings.generation_policy_versions["D-05"] = version
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: submit(c, body), range(2)))
    assert sorted(r.status_code for r in responses) == expected, [r.text for r in responses]
    accepted = expected.count(201)
    assert counts(c)["capacity"] == 50 * accepted
    assert counts(c)["balances"] == (100 - 7 * accepted, 7 * accepted, 0)


def test_outbox_and_event_writers_share_transaction(admission):
    from app.auth.service import AuthService
    from app.dispatch.outbox import enqueue_outbox
    from app.events.service import append_durable_event

    c = admission
    body = request_body(c)
    response = submit(c, body)
    assert response.status_code == 201, response.text
    task = response.json()["task"]
    before = counts(c)
    with Session(c.engine) as s:
        AuthService(s).require_active_principal(c.client.cookies["session"])
        a = enqueue_outbox(s, task["task_id"], "submit")
        assert enqueue_outbox(s, task["task_id"], "submit").event_id == a.event_id
        enqueue_outbox(s, task["task_id"], "recover")
        payload = {k: task[k] for k in ("task_id", "state", "state_version")}
        e = append_durable_event(s, c.user, "task.updated", payload, event_key="TEST_ONLY_repeat")
        assert (
            append_durable_event(
                s, c.user, "task.updated", payload, event_key="TEST_ONLY_repeat"
            ).id
            == e.id
        )
        s.rollback()
    assert counts(c) == before


def test_no_upstream_or_redis_during_admission_and_paged_history(admission, monkeypatch):
    from app.agents.mock import MockAgentAdapter
    from app.agents.registry import AgentRegistry

    c = admission
    body = request_body(c)

    def forbidden(*args, **kwargs):
        raise AssertionError("Admission must not contact an agent")

    monkeypatch.setattr(AgentRegistry, "get", forbidden)
    monkeypatch.setattr(MockAgentAdapter, "submit", forbidden)
    c.client.app.state.auth_redis = None
    ids = []
    for _ in range(3):
        response = submit(c, body)
        assert response.status_code == 201, response.text
        ids.append(response.json()["task"]["task_id"])
    page = c.client.get(
        "/api/v1/tasks", params={"conversation_id": body["conversation_id"], "limit": 2}
    ).json()
    assert [t["task_id"] for t in page["items"]] == ids[::-1][:2]
    next_page = c.client.get(
        "/api/v1/tasks",
        params={
            "conversation_id": body["conversation_id"],
            "limit": 2,
            "cursor": page["next_cursor"],
        },
    ).json()
    assert [t["task_id"] for t in next_page["items"]] == ids[:1]
    conversation = c.client.get("/api/v1/conversations/" + body["conversation_id"]).json()
    assert len(conversation["tasks"]["items"]) == len(conversation["messages"]["items"]) == 3


def test_real_foreign_material_and_admin_content_scope(admission):
    from test_capacity import upload

    c = admission
    body = request_body(c)
    old_cookies = dict(c.client.cookies)
    result = c.client.post(
        "/api/v1/auth/register",
        json={
            "account": "material_" + uuid4().hex,
            "password": "TEST_ONLY_password",
            "request_key": uuid4().hex,
        },
    )
    assert result.status_code == 201
    c.client.headers["X-CSRF-Token"] = c.client.cookies["csrf_token"]
    foreign = upload(c.client)
    assert foreign.status_code == 201, foreign.text
    c.client.cookies.clear()
    c.client.cookies.update(old_cookies)
    c.client.headers["X-CSRF-Token"] = old_cookies["csrf_token"]
    # The original catalog fixture is an admin. That role does not authorize content.
    c.input["material_versions"] = [foreign.json()]
    body["input"] = deepcopy(c.input)
    body["confirmed_quote"] = c.quote().json()
    before = counts(c)
    assert submit(c, body).status_code == 404
    assert counts(c) == before


@pytest.mark.parametrize("decision", ["D-01", "D-05", "D-08", "D-09", "D-10"])
def test_each_server_generation_decision_required(admission, decision):
    c = admission
    body = request_body(c)
    before = counts(c)
    del c.client.app.state.settings.generation_policy_versions[decision]
    assert submit(c, body).status_code == 403
    assert counts(c) == before


def test_direct_admission_retains_quote_locks_and_rollback(admission):
    from concurrent.futures import TimeoutError
    from threading import Event

    from app.auth.service import AuthService
    from app.common.types import SubmitTaskRequest
    from app.tasks.admission import AdmissionService

    c = admission
    body = request_body(c)
    before = counts(c)
    entered = Event()

    def lock_price():
        with c.engine.connect() as conn, conn.begin():
            entered.set()
            conn.execute(
                text("SELECT version FROM generation_parameter_heads WHERE mode='mock' FOR UPDATE"),
                {"id": c.spec_id},
            ).one()
            return "acquired"

    with Session(c.engine) as s:
        actor = AuthService(s).require_active_principal(c.client.cookies["session"])
        AdmissionService(s, c.client.app.state.settings).admit_task(
            actor, uuid4().hex, SubmitTaskRequest.model_validate(body)
        )
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(lock_price)
            assert entered.wait(2)
            try:
                with pytest.raises(TimeoutError):
                    pending.result(timeout=0.2)
            finally:
                s.rollback()
            assert pending.result(timeout=2) == "acquired"
    assert counts(c) == before


def test_database_rejects_task_owner_mismatch_and_ledger_orphan(admission):
    from sqlalchemy.exc import DBAPIError

    c = admission
    body = request_body(c)
    result = submit(c, body)
    assert result.status_code == 201
    with c.engine.connect() as conn, conn.begin():
        with pytest.raises(DBAPIError):
            conn.execute(
                text("UPDATE credit_reservations SET task_id=:bad WHERE user_id=:u"),
                {"bad": str(uuid4()), "u": c.user},
            )
    from fastapi import HTTPException

    from app.ledger.service import freeze_credits

    with Session(c.engine) as s:
        with pytest.raises(HTTPException) as exc:
            freeze_credits(s, c.user, uuid4(), 1)
        assert exc.value.status_code == 404


def test_concurrent_different_accounts_share_budget_without_deadlock(admission):
    from fastapi.testclient import TestClient

    c = admission
    body1 = request_body(c)
    with TestClient(c.client.app, base_url="https://testserver") as other:
        other.headers.update({"Origin": "https://testserver", "X-Requested-With": "platform"})
        r = other.post(
            "/api/v1/auth/register",
            json={
                "account": "parallel_" + uuid4().hex,
                "password": "TEST_ONLY_password",
                "request_key": uuid4().hex,
            },
        )
        assert r.status_code == 201
        other.headers["X-CSRF-Token"] = other.cookies["csrf_token"]
        conversation = other.post("/api/v1/conversations", json={"title": "other"}).json()
        product = other.post("/api/v1/products/versions", json={"product": {"name": "cup"}}).json()
        body2 = deepcopy(body1)
        body2["conversation_id"] = conversation["conversation_id"]
        body2["input"]["product_version"] = product["version"]
        body2["confirmed_quote"] = other.post(
            "/api/v1/quotes", json={"agent_id": c.agent_id, "input": body2["input"]}
        ).json()
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(submit, c, body1)
            b = pool.submit(
                other.post, "/api/v1/tasks", json=body2, headers={"Idempotency-Key": uuid4().hex}
            )
            results = [a.result(), b.result()]
        assert [r.status_code for r in results] == [201, 201], [r.text for r in results]
