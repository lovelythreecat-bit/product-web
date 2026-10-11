"""Prompt assistance integration tests: real MySQL/API, no generation side effects."""

from copy import deepcopy
from uuid import uuid4

import pytest
import test_catalog_quotes as catalog_tests
import test_task_admission as admission_tests
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.policies.schemas import DecisionVersion
from app.policies.service import PolicyService

catalog = catalog_tests.catalog
admission = admission_tests.admission


@pytest.fixture
def assist(admission):
    c = admission
    c.assist_version = "TEST_ONLY_" + uuid4().hex
    with Session(c.engine) as session, session.begin():
        PolicyService(session).add_draft(
            DecisionVersion(
                decision_id="D-05",
                version=c.assist_version,
                mode="mock",
                test_only=True,
                payload={
                    "assist": {
                        "scheme": "OTHER_CONFIRMED_SCHEME",
                        "policy_ref": "TEST_ONLY_draft_no_meter_v1",
                        "implementation_ref": "TEST_ONLY_draft_no_meter_v1",
                    }
                },
            )
        )
    c.client.app.state.settings = c.client.app.state.settings.model_copy(
        update={
            "assist_policy_version": c.assist_version,
            "assist_provider": "deterministic_mock",
            "assist_rate_limit": 30,
            "assist_timeout_seconds": 0.1,
        }
    )
    c.body = {
        "agent_id": c.agent_id,
        "agent_version": "TEST_ONLY_v1",
        "spec_id": c.spec_id,
        "spec_version": "TEST_ONLY_v1",
        "original": "",
        "product": {"name": "cup"},
        "parameters": {"tone": "plain"},
        "material_versions": [],
    }
    return c


def post(c, body=None, key=None):
    return c.client.post(
        "/api/v1/assist/prompts",
        json=body or c.body,
        headers={"Idempotency-Key": key or uuid4().hex},
    )


def facts(c):
    with c.engine.connect() as conn:
        result = {
            name: conn.execute(
                text(f"SELECT COUNT(*) FROM {name} WHERE user_id=:u"), {"u": c.user}
            ).scalar_one()
            for name in (
                "generation_tasks",
                "task_snapshots",
                "credit_reservations",
                "dispatch_outbox",
                "credit_ledger",
            )
        }
        result["balance"] = tuple(
            conn.execute(
                text("SELECT available,frozen,consumed FROM credit_accounts WHERE user_id=:u"),
                {"u": c.user},
            ).one()
        )
        return result


def test_assist_no_generation_task(assist):
    c = assist
    before = facts(c)
    response = post(c)
    assert response.status_code == 200, response.text
    assert facts(c) == before
    assert before["balance"] == (100, 0, 0)
    assert response.json()["policy_version"] == c.assist_version
    assert response.json()["test_only"] is True
    print({"database_before": before, "database_after": facts(c)})


def test_original_restore_edit_reoptimize(assist):
    c = assist
    for original in ("", "  一个简短描述\n", "重新编辑的原文"):
        body = deepcopy(c.body)
        body["original"] = original
        response = post(c, body)
        assert response.status_code == 200, response.text
        assert response.json()["original"] == original
        assert response.json()["parameters"] == body["parameters"]


def test_no_invented_facts(assist):
    response = post(assist)
    assert response.status_code == 200, response.text
    result = response.json()
    assert {"material", "efficacy", "price", "promotion"} <= set(result["missing_facts"])
    assert all(word not in result["proposed"] for word in ("陶瓷", "抗菌", "99元", "五折"))


def test_d05_unconfirmed_blocks_live(assist):
    assist.client.app.state.settings = assist.client.app.state.settings.model_copy(
        update={"mode": "production", "test_only": False}
    )
    response = post(assist)
    assert response.status_code == 403, response.text


def test_real_mysql_identity(assist):
    with assist.engine.connect() as conn:
        row = conn.execute(text("SELECT VERSION(), DATABASE(), CURRENT_USER()")).one()
    assert row[0].startswith("8.4.")
    print({"mysql_identity": tuple(row)})


@pytest.mark.parametrize(
    "field,value,status",
    [
        ("agent_version", "stale", 409),
        ("spec_version", "stale", 409),
        ("agent_id", "00000000-0000-0000-0000-000000000001", 422),
        ("parameters", {"tone": "unsupported"}, 422),
        (
            "material_versions",
            [{"file_id": "00000000-0000-0000-0000-000000000001", "version": "wrong"}],
            404,
        ),
    ],
)
def test_current_capability_and_material_validation(assist, field, value, status):
    assist.body[field] = value
    assert post(assist).status_code == status


def test_incomplete_form_is_a_draft(assist):
    assist.body["product"] = {}
    assist.body["parameters"] = {}
    response = post(assist)
    assert response.status_code == 200, response.text
    assert "name" in response.json()["missing_facts"]
    assert "parameters.tone" in response.json()["missing_facts"]
    assert response.json()["parameters"] == {}


@pytest.mark.parametrize("header", ["Origin", "X-CSRF-Token", "X-Requested-With"])
def test_mutation_headers(assist, header):
    assist.client.headers.pop(header)
    assert post(assist).status_code == 403


@pytest.mark.parametrize(
    "payload",
    [
        {"registration": {"credits": 100}},
        {"assist": {"scheme": "UNDECIDED"}},
        {
            "assist": {
                "scheme": "OTHER_CONFIRMED_SCHEME",
                "policy_ref": "unimplemented",
                "implementation_ref": "unimplemented",
            }
        },
    ],
)
def test_incomplete_or_unimplemented_policy_rejected(assist, payload):
    version = "TEST_ONLY_" + uuid4().hex
    with Session(assist.engine) as session, session.begin():
        PolicyService(session).add_draft(
            DecisionVersion(
                decision_id="D-05", version=version, mode="mock", test_only=True, payload=payload
            )
        )
    assist.client.app.state.settings.assist_policy_version = version
    assert post(assist).status_code == 403


def test_provider_not_configured(assist):
    assist.client.app.state.settings.assist_provider = None
    assert post(assist).status_code == 403


def test_basic_rate_limit(assist):
    assist.client.app.state.settings.assist_rate_limit = 1
    assert post(assist).status_code == 200
    assert post(assist).status_code == 429
    assert facts(assist)["balance"] == (100, 0, 0)


@pytest.mark.parametrize("failure,status", [("timeout", 504), ("error", 503)])
def test_provider_failure_no_side_effects(assist, monkeypatch, failure, status):
    import asyncio

    from app.assist.provider import MockPromptAssistProvider

    async def broken(self, request):
        if failure == "timeout":
            await asyncio.sleep(1)
        raise RuntimeError("private provider detail")

    monkeypatch.setattr(MockPromptAssistProvider, "prepare", broken)
    before = facts(assist)
    response = post(assist)
    assert response.status_code == status, response.text
    assert "private provider detail" not in response.text
    assert facts(assist) == before


@pytest.mark.parametrize("mutation", ["disable", "revoke", "delist"])
def test_provider_outside_transaction_and_authoritative_recheck(assist, monkeypatch, mutation):
    from app.assist.provider import MockPromptAssistProvider

    original = MockPromptAssistProvider.prepare

    async def change_during_wait(self, request):
        # An independent connection can acquire the same user's lock during the provider wait.
        with assist.engine.begin() as conn:
            conn.execute(text("SET innodb_lock_wait_timeout=1"))
            conn.execute(text("SELECT id FROM users WHERE id=:u FOR UPDATE"), {"u": assist.user})
            if mutation == "disable":
                conn.execute(
                    text("UPDATE users SET status='disabled' WHERE id=:u"), {"u": assist.user}
                )
            elif mutation == "revoke":
                conn.execute(
                    text("UPDATE auth_sessions SET revoked_at=UTC_TIMESTAMP(6) WHERE user_id=:u"),
                    {"u": assist.user},
                )
            else:
                conn.execute(text("DELETE FROM spec_heads WHERE spec_id=:s"), {"s": assist.spec_id})
        return await original(self, request)

    monkeypatch.setattr(MockPromptAssistProvider, "prepare", change_during_wait)
    response = post(assist)
    assert response.status_code == (422 if mutation == "delist" else 401), response.text
    assert facts(assist)["balance"] == (100, 0, 0)


def test_request_idempotency_concurrency_and_conflict(assist, monkeypatch):
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Lock

    from app.assist.provider import MockPromptAssistProvider

    barrier, lock = Barrier(3), Lock()
    calls = []
    original = MockPromptAssistProvider.prepare

    async def concurrent(self, request):
        with lock:
            calls.append(1)
        await asyncio.to_thread(barrier.wait, 3)
        return await original(self, request)

    monkeypatch.setattr(MockPromptAssistProvider, "prepare", concurrent)
    assist.client.app.state.settings.assist_timeout_seconds = 5
    key = uuid4().hex
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda _: post(assist, key=key), range(3)))
    assert [r.status_code for r in responses] == [200, 200, 200]
    assert responses[0].json() == responses[1].json() == responses[2].json()
    assert len(calls) == 3
    assert post(assist, key=key).json() == responses[0].json()
    assert len(calls) == 3
    print({"concurrent_mock_provider_calls": len(calls), "completed_replay_extra_calls": 0})
    body = deepcopy(assist.body)
    body["original"] = "different intent"
    assert post(assist, body, key).status_code == 409
    with assist.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT original, proposed, policy_version, status "
                "FROM assist_requests WHERE user_id=:u AND request_key=:k"
            ),
            {"u": assist.user, "k": key},
        ).all()
    assert len(rows) == 1
    assert tuple(rows[0]) == (
        "",
        responses[0].json()["proposed"],
        assist.assist_version,
        "COMPLETED",
    )


def test_existing_generation_snapshots_unchanged(assist):
    body = admission_tests.request_body(assist)
    assert admission_tests.submit(assist, body).status_code == 201
    before = admission_tests.counts(assist)

    def snapshot():
        with assist.engine.connect() as conn:
            return tuple(
                conn.execute(
                    text("SELECT input_snapshot, quote FROM task_snapshots WHERE user_id=:u"),
                    {"u": assist.user},
                ).one()
            )

    saved = snapshot()
    assert post(assist).status_code == 200
    assert snapshot() == saved
    assert admission_tests.counts(assist) == before
    print({"existing_task_before": before, "existing_task_after": admission_tests.counts(assist)})


@pytest.mark.parametrize("case", ["version", "foreign", "deleted_during_provider"])
def test_actual_material_authorization(assist, monkeypatch, case):
    from test_capacity import upload

    from app.assist.provider import MockPromptAssistProvider

    c = assist
    cookies = dict(c.client.cookies)
    if case == "foreign":
        r = c.client.post(
            "/api/v1/auth/register",
            json={
                "account": "foreign_" + uuid4().hex,
                "password": "TEST_ONLY_password",
                "request_key": uuid4().hex,
            },
        )
        assert r.status_code == 201
        c.client.headers["X-CSRF-Token"] = c.client.cookies["csrf_token"]
    r = upload(c.client)
    assert r.status_code == 201, r.text
    c.body["material_versions"] = [r.json()]
    if case == "foreign":
        c.client.cookies.clear()
        c.client.cookies.update(cookies)
        c.client.headers["X-CSRF-Token"] = cookies["csrf_token"]
    elif case == "version":
        assert post(c).status_code == 200
        c.body["material_versions"][0]["version"] = str(uuid4())
    else:
        original = MockPromptAssistProvider.prepare

        async def remove(self, request):
            with c.engine.begin() as conn:
                conn.execute(
                    text("UPDATE files SET deleted_at=UTC_TIMESTAMP(6) WHERE id=:f"),
                    {"f": r.json()["file_id"]},
                )
            return await original(self, request)

        monkeypatch.setattr(MockPromptAssistProvider, "prepare", remove)
    assert post(c).status_code == 404


def test_completed_retry_skips_provider_and_rate_budget(assist, monkeypatch):
    from app.assist.provider import MockPromptAssistProvider

    key = uuid4().hex
    assist.client.app.state.settings.assist_rate_limit = 1
    first = post(assist, key=key)
    assert first.status_code == 200

    async def forbidden(self, request):
        raise AssertionError("Completed receipt must precede provider invocation")

    monkeypatch.setattr(MockPromptAssistProvider, "prepare", forbidden)
    assert post(assist, key=key).json() == first.json()
    assert post(assist).status_code == 429


@pytest.mark.parametrize("kind,focus", [("image", "构图"), ("video", "镜头")])
def test_draft_uses_selected_agent_capability(assist, monkeypatch, kind, focus):
    # Publish another real Agent instead of mutating the provider's kind in memory.
    from test_catalog_quotes import CatalogFixture

    c = CatalogFixture(assist.client, assist.engine, assist.user)
    original_post = c.client.post

    def publish_kind(url, **kwargs):
        if url == "/api/v1/admin/agents":
            kwargs["json"]["kind"] = kind
        return original_post(url, **kwargs)

    monkeypatch.setattr(c.client, "post", publish_kind)
    c.publish()
    body = deepcopy(assist.body)
    body.update(agent_id=c.agent_id, spec_id=c.spec_id)
    response = post(assist, body)
    assert response.status_code == 200, response.text
    assert focus in response.json()["proposed"]
    assert "脚本产品" not in response.json()["proposed"]


def test_public_assist_path_and_request_key_contract(assist):
    schema = assist.client.get("/openapi.json").json()
    assert "/api/v1/assist/prompts" in schema["paths"]
    assert "/api/v1/prompt-assist" not in schema["paths"]
    operation = schema["paths"]["/api/v1/assist/prompts"]["post"]
    header = next(p for p in operation["parameters"] if p["name"] == "Idempotency-Key")
    assert header["in"] == "header" and header["required"] is True
    assert "request_key" in header["description"]
    assert "request_key" not in schema["components"]["schemas"]["AssistRequest"]["properties"]
    assert post(assist).status_code == 200
