from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.auth.models import AuthSession, User
from app.auth.security import digest
from app.ledger.models import CreditAccount, CreditLedger
from app.ledger.service import now
from app.policies.schemas import DecisionVersion
from app.policies.service import PolicyService
from app.tasks.models import GenerationTask
from tests.faults.test_result_persistence import ready as ready_fixture
from tests.faults.test_upstream_recovery import calls, submit
from tests.t12_fixtures import upstream as upstream_fixture

upstream = upstream_fixture
ready = ready_fixture


@pytest.fixture
def desk(upstream, auth_client, tmp_path):
    root = tmp_path / "t13-originals"
    root.mkdir()
    auth_client.app.state.settings = auth_client.app.state.settings.model_copy(
        update={"storage_root": root}
    )
    factory = upstream[0]
    uid, sid, token, csrf = [str(uuid4()) for _ in range(4)]
    policy = "TEST_ONLY_" + uuid4().hex
    with factory() as s, s.begin():
        s.add(
            User(
                id=uid,
                account_normalized="t13_" + uuid4().hex,
                password_hash="TEST_ONLY",
                role="admin",
                created_at=now(),
            )
        )
        s.flush()
        s.add(
            AuthSession(
                id=sid,
                user_id=uid,
                token_hash=digest(token),
                csrf_hash=digest(csrf),
                auth_version=0,
                expires_at=now() + timedelta(hours=1),
            )
        )
        PolicyService(s).add_draft(
            DecisionVersion(
                decision_id="D-08",
                version=policy,
                mode="mock",
                test_only=True,
                payload={
                    "investigations": {
                        "schema_version": "investigations-v1",
                        "deadline_seconds": 60,
                        "responsible_user_id": uid,
                        "escalation_ref": "TEST_ONLY:operations",
                        "authorized_actor_ids": [uid],
                        "actions": ["resume_original", "confirm_failure", "manual_close", "settle"],
                        "manual_release_basis": "operator_review",
                        "capacity_on_close": "retain_all",
                        "late_delivery": "quarantine",
                        "evidence_types": ["review", "upstream_failure", "durable_delivery"],
                        "deadline_is_failure": False,
                        "requires_complete_delivery": True,
                    }
                },
            )
        )
    auth_client.cookies.set("session", token)
    auth_client.cookies.set("csrf_token", csrf)
    auth_client.headers["X-CSRF-Token"] = csrf
    return auth_client, uid, sid, policy


def open_case(runtime, desk, scenario="lost_response"):
    task = runtime[2](scenario)
    submit(runtime, task)
    client, uid, _, policy = desk
    response = client.post(
        "/api/v1/admin/tasks/" + task + "/investigations",
        json={"owner": uid, "policy_version": policy, "evidence": "TEST_ONLY:review"},
    )
    assert response.status_code == 201, response.text
    return task, response.json()


def resolve(desk, task, case, action, **overrides):
    data = dict(
        action=action,
        reason="核查后按测试政策处置",
        expected_version=case["version"],
        policy_version=desk[3],
        evidence={"kind": "review", "reference": "TEST_ONLY:review"},
    )
    data.update(overrides)
    return desk[0].post("/api/v1/admin/tasks/" + task + "/resolutions", json=data)


def owner_session(runtime, desk, task):
    token = str(uuid4())
    with runtime[0]() as s, s.begin():
        row = s.get(GenerationTask, task)
        conversation_id = row.conversation_id
        s.add(
            AuthSession(
                id=str(uuid4()),
                user_id=row.user_id,
                token_hash=digest(token),
                csrf_hash=digest(str(uuid4())),
                auth_version=0,
                expires_at=now() + timedelta(hours=1),
            )
        )
    desk[0].cookies.set("session", token)
    return conversation_id


def assert_task_consumers(client, task, conversation_id, reason):
    detail = client.get("/api/v1/tasks/" + task)
    listing = client.get("/api/v1/tasks", params={"conversation_id": conversation_id})
    conversation = client.get("/api/v1/conversations/" + conversation_id)
    for response in (detail, listing, conversation):
        assert response.status_code == 200, response.text
    views = [
        detail.json()["task"],
        *listing.json()["items"],
        *conversation.json()["tasks"]["items"],
    ]
    assert len(views) == 3
    assert all(view["task_id"] == task and view["investigation_reason"] == reason for view in views)
    assert all("evidence" not in view for view in views)


def test_planned_admin_write_routes(upstream, desk):
    task = upstream[2]("lost_response")
    submit(upstream, task)
    response = desk[0].post(
        f"/api/v1/admin/tasks/{task}/investigations",
        json={"owner": desk[1], "policy_version": desk[3], "evidence": "TEST_ONLY:review"},
    )
    assert response.status_code == 201, response.text
    response = desk[0].post(
        f"/api/v1/admin/tasks/{task}/resolutions",
        json={
            "action": "manual_close",
            "reason": "TEST_ONLY planned route",
            "expected_version": response.json()["version"],
            "policy_version": desk[3],
            "evidence": {"kind": "review", "reference": "TEST_ONLY:review"},
        },
    )
    assert response.status_code == 200, response.text
    paths = desk[0].app.openapi()["paths"]
    assert "post" in paths["/api/v1/admin/tasks/{id}/investigations"]
    assert "post" in paths["/api/v1/admin/tasks/{id}/resolutions"]


@pytest.mark.parametrize("view", ["admin", "owner", "alert"])
def test_response_dates_identify_database_utc(upstream, desk, view):
    from app.investigations.models import Investigation, InvestigationAlert
    from app.investigations.service import InvestigationService

    task, _ = open_case(upstream, desk)
    if view == "alert":
        with upstream[0]() as s, s.begin():
            InvestigationService.alert(s, s.get(GenerationTask, task), "OVERDUE", "TEST_ONLY:ops")
        response = desk[0].get("/api/v1/admin/investigation-alerts", params={"limit": 100})
        assert response.status_code == 200, response.text
        payload = next(item for item in response.json()["items"] if item["task_id"] == task)
        field = "created_at"
        with upstream[0]() as s:
            expected = s.get(InvestigationAlert, payload["key"]).created_at
    else:
        if view == "owner":
            owner_session(upstream, desk, task)
        path = (
            "/api/v1/tasks/" + task + "/investigation"
            if view == "owner"
            else "/api/v1/admin/investigations/" + task
        )
        response = desk[0].get(path)
        assert response.status_code == 200, response.text
        payload, field = response.json(), "deadline_at"
        with upstream[0]() as s:
            expected = s.get(Investigation, task).deadline_at
    actual = datetime.fromisoformat(payload[field])
    assert actual.utcoffset() == timedelta(0), payload[field]
    assert actual == expected.replace(tzinfo=UTC)


def test_deadline_requires_owner_not_auto_failure(upstream, desk):
    task, case = open_case(upstream, desk)
    from app.investigations.service import InvestigationService

    with upstream[0]() as s, s.begin():
        s.execute(
            text(
                "UPDATE investigations SET deadline_at=UTC_TIMESTAMP(6)-INTERVAL 1 SECOND "
                "WHERE task_id=:id"
            ),
            {"id": task},
        )
    InvestigationService(upstream[0], upstream=upstream[1]).scan([task])
    result = desk[0].get("/api/v1/admin/investigations/" + task).json()
    assert result["status"] == "overdue" and result["owner"] == desk[1]
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        assert row.state == "INVESTIGATING" and row.settlement_state == "FROZEN"
        assert s.get(CreditAccount, row.user_id).frozen == 30


def test_investigation_sweep_defers_locked_user_and_retries_next_scan(upstream, desk):
    from app.investigations.models import Investigation
    from app.investigations.service import InvestigationService

    task, _ = open_case(upstream, desk)
    factory = upstream[0]
    with factory() as session, session.begin():
        session.execute(
            text("UPDATE investigations SET deadline_at=UTC_TIMESTAMP(6)-INTERVAL 1 SECOND "
                 "WHERE task_id=:id"), {"id": task},
        )
        owner = session.get(GenerationTask, task).user_id
    sweep = InvestigationService(factory, upstream=upstream[1])
    with factory() as blocker, blocker.begin():
        blocker.scalar(select(User).where(User.id == owner).with_for_update())
        # Maintenance must yield busy accounts instead of starving task consumption.
        sweep.scan([task])
        with factory() as check:
            assert check.get(Investigation, task).status == "open"
    sweep.scan([task])
    with factory() as check:
        assert check.get(Investigation, task).status == "overdue"
        assert check.get(GenerationTask, task).settlement_state == "FROZEN"


def test_no_delivery_no_manual_settle(upstream, desk):
    task, case = open_case(upstream, desk)
    assert resolve(desk, task, case, "settle").status_code == 409
    with upstream[0]() as s:
        assert s.get(GenerationTask, task).settlement_state == "FROZEN"


def test_missing_policy_blocks_resolution(upstream, desk):
    task, case = open_case(upstream, desk)
    assert resolve(desk, task, case, "manual_close", policy_version="absent").status_code == 403
    with upstream[0]() as s:
        assert s.get(GenerationTask, task).settlement_state == "FROZEN"


def test_late_success_after_release(upstream, desk):
    task, case = open_case(upstream, desk)
    response = resolve(desk, task, case, "manual_close")
    assert response.status_code == 200, response.text
    from app.investigations.service import InvestigationService
    from tests.integration.test_callbacks import event_for

    path, wire = event_for(upstream, task)
    # A trusted source records terminal late through its normal authenticated ingress.
    from tests.integration.test_callbacks import post

    response = post(desk[0], path, wire)
    assert response.status_code == 202, response.text
    InvestigationService(upstream[0], upstream=upstream[1]).scan([task])
    from app.investigations.models import InvestigationAlert

    with upstream[0]() as s:
        alert = s.scalar(
            select(InvestigationAlert).where(
                InvestigationAlert.task_id == task, InvestigationAlert.kind == "LATE_RESULT"
            )
        )
        assert alert and alert.disposition == "quarantine" and alert.evidence_ref
        row = s.get(GenerationTask, task)
        assert row.state == "MANUALLY_CLOSED" and row.settlement_state == "RELEASED"
        ledger = s.scalars(
            select(CreditLedger).where(
                CreditLedger.task_id == task, CreditLedger.kind.in_(["consume", "release"])
            )
        ).all()
        assert len(ledger) == 1 and ledger[0].kind == "release"
        print(
            "T13_FACTS",
            task,
            row.state,
            row.settlement_state,
            ledger[0].id,
            s.get(CreditAccount, row.user_id).available,
            calls(upstream, task),
        )


def existing_case(desk, task):
    response = desk[0].post(
        "/api/v1/admin/tasks/" + task + "/investigations",
        json={"owner": desk[1], "policy_version": desk[3], "evidence": "TEST_ONLY:review"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_manual_settle_uses_complete_original_publication(upstream, desk, ready, monkeypatch):
    from tests.integration.test_settlement import publisher

    task = ready(count=2)
    pub = publisher(upstream, desk[0].app.state.settings.storage_root)
    original_commit = pub.persistence.store.commit

    def fail_commit(staged):
        raise OSError("TEST_ONLY disk failure")

    monkeypatch.setattr(pub.persistence.store, "commit", fail_commit)
    assert pub.run(task) is None
    monkeypatch.setattr(pub.persistence.store, "commit", original_commit)
    case = existing_case(desk, task)
    response = resolve(
        desk,
        task,
        case,
        "settle",
        evidence={"kind": "durable_delivery", "reference": "TEST_ONLY:original"},
    )
    assert response.status_code == 200, response.text
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        assert row.state == "SUCCEEDED" and row.settlement_state == "CONSUMED"
        assert s.get(CreditAccount, row.user_id).consumed == 30
    assert calls(upstream, task)["submit"] == 1


def test_worker_creates_unassigned_alert(upstream, redis_namespace):
    from app.investigations.models import InvestigationAlert
    from worker.main import compose_worker

    task = upstream[2]("lost_response")
    submit(upstream, task)
    redis, prefix = redis_namespace
    worker = compose_worker(
        upstream[0],
        redis,
        prefix + "t13",
        "workers",
        "t13",
        registry=upstream[1].registry,
        task_ids=[task],
    )
    worker.tick()
    with upstream[0]() as s:
        assert s.scalar(
            select(InvestigationAlert).where(
                InvestigationAlert.task_id == task, InvestigationAlert.kind == "UNASSIGNED"
            )
        )


def test_close_keeps_partial_file_capacity(upstream, desk, ready, monkeypatch):
    from app.storage.models import CapacityReservation, File
    from tests.integration.test_settlement import publisher

    task = ready(count=2)
    pub = publisher(upstream, desk[0].app.state.settings.storage_root)
    commit = pub.persistence.store.commit
    count = [0]

    def partial(staged):
        count[0] += 1
        if count[0] == 2:
            raise OSError("TEST_ONLY second item disk failure")
        return commit(staged)

    monkeypatch.setattr(pub.persistence.store, "commit", partial)
    assert pub.run(task) is None
    case = existing_case(desk, task)
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        capacity = s.get(CapacityReservation, row.capacity_reservation_id)
        before = (capacity.state, capacity.estimated_bytes, capacity.actual_bytes)
        files = s.scalars(select(File).where(File.user_id == row.user_id)).all()
        assert files
    response = resolve(desk, task, case, "manual_close")
    assert response.status_code == 200, response.text
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        capacity = s.get(CapacityReservation, row.capacity_reservation_id)
        from app.results.models import ResultManifestRecord, ResultSaveItem
        from app.storage.models import StorageAccount

        expected = sum(
            s.scalars(
                select(ResultSaveItem.actual_bytes)
                .join(ResultManifestRecord, ResultManifestRecord.id == ResultSaveItem.manifest_id)
                .where(ResultManifestRecord.task_id == task)
            ).all()
        )
        assert (capacity.state, capacity.actual_bytes) == (before[0], before[2])
        assert capacity.estimated_bytes >= max(before[1], expected)
        assert s.get(StorageAccount, row.user_id).reserved_bytes >= expected
        print("T13_CAPACITY", task, capacity.id, capacity.state, capacity.estimated_bytes, expected)
        assert s.get(CreditAccount, row.user_id).available == 100


@pytest.mark.parametrize("defect", ["csrf", "role", "revoked", "disabled", "auth_version"])
def test_admin_authority_is_live(upstream, desk, defect):
    task, case = open_case(upstream, desk)
    if defect == "csrf":
        del desk[0].headers["X-CSRF-Token"]
    else:
        with upstream[0]() as s, s.begin():
            if defect == "role":
                s.get(User, desk[1]).role = "user"
            elif defect == "revoked":
                s.get(AuthSession, desk[2]).revoked_at = now()
            elif defect == "disabled":
                s.get(User, desk[1]).status = "disabled"
            else:
                s.get(User, desk[1]).auth_version += 1
    assert resolve(desk, task, case, "manual_close").status_code in (401, 403)
    with upstream[0]() as s:
        assert s.get(GenerationTask, task).settlement_state == "FROZEN"


def test_concurrent_close_cas_is_unique(upstream, desk):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from fastapi import HTTPException

    from app.common.types import Principal
    from app.investigations.models import Resolution
    from app.investigations.schemas import ResolveInvestigation
    from app.investigations.service import InvestigationService

    task, case = open_case(upstream, desk)
    barrier = Barrier(2)
    connections = []
    actor = Principal(user_id=desk[1], session_id=desk[2], role="admin", auth_version=0)
    dto = ResolveInvestigation(
        action="manual_close",
        policy_version=desk[3],
        evidence={"kind": "review", "reference": "TEST_ONLY:review"},
        reason="TEST_ONLY close",
        expected_version=case["version"],
    )

    def contender():
        try:
            with upstream[0]() as s, s.begin():
                connections.append(s.scalar(text("SELECT CONNECTION_ID()")))
                barrier.wait(10)
                InvestigationService(upstream[0], upstream=upstream[1]).resolve_investigation(
                    s, actor, task, dto
                )
            return 200
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(2) as pool:
        a, b = pool.submit(contender), pool.submit(contender)
        assert sorted([a.result(), b.result()]) == [200, 409]
    assert len(set(connections)) == 2
    with upstream[0]() as s:
        assert len(s.scalars(select(Resolution).where(Resolution.task_id == task)).all()) == 1
        assert (
            len(
                s.scalars(
                    select(CreditLedger).where(
                        CreditLedger.task_id == task, CreditLedger.kind == "release"
                    )
                ).all()
            )
            == 1
        )


def test_confirm_failure_consumes_trusted_event(upstream, desk):
    from tests.integration.test_callbacks import changed, event_for, post

    task, case = open_case(upstream, desk)
    path, wire = event_for(upstream, task)
    assert post(desk[0], path, changed(wire, state="FAILED", result=None)).status_code == 202
    upstream[1].poll_original_task(task)
    reference = upstream[1].pending_failure(task)
    assert reference
    assert (
        resolve(
            desk,
            task,
            case,
            "confirm_failure",
            evidence={"kind": "upstream_failure", "reference": reference},
        ).status_code
        == 200
    )
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        assert row.state == "FAILED" and row.settlement_state == "RELEASED"


def test_fake_failure_reference_cannot_release(upstream, desk):
    task, case = open_case(upstream, desk)
    response = resolve(
        desk,
        task,
        case,
        "confirm_failure",
        evidence={"kind": "upstream_failure", "reference": str(uuid4())},
    )
    assert response.status_code == 409
    with upstream[0]() as s:
        assert s.get(GenerationTask, task).settlement_state == "FROZEN"


def test_resume_not_found_keeps_original_identity(upstream, desk, redis_namespace):
    from tests.faults.test_upstream_recovery import facts
    from worker.main import compose_worker

    task, case = open_case(upstream, desk)
    before = facts(upstream[0], task)
    with upstream[3].simulator.lock:
        next(iter(upstream[3].simulator.records.values()))["scenario"] = "not_found"
    assert resolve(desk, task, case, "resume_original").status_code == 200
    redis, prefix = redis_namespace
    worker = compose_worker(
        upstream[0],
        redis,
        prefix + "resume",
        "workers",
        "t13",
        registry=upstream[1].registry,
        task_ids=[task],
    )
    assert worker.tick()[2].failed == 0
    assert facts(upstream[0], task) == before
    assert calls(upstream, task)["submit"] == 1
    with upstream[0]() as s:
        assert s.get(GenerationTask, task).state == "INVESTIGATING"


def test_production_draft_policy_stays_closed(upstream, desk):
    task, case = open_case(upstream, desk)
    desk[0].app.state.settings = desk[0].app.state.settings.model_copy(
        update={"mode": "production", "test_only": False}
    )
    assert resolve(desk, task, case, "manual_close").status_code == 403


def test_owner_reads_reason_without_internal_evidence(upstream, desk):
    task, case = open_case(upstream, desk)
    with upstream[0]() as s:
        original_reason = s.get(GenerationTask, task).investigation_reason
    assert resolve(desk, task, case, "manual_close").status_code == 200
    token, csrf = str(uuid4()), str(uuid4())
    with upstream[0]() as s, s.begin():
        owner = s.get(GenerationTask, task).user_id
        s.add(
            AuthSession(
                id=str(uuid4()),
                user_id=owner,
                token_hash=digest(token),
                csrf_hash=digest(csrf),
                auth_version=0,
                expires_at=now() + timedelta(hours=1),
            )
        )
    desk[0].cookies.set("session", token)
    response = desk[0].get("/api/v1/tasks/" + task + "/investigation")
    assert response.status_code == 200
    assert response.json()["user_reason"] == "核查后按测试政策处置"
    assert set(response.json()) == {"task_id", "status", "deadline_at", "user_reason"}
    assert desk[0].get("/api/v1/admin/investigations/" + task).status_code == 403
    with upstream[0]() as s:
        conversation_id = s.get(GenerationTask, task).conversation_id
    assert_task_consumers(desk[0], task, conversation_id, "核查后按测试政策处置")
    from app.audit.models import AuditEvent

    with upstream[0]() as s:
        audit = s.scalar(
            select(AuditEvent).where(
                AuditEvent.object_id == task, AuditEvent.action == "investigation.manual_close"
            )
        )
        assert audit.changes["previous_investigation_reason"] == original_reason


def test_audit_failure_rolls_back_release(upstream, desk, monkeypatch):
    from sqlalchemy import event

    from app.audit.models import AuditEvent

    task, case = open_case(upstream, desk)

    def fail(mapper, connection, target):
        if target.object_id == task and target.action == "investigation.manual_close":
            raise RuntimeError("TEST_ONLY audit unavailable")

    event.listen(AuditEvent, "before_insert", fail)
    try:
        assert resolve(desk, task, case, "manual_close").status_code == 500
    finally:
        event.remove(AuditEvent, "before_insert", fail)
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        assert row.state == "INVESTIGATING" and row.settlement_state == "FROZEN"
        assert s.get(CreditAccount, row.user_id).frozen == 30


def test_reassignment_and_todo_are_operable(upstream, desk):
    task, case = open_case(upstream, desk)
    listing = desk[0].get("/api/v1/admin/investigations")
    assert listing.status_code == 200, listing.text
    assert task in [v["task_id"] for v in listing.json()["items"]]
    response = desk[0].post(
        "/api/v1/admin/investigations/" + task + "/assign",
        json={
            "owner": desk[1],
            "policy_version": desk[3],
            "evidence": "TEST_ONLY:handoff",
            "expected_version": case["version"],
            "reason": "TEST_ONLY responsibility confirmed",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["version"] == case["version"] + 1
    assert response.json()["deadline_at"] == case["deadline_at"]


def test_worker_recovery_finishes_case_with_publication(
    upstream, desk, ready, monkeypatch, redis_namespace
):
    from app.investigations.models import Investigation
    from app.storage.local_store import LocalStore
    from tests.integration.test_settlement import publisher
    from worker.main import compose_worker

    task = ready()
    root = desk[0].app.state.settings.storage_root
    pub = publisher(upstream, root)
    with monkeypatch.context() as patch:

        def fail_commit(staged):
            raise OSError("TEST_ONLY disk failure")

        patch.setattr(pub.persistence.store, "commit", fail_commit)
        assert pub.run(task) is None
    case = existing_case(desk, task)
    assert resolve(desk, task, case, "resume_original").status_code == 200
    redis, prefix = redis_namespace
    worker = compose_worker(
        upstream[0],
        redis,
        prefix + "save-resume",
        "workers",
        "t13",
        registry=upstream[1].registry,
        task_ids=[task],
        store=LocalStore(root),
    )
    assert worker.tick()[2].failed == 0
    with upstream[0]() as s:
        assert s.get(GenerationTask, task).state == "SUCCEEDED"
        assert s.get(Investigation, task).status == "resolved"
    conversation_id = owner_session(upstream, desk, task)
    assert_task_consumers(desk[0], task, conversation_id, "原任务已完成保存并结算。")


def test_disabled_task_owner_requires_d09(upstream, desk):
    task, case = open_case(upstream, desk)
    with upstream[0]() as s, s.begin():
        s.get(User, s.get(GenerationTask, task).user_id).status = "disabled"
    assert resolve(desk, task, case, "manual_close").status_code == 403
    with upstream[0]() as s:
        assert s.get(GenerationTask, task).settlement_state == "FROZEN"


def test_worker_assigns_exact_snapshot_policy(upstream, desk):
    from sqlalchemy import event

    from app.investigations.models import Investigation
    from app.investigations.service import InvestigationService
    from app.tasks.models import TaskSnapshot

    def stamp(mapper, connection, target):
        target.policy_versions = dict(target.policy_versions, **{"D-08": desk[3]})

    event.listen(TaskSnapshot, "before_insert", stamp)
    try:
        task = upstream[2]("lost_response")
    finally:
        event.remove(TaskSnapshot, "before_insert", stamp)
    submit(upstream, task)
    InvestigationService(upstream[0], upstream=upstream[1]).scan([task])
    with upstream[0]() as s:
        case = s.get(Investigation, task)
        assert case is not None and case.owner == desk[1] and case.policy_version == desk[3]
        assert case.deadline_at and s.get(GenerationTask, task).settlement_state == "FROZEN"


def test_test_only_policy_sample_validates():
    import json
    from pathlib import Path

    from app.policies.schemas import InvestigationPolicy

    source = (
        Path(__file__).resolve().parents[3]
        / "contracts/fixtures/policies/TEST_ONLY-investigations.json"
    )
    record = DecisionVersion.model_validate(json.loads(source.read_text(encoding="utf-8-sig")))
    policy = InvestigationPolicy.model_validate(record.payload["investigations"])
    assert record.mode == "mock" and record.test_only and record.status == "draft"
    assert policy.deadline_is_failure is False and policy.late_delivery == "quarantine"


def test_alert_api_paginates_without_private_payload(upstream, desk):
    from app.investigations.service import InvestigationService

    task, case = open_case(upstream, desk)
    with upstream[0]() as s, s.begin():
        s.execute(
            text(
                "UPDATE investigations SET deadline_at=UTC_TIMESTAMP(6)-INTERVAL 1 SECOND "
                "WHERE task_id=:id"
            ),
            {"id": task},
        )
    InvestigationService(upstream[0], upstream=upstream[1]).scan([task])
    other = upstream[2]("lost_response")
    submit(upstream, other)
    InvestigationService(upstream[0], upstream=upstream[1]).scan([other])
    response = desk[0].get("/api/v1/admin/investigation-alerts", params={"limit": 1})
    assert response.status_code == 200
    page = response.json()
    assert isinstance(page, dict) and len(page["items"]) == 1
    assert "payload" not in page["items"][0]
    assert page["next_cursor"]
    second = (
        desk[0]
        .get(
            "/api/v1/admin/investigation-alerts", params={"limit": 1, "cursor": page["next_cursor"]}
        )
        .json()
    )
    assert second["items"][0]["key"] != page["items"][0]["key"]


def test_manual_close_accounts_staged_bytes_without_quota(upstream, desk, ready, monkeypatch):
    from app.audit.models import AuditEvent
    from app.investigations.models import Investigation, Resolution
    from app.results.models import ResultManifestRecord, ResultSaveItem
    from app.storage.models import CapacityReservation, StorageAccount
    from tests.integration.test_settlement import publisher

    task = ready(count=2)
    pub = publisher(upstream, desk[0].app.state.settings.storage_root)

    def fail_commit(staged):
        raise OSError("TEST_ONLY journal protection")

    monkeypatch.setattr(pub.persistence.store, "commit", fail_commit)
    assert pub.run(task) is None
    case = existing_case(desk, task)
    response = resolve(desk, task, case, "manual_close")
    assert response.status_code == 200, response.text
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        assert row.state == "MANUALLY_CLOSED" and row.settlement_state == "RELEASED"
        assert s.get(Investigation, task).version > case["version"]
        assert s.get(CreditAccount, row.user_id).frozen == 0
        assert s.scalar(select(Resolution).where(Resolution.task_id == task)) is not None
        expected = sum(s.scalars(
            select(ResultSaveItem.actual_bytes)
            .join(ResultManifestRecord, ResultManifestRecord.id == ResultSaveItem.manifest_id)
            .where(ResultManifestRecord.task_id == task)
        ).all())
        reservation = s.get(CapacityReservation, row.capacity_reservation_id)
        assert reservation.state == "reserved"
        assert reservation.estimated_bytes >= expected > 0
        assert s.get(StorageAccount, row.user_id).reserved_bytes >= expected
        assert (
            s.scalar(
                select(AuditEvent).where(
                    AuditEvent.object_id == task, AuditEvent.action == "investigation.manual_close"
                )
            )
            is not None
        )
        assert (
            s.scalar(select(CreditLedger).where(CreditLedger.operation_key == "settle:" + task))
            is not None
        )
