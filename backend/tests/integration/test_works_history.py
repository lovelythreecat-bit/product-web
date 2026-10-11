"""T16: actual MySQL publication and cookie-authenticated API reads."""

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select

from app.auth.models import AuthSession, User
from app.auth.security import digest
from app.catalog.models import AgentRecord
from app.dispatch.outbox import enqueue_outbox
from app.ledger.models import CreditAccount, CreditLedger
from app.ledger.service import freeze_credits, grant_credits, now
from app.tasks.models import GenerationTask, TaskSnapshot
from app.works.models import Work
from tests.faults.test_result_persistence import ready as ready_fixture
from tests.integration.test_settlement import publisher
from tests.t12_fixtures import upstream as base_upstream_fixture

ready = ready_fixture
base_upstream = base_upstream_fixture


@pytest.fixture
def upstream(base_upstream, works_task):
    """Reuse T12 HTTP simulator with repeatable owners, without forging published records."""
    factory, service, _, server, worker = base_upstream
    owners = {}

    def create(scenario="normal", kind="copy", agent_identity=None):
        owner = create.owner
        with factory() as s, s.begin():
            if owner not in owners:
                user_id = str(uuid4())
                owners[owner] = user_id
                s.add(
                    User(
                        id=user_id,
                        account_normalized="t16_" + uuid4().hex,
                        password_hash="TEST_ONLY_unusable",
                        created_at=now(),
                    )
                )
                s.flush()
                s.add(CreditAccount(user_id=user_id))
                s.flush()
                grant_credits(
                    s, user_id, "signup", "signup:" + user_id, 1000, "TEST_ONLY T16", None
                )
            user_id = owners[owner]
            task_id = str(uuid4())

            def stamp(mapper, connection, target):
                target.agent_snapshot = dict(
                    agent_id=target.agent_snapshot["agent_id"],
                    version="TEST_ONLY_v1",
                    kind=kind,
                    name="TEST_ONLY Agent",
                    mode="mock",
                    test_only=True,
                    enabled=True,
                    protocol_version="mock-v1-TEST_ONLY",
                    input_support=dict(
                        product_required_fields=[],
                        instruction_required=False,
                        min_materials=0,
                        max_materials=2,
                    ),
                    policy_versions={},
                    secret_configured=False,
                )
                from app.catalog.schemas import content_digest

                target.input_snapshot = dict(
                    target.input_snapshot, material_versions=create.materials
                )
                target.quote = dict(
                    target.quote, input_digest=content_digest(target.input_snapshot)
                )

            event.listen(TaskSnapshot, "before_insert", stamp)
            try:
                task = works_task(s, user_id, task_id)
            finally:
                event.remove(TaskSnapshot, "before_insert", stamp)
            from app.storage.models import FileRef

            for ref in create.materials:
                s.add(
                    FileRef(
                        id=str(uuid4()),
                        file_id=ref["file_id"],
                        version=ref["version"],
                        user_id=user_id,
                        ref_type="task_input",
                        ref_id=task_id,
                        created_at=now(),
                    )
                )
            freeze_credits(s, user_id, task_id, 30)
            s.add(
                AgentRecord(
                    agent_id=task.agent_id,
                    version=task.agent_version,
                    snapshot=s.get(TaskSnapshot, task_id).agent_snapshot,
                    endpoint=f"http://127.0.0.1:{server.server_port}",
                )
            )
            enqueue_outbox(s, task_id, "submit")
            external = task.external_submission_id
        with server.simulator.lock:
            server.simulator.configure(kind, external, {"scenario": scenario})
        return task_id

    create.materials = []
    create.owner = "a"
    create.owners = owners
    return factory, service, create, server, worker


def token_for(factory, user_id):
    token, csrf, session_id = uuid4().hex, uuid4().hex, str(uuid4())
    with factory() as s, s.begin():
        user = s.get(User, user_id)
        s.add(
            AuthSession(
                id=session_id,
                user_id=user_id,
                token_hash=digest(token),
                csrf_hash=digest(csrf),
                auth_version=user.auth_version,
                expires_at=now() + timedelta(hours=1),
            )
        )
    return token, csrf, session_id


@pytest.fixture
def published(upstream, ready, mysql_settings, tmp_path, redis_namespace):
    from app.main import create_app

    app = create_app(
        mysql_settings.model_copy(
            update={
                "storage_root": tmp_path,
                "auth_origins": ["https://testserver"],
            }
        )
    )
    app.state.auth_redis, app.state.auth_rate_prefix = redis_namespace
    with TestClient(app, base_url="https://testserver") as client:

        def create(kind="copy", owner="a", count=1, publish=True):
            upstream[2].owner = owner
            task_id = ready(kind=kind, count=count)
            if publish:
                assert publisher(upstream, tmp_path).run(task_id).state == "SUCCEEDED"
            with upstream[0]() as s:
                task = s.get(GenerationTask, task_id)
                work = s.scalar(select(Work).where(Work.task_id == task_id))
                return {
                    "task_id": task_id,
                    "user_id": task.user_id,
                    "conversation_id": task.conversation_id,
                    "work_id": work.id if work else None,
                }

        def login(user_id):
            token, csrf, session_id = token_for(upstream[0], user_id)
            client.cookies.set("session", token)
            client.cookies.set("csrf_token", csrf)
            client.headers.update(
                {
                    "X-CSRF-Token": csrf,
                    "Origin": "https://testserver",
                    "X-Requested-With": "platform",
                }
            )
            return session_id

        yield client, create, login


@pytest.mark.parametrize(
    "kind,mime", [("copy", "text/plain"), ("image", "image/png"), ("video", "video/mp4")]
)
def test_copy_preview_play_download_filter(published, upstream, kind, mime):
    client, create, login = published
    original = create(kind, count=2)
    login(original["user_id"])
    response = client.get("/api/v1/works", params={"kind": kind})
    assert response.status_code == 200, response.text
    assert [w["work_id"] for w in response.json()["items"]] == [original["work_id"]]
    detail = client.get("/api/v1/works/" + original["work_id"]).json()
    assert detail["kind"] == kind and detail["created_at"].endswith("Z")
    assert detail["task_id"] == original["task_id"]
    assert detail["conversation_id"] == original["conversation_id"]
    assert len(detail["items"]) == 2
    for item in detail["items"]:
        assert item["media_type"] == mime
        result = client.get(item["content_url"])
        assert result.status_code == 200
        assert len(result.content) == item["actual_bytes"]
        assert (
            client.get(item["content_url"], headers={"Range": "bytes=0-3"}).content
            == result.content[:4]
        )
        if kind == "copy":
            assert item["text"] == result.content.decode("utf-8")
        else:
            assert item["text"] is None
    for other in {"copy", "image", "video"} - {kind}:
        assert client.get("/api/v1/works", params={"kind": other}).json()["items"] == []
    assert "internal_path" not in response.text and "endpoint" not in str(detail)
    with upstream[0]() as s:
        snapshot = s.get(TaskSnapshot, original["task_id"])
        assert detail["source"]["input"] == snapshot.input_snapshot
        assert detail["source"]["task"]["quote"] == snapshot.quote
        assert detail["source"]["policy_versions"] == snapshot.policy_versions
        ledger = s.scalars(
            select(CreditLedger).where(CreditLedger.task_id == original["task_id"])
        ).all()
        assert set(detail["source"]["ledger_ids"]) == {r.id for r in ledger}
        print(
            "T16_PUBLISHED",
            original,
            detail["message_id"],
            [i["file_id"] for i in detail["items"]],
            [(r.id, r.kind, r.amount, r.balances_before, r.balances_after) for r in ledger],
        )


def test_stable_pagination_and_unpublished_exclusion(published, upstream):
    client, create, login = published
    rows = [create() for _ in range(3)]
    pending = create(publish=False)
    login(rows[0]["user_id"])
    first = client.get("/api/v1/works?limit=1").json()
    assert "items" in first, first
    inserted = create()
    found, page = [], first
    while True:
        found.extend(w["work_id"] for w in page["items"])
        if not page["next_cursor"]:
            break
        page = client.get(
            "/api/v1/works", params={"limit": 1, "cursor": page["next_cursor"]}
        ).json()
    assert len(found) == len(set(found)) == 3
    assert set(found) == {r["work_id"] for r in rows}
    assert inserted["work_id"] not in found and pending["work_id"] is None
    # Equal database timestamps still have a total, deterministic UUID order.
    with upstream[0]() as s, s.begin():
        same = now()
        for row in s.scalars(select(Work).where(Work.user_id == rows[0]["user_id"])):
            row.created_at = same
    page = client.get("/api/v1/works?limit=100").json()
    assert [w["work_id"] for w in page["items"]] == sorted(
        [r["work_id"] for r in rows] + [inserted["work_id"]], reverse=True
    )


def test_history_matches_task_ledger_regeneration(published, upstream):
    client, create, login = published
    original = create()
    login(original["user_id"])
    response = client.get("/api/v1/works/" + original["work_id"])
    assert response.status_code == 200, response.text
    detail = response.json()
    history = client.get("/api/v1/conversations/" + original["conversation_id"]).json()
    task = client.get("/api/v1/tasks/" + original["task_id"]).json()
    assert detail["source"]["task"] == task["task"] == history["tasks"]["items"][0]
    assert detail["message_id"] == history["messages"]["items"][0]["message_id"]
    assert detail["source"]["task"]["settlement_state"] == "CONSUMED"
    assert detail["source"]["materials"] == []
    assert detail["source"]["requires_new_quote"] is True
    with upstream[0]() as s:
        assert s.get(CreditAccount, original["user_id"]).frozen == 0


@pytest.fixture
def works_task():
    """Real relational task fixture for T04's isolated ledger transaction tests.

    It does not call admission, because these tests exercise the freeze itself.
    Every required task/product/conversation/capacity row is in the caller transaction.
    """

    def create(session, user_id, task_id, amount=30):
        from app.catalog.schemas import content_digest
        from app.conversations.models import Conversation, Product, ProductVersion
        from app.ledger.service import locked_account, now
        from app.policies.schemas import DecisionVersion
        from app.policies.service import PolicyService
        from app.storage.capacity import reserve_capacity
        from app.tasks.models import GenerationTask, TaskSnapshot

        user_id, task_id = str(user_id), str(task_id)
        locked_account(session, user_id)
        policy = "TEST_ONLY_" + uuid4().hex
        PolicyService(session).add_draft(
            DecisionVersion(
                decision_id="D-10",
                version=policy,
                mode="mock",
                test_only=True,
                payload={
                    "generation": {
                        "account_quota_bytes": 20000,
                        "server_budget_bytes": 100000000,
                        "reservation_seconds": 120,
                        "reclamation_ref": "TEST_ONLY_fixture",
                        "alert_ref": "TEST_ONLY_fixture",
                    }
                },
            )
        )
        capacity = reserve_capacity(
            session, user_id, "generation:" + task_id, 1, policy, mode="mock"
        )
        conversation = Conversation(
            id=str(uuid4()), user_id=user_id, title="TEST_ONLY ledger", created_at=now()
        )
        product = Product(id=str(uuid4()), user_id=user_id)
        session.add_all([conversation, product])
        session.flush()
        product_version = ProductVersion(
            version=str(uuid4()),
            user_id=user_id,
            product_id=product.id,
            product={"name": "TEST_ONLY cup"},
            created_at=now(),
        )
        session.add(product_version)
        session.flush()
        agent_id, spec_id = str(uuid4()), str(uuid4())
        input = {
            "product_version": product_version.version,
            "product": product_version.product,
            "instruction": "TEST_ONLY ledger fixture",
            "parameters": {},
            "material_versions": [],
        }
        quote = {
            "spec_id": spec_id,
            "spec_version": "TEST_ONLY_v1",
            "price_version": "TEST_ONLY_v1",
            "agent_version": "TEST_ONLY_v1",
            "policy_versions": {},
            "credits": amount,
            "input_digest": content_digest(input),
        }
        task = GenerationTask(
            id=task_id,
            user_id=user_id,
            conversation_id=conversation.id,
            idempotency_key=uuid4().hex,
            request_hash=content_digest(input),
            agent_id=agent_id,
            agent_version="TEST_ONLY_v1",
            external_submission_id=str(uuid4()),
            state="SUBMITTED",
            state_version=1,
            settlement_state="FROZEN",
            capacity_reservation_id=capacity.id,
            fencing_token=0,
            created_at=now(),
        )
        session.add(task)
        session.flush()
        session.add(
            TaskSnapshot(
                task_id=task_id,
                user_id=user_id,
                product_version=product_version.version,
                input_snapshot=input,
                quote=quote,
                agent_snapshot={"agent_id": agent_id, "version": "TEST_ONLY_v1"},
                spec_snapshot={"spec_id": spec_id, "version": "TEST_ONLY_v1"},
                price_snapshot={"spec_id": spec_id, "version": "TEST_ONLY_v1", "credits": amount},
                policy_versions={"D-10": policy},
                capacity_estimate={"total_bytes": 1, "estimation_ref": "TEST_ONLY_fixture"},
            )
        )
        session.flush()
        return task

    return create


def test_account_and_ledger_are_current_owner_only(published, upstream):
    client, create, login = published
    original, other = create(), create(owner="b")
    login(original["user_id"])
    response = client.get("/api/v1/account")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "available": 970,
        "frozen": 0,
        "consumed": 30,
        "credited_total": 1000,
    }
    source = client.get("/api/v1/works/" + original["work_id"]).json()["source"]
    rows, cursor = [], None
    while True:
        page = client.get(
            "/api/v1/account/ledger", params={"limit": 1, **({"cursor": cursor} if cursor else {})}
        )
        assert page.status_code == 200, page.text
        rows.extend(page.json()["items"])
        cursor = page.json()["next_cursor"]
        if cursor is None:
            break
    assert [r["kind"] for r in rows] == ["consume", "freeze", "signup"]
    assert all(r["created_at"].endswith("Z") for r in rows)
    assert {r["ledger_id"] for r in rows if r["task_id"]} == set(source["ledger_ids"])
    assert all(r["reservation_id"] == source["credit_reservation_id"] for r in rows if r["task_id"])
    assert rows[0]["balances_before"] == {"available": 970, "frozen": 30, "consumed": 0}
    assert rows[0]["balances_after"] == {"available": 970, "frozen": 0, "consumed": 30}
    login(other["user_id"])
    for cursor in (rows[0]["ledger_id"], str(uuid4())):
        assert client.get("/api/v1/account/ledger", params={"cursor": cursor}).status_code == 404
    assert all(
        r["task_id"] != original["task_id"]
        for r in client.get("/api/v1/account/ledger").json()["items"]
    )
    with upstream[0]() as s, s.begin():
        s.get(User, other["user_id"]).status = "disabled"
    assert client.get("/api/v1/account").status_code == 401
    assert client.get("/api/v1/account/ledger").status_code == 401


def current_catalog_for_source(client, engine, user_id, source):
    """Publish a new catalog version using real admin APIs, leaving old snapshots intact."""
    from copy import deepcopy

    from app.policies.models import DecisionVersionRecord
    from app.policies.schemas import DecisionVersion
    from app.policies.service import PolicyService
    from tests.integration.test_catalog_quotes import CatalogFixture
    from tests.integration.test_task_admission import admission

    class SourceCatalog(CatalogFixture):
        def set_policies(self, credits=7, delivery="single", d04=False):
            super().set_policies(credits, delivery, d04)
            with upstream_session(self.engine) as s, s.begin():
                payload = deepcopy(
                    s.get(DecisionVersionRecord, ("D-02", self.policies["D-02"])).payload
                )
                payload["specs"][self.spec_id]["agent_version"] = "TEST_ONLY_v2"
                version = "TEST_ONLY_" + uuid4().hex
                PolicyService(s).add_draft(
                    DecisionVersion(
                        decision_id="D-02",
                        version=version,
                        mode="mock",
                        test_only=True,
                        payload=payload,
                    )
                )
                self.policies["D-02"] = version

        def agent(self, enabled=True, version="TEST_ONLY_v2", expected=None):
            return super().agent(enabled, version, expected)

        def spec(self):
            return self.client.post(
                "/api/v1/admin/specs",
                json={
                    "spec_id": self.spec_id,
                    "version": "TEST_ONLY_v1",
                    "expected_version": None,
                    "agent_id": self.agent_id,
                    "agent_version": "TEST_ONLY_v2",
                    "name": "TEST_ONLY",
                    "parameter_schema": self.parameter_schema,
                    "delivery_kind": "single",
                    "enabled": True,
                    "policy_versions": self.policies,
                    "reason": "TEST_ONLY new source quote",
                },
            )

    from sqlalchemy.orm import Session as upstream_session

    with upstream_session(engine) as s, s.begin():
        s.get(User, user_id).role = "admin"
    c = SourceCatalog(client, engine, user_id)
    c.agent_id, c.spec_id = source["agent_id"], source["task"]["quote"]["spec_id"]
    c.parameter_schema = {"fields": {}, "combinations": []}
    c.input = deepcopy(source["input"])
    c = admission.__wrapped__(c)
    settings = client.app.state.settings
    with upstream_session(engine) as s, s.begin():
        payload = deepcopy(
            s.get(
                DecisionVersionRecord, ("D-10", settings.generation_policy_versions["D-10"])
            ).payload
        )
        payload["generation"]["account_quota_bytes"] = 20000
        payload["upload"]["account_quota_bytes"] = 20000
        payload["upload"]["max_file_bytes"] = 10000
        version = "TEST_ONLY_" + uuid4().hex
        PolicyService(s).add_draft(
            DecisionVersion(
                decision_id="D-10", version=version, mode="mock", test_only=True, payload=payload
            )
        )
        s.get(User, user_id).role = "user"
    settings.generation_policy_versions["D-10"] = version
    settings.generation_capacity_estimates[c.spec_id]["policy_version"] = version
    settings.storage_policy_version = version
    return c


def test_regenerate_missing_material_requires_reupload_and_new_quote(published, upstream):
    from copy import deepcopy

    from app.storage.models import File
    from tests.integration.test_task_admission import submit

    client, create, login = published
    material_work = create("image")
    login(material_work["user_id"])
    material = client.get("/api/v1/works/" + material_work["work_id"]).json()["items"][0]
    material_bytes = client.get(material["content_url"]).content
    upstream[2].materials = [{"file_id": material["file_id"], "version": material["file_version"]}]
    original = create()
    original_detail = client.get("/api/v1/works/" + original["work_id"])
    assert original_detail.status_code == 200, original_detail.text
    source = original_detail.json()["source"]
    assert source["materials"] == [
        {"file": upstream[2].materials[0], "available": True, "action": None}
    ]
    c = current_catalog_for_source(client, upstream[0].kw["bind"], original["user_id"], source)
    conversation = client.post(
        "/api/v1/conversations", json={"title": "TEST_ONLY regenerate"}
    ).json()
    body = {
        "conversation_id": conversation["conversation_id"],
        "agent_id": source["agent_id"],
        "input": source["input"],
        "confirmed_quote": source["task"]["quote"],
    }
    before = client.get("/api/v1/account").json()
    assert submit(c, body).status_code == 409
    quote = c.quote()
    assert quote.status_code == 200, quote.text
    assert quote.json()["credits"] == 7 and quote.json()["agent_version"] == "TEST_ONLY_v2"
    body["confirmed_quote"] = quote.json()
    # Simulate an unavailable source asset, without applying an unconfirmed deletion policy.
    with upstream[0]() as s, s.begin():
        s.get(File, material["file_id"]).state = "unavailable"
    missing = client.get("/api/v1/works/" + original["work_id"]).json()
    assert missing["source"]["materials"] == [
        {"file": upstream[2].materials[0], "available": False, "action": "upload_again"}
    ]
    assert missing["source"]["input"] == source["input"]
    rejected = submit(c, body)
    assert rejected.status_code == 404, rejected.text
    assert client.get("/api/v1/account").json() == before
    replacement = client.post(
        "/api/v1/files",
        params={"display_name": "TEST_ONLY reupload.png"},
        content=material_bytes,
        headers={"Content-Type": "image/png"},
    )
    assert replacement.status_code == 201, replacement.text
    replacement_file = replacement.json()
    body = deepcopy(body)
    body["input"]["material_versions"] = [replacement_file]
    stale = submit(c, body)
    assert stale.status_code == 409, stale.text
    c.input = body["input"]
    body["confirmed_quote"] = c.quote().json()
    before_new = client.get("/api/v1/account").json()
    key = uuid4().hex
    admitted = submit(c, body, key)
    assert admitted.status_code == 201, admitted.text
    new = admitted.json()["task"]
    assert new["task_id"] != original["task_id"] and new["quote"]["credits"] == 7
    assert submit(c, body, key).status_code == 200
    after = client.get("/api/v1/account").json()
    assert after["frozen"] == before_new["frozen"] + 7
    assert after["available"] == before_new["available"] - 7
    old = client.get("/api/v1/works/" + original["work_id"]).json()
    assert old == missing
    ledger = client.get("/api/v1/account/ledger").json()["items"]
    assert len([r for r in ledger if r["task_id"] == new["task_id"] and r["kind"] == "freeze"]) == 1
    assert set(source["ledger_ids"]) <= {r["ledger_id"] for r in ledger}
    print(
        "T16_REGENERATION",
        {
            "original_task": original["task_id"],
            "work": original["work_id"],
            "original_ledger": source["ledger_ids"],
            "new_task": new["task_id"],
            "new_key": key,
            "original_quote": source["task"]["quote"],
            "new_quote": new["quote"],
            "balances_before": before_new,
            "balances_after": after,
        },
    )


def test_history_exposes_persisted_disposition_reason(published, upstream):
    client, create, login = published
    original = create()
    login(original["user_id"])
    reason = "TEST_ONLY original result recovered after investigation"
    with upstream[0]() as s, s.begin():
        s.get(GenerationTask, original["task_id"]).investigation_reason = reason
    work = client.get("/api/v1/works/" + original["work_id"]).json()
    history = client.get("/api/v1/conversations/" + original["conversation_id"]).json()
    task = client.get("/api/v1/tasks/" + original["task_id"]).json()
    assert work["source"]["task"]["investigation_reason"] == reason
    assert task["task"]["investigation_reason"] == reason
    assert history["tasks"]["items"][0]["investigation_reason"] == reason
