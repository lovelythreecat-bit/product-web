"""T10 callbacks exercise the real HTTP boundary and MySQL persistence."""

import hashlib
import hmac
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agents.mock_server import CALLBACK_KEY
from app.main import create_app
from app.tasks.models import GenerationTask
from tests.faults.test_upstream_recovery import calls, facts, submit
from tests.faults.test_upstream_recovery import upstream as upstream_fixture

upstream = upstream_fixture


@pytest.fixture
def callbacks(upstream, mysql_settings):
    with TestClient(create_app(mysql_settings)) as client:
        yield client


def event_for(runtime, task_id, index=1):
    factory, _, _, server, _ = runtime
    with factory() as s:
        task = s.get(GenerationTask, task_id)
        binding = runtime[1].registry.bind_task(s, task)
        _, body = server.simulator.events(binding.wire_agent_id, task.external_submission_id)
        event = body["events"][index]
        return f"/api/v1/agent-callbacks/{task.agent_id}/{task.agent_version}", event


def changed(event, **values):
    payload = json.loads(event["raw"])
    payload.update(values)
    raw = json.dumps(payload).encode()
    return dict(
        raw=raw,
        headers={"X-Mock-Signature": hmac.new(CALLBACK_KEY, raw, hashlib.sha256).hexdigest()},
    )


def post(client, path, event):
    return client.post(path, content=event["raw"], headers=event["headers"])


def reducer(runtime):
    import app.agents.upstream as module

    assert callable(getattr(module.UpstreamService, "poll_original_task", None)), (
        "UpstreamService must expose durable original-task polling"
    )
    return runtime[1]


def test_repeated_poll_history_does_not_repeat_sql_under_the_account_lock(upstream):
    from copy import deepcopy

    from sqlalchemy import event, func

    from app.agents.callbacks import CallbackService
    from app.agents.models import UpstreamEvidence
    from app.dispatch.consumer import LeaseManager
    from app.ledger.service import now

    factory, service, create, *_ = upstream
    task_id = create()
    submit(upstream, task_id)
    assert service.poll_original_task(task_id).state == 'SAVING'
    with factory() as session, session.begin():
        original = session.scalar(select(UpstreamEvidence).where(
            UpstreamEvidence.task_id == task_id, UpstreamEvidence.kind == 'observation',
        ).order_by(UpstreamEvidence.created_at.desc(), UpstreamEvidence.id.desc()))
        for _ in range(75):
            session.add(UpstreamEvidence(
                id=str(uuid4()), task_id=task_id, attempt_id=original.attempt_id,
                kind='observation', payload=deepcopy(original.payload), created_at=now(),
            ))
        changed = deepcopy(original.payload)
        changed['identity']['snapshot_digest'] = 'different-input'
        session.add(UpstreamEvidence(
            id=str(uuid4()), task_id=task_id, attempt_id=original.attempt_id,
            kind='observation', payload=changed, created_at=now(),
        ))

    manager = LeaseManager(factory)
    lease = manager.claim_task(task_id, 'TEST_ONLY_history')
    engine = factory.kw['bind']
    statements = []
    def capture(*args):
        statements.append(args[2])
    event.listen(engine, 'before_cursor_execute', capture)
    try:
        CallbackService(service).import_observations(task_id, lease)
    finally:
        event.remove(engine, 'before_cursor_execute', capture)
        manager.release(lease)
    assert len(statements) < 40, 'Repeated poll history held the account lock across redundant SQL'
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(UpstreamEvidence).where(
            UpstreamEvidence.task_id == task_id, UpstreamEvidence.kind == 'callback_conflict',
        )) == 1
    assert service._view(task_id).state == 'SAVING'


def test_product_save_can_run_while_poll_history_is_scanned(upstream, monkeypatch):
    from copy import deepcopy
    from datetime import timedelta

    import app.agents.callbacks as module
    from app.agents.models import UpstreamEvidence
    from app.auth.models import AuthSession, User
    from app.common.types import Principal
    from app.conversations.schemas import ProductVersionCreate
    from app.conversations.service import ConversationService
    from app.dispatch.consumer import LeaseManager
    from app.ledger.service import now

    factory, service, create, *_ = upstream
    task_id = create()
    submit(upstream, task_id)
    assert service.poll_original_task(task_id).state == "SAVING"
    with factory() as session, session.begin():
        task = session.get(GenerationTask, task_id)
        user = session.get(User, task.user_id)
        credential = AuthSession(
            id=str(uuid4()), user_id=user.id, token_hash=uuid4().hex,
            csrf_hash=uuid4().hex, auth_version=user.auth_version,
            expires_at=now() + timedelta(hours=1),
        )
        session.add(credential)
        principal = Principal(user_id=user.id, session_id=credential.id,
                              auth_version=user.auth_version, role=user.role)
        original = session.scalar(select(UpstreamEvidence).where(
            UpstreamEvidence.task_id == task_id, UpstreamEvidence.kind == "observation",
        ).limit(1))
        # Durable source progress skips the already imported history. A genuinely
        # new receipt must still be scanned without holding the account lock.
        session.add(UpstreamEvidence(
            id=str(uuid4()), task_id=task_id, attempt_id=original.attempt_id,
            kind="observation", payload=deepcopy(original.payload), created_at=now(),
        ))

    saved = []
    digest = module.content_digest

    def save_during_history_scan(payload):
        if not saved:
            with factory() as session:
                saved.append(ConversationService(session).create_product_version(
                    principal, ProductVersionCreate(product={"name": "TEST_ONLY_concurrent_edit"}),
                ))
                session.rollback()
        return digest(payload)

    monkeypatch.setattr(module, "content_digest", save_during_history_scan)
    manager = LeaseManager(factory)
    lease = manager.claim_task(task_id, "TEST_ONLY_product_edit")
    try:
        module.CallbackService(service).import_observations(task_id, lease)
    finally:
        manager.release(lease)
    assert len(saved) == 1
    assert service._view(task_id).state == "SAVING"


def test_forged_cross_agent_task(upstream, callbacks):
    task = upstream[2]()
    other = upstream[2](kind="image")
    submit(upstream, task)
    submit(upstream, other)
    path, event = event_for(upstream, task)
    other_path, _ = event_for(upstream, other)
    assert (
        post(callbacks, path, dict(event, headers={"X-Mock-Signature": "0" * 64})).status_code
        == 403
    )
    assert post(callbacks, other_path, event).status_code == 403
    wrong_id = str(uuid4())
    assert (
        post(
            callbacks, path, changed(event, upstream_task_id=wrong_id, event_id=f"{wrong_id}:2")
        ).status_code
        == 409
    )
    assert post(callbacks, path, changed(event, user_id=str(uuid4()))).status_code == 403
    assert facts(upstream[0], task)[-1] == "frozen"


@pytest.mark.parametrize("kind", ["copy", "image", "video"])
def test_duplicate_out_of_order_terminal(upstream, callbacks, kind):
    task = upstream[2](kind=kind)
    submit(upstream, task)
    path, ready = event_for(upstream, task)
    assert post(callbacks, path, ready).status_code == 202
    # New app + adapter instance cannot erase MySQL replay protection.
    assert post(callbacks, path, ready).json()["status"] == "DUPLICATE"
    service = reducer(upstream)
    assert service.poll_original_task(task).state == "SAVING"
    _, running = event_for(upstream, task, 0)
    assert post(callbacks, path, running).status_code == 202
    before = service._view(task).state_version
    assert service.poll_original_task(task).state_version == before
    from app.agents.models import AgentEvent, AgentEventDecision

    with upstream[0]() as s:
        events = s.scalars(select(AgentEvent).where(AgentEvent.task_id == task)).all()
        decisions = s.scalars(
            select(AgentEventDecision).where(AgentEventDecision.task_id == task)
        ).all()
        assert len(events) == 2
        assert {d.disposition for d in decisions} == {"APPLIED", "STALE"}
    assert facts(upstream[0], task)[-1] == "frozen"
    assert calls(upstream, task)["submit"] == 1


def test_same_event_changed_payload_is_durable_conflict(upstream, callbacks):
    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    assert post(callbacks, path, event).status_code == 202
    assert post(callbacks, path, changed(event, state="FAILED", result=None)).status_code == 409
    from app.agents.models import UpstreamEvidence

    with upstream[0]() as s:
        assert s.scalar(
            select(UpstreamEvidence).where(
                UpstreamEvidence.task_id == task, UpstreamEvidence.kind == "callback_conflict"
            )
        )


def test_concurrent_changed_event_replays_have_one_conflict_per_variant(upstream, callbacks):
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import func

    from app.agents.models import UpstreamEvidence

    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    assert post(callbacks, path, event).status_code == 202
    conflict = changed(event, state="FAILED", result=None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: post(callbacks, path, conflict).status_code, range(20)))
    assert results == [409] * 20
    with upstream[0]() as session:
        assert session.scalar(select(func.count()).select_from(UpstreamEvidence).where(
            UpstreamEvidence.task_id == task, UpstreamEvidence.kind == "callback_conflict",
        )) == 1
    assert post(callbacks, path, changed(event)).status_code == 409
    with upstream[0]() as session:
        assert session.scalar(select(func.count()).select_from(UpstreamEvidence).where(
            UpstreamEvidence.task_id == task, UpstreamEvidence.kind == "callback_conflict",
        )) == 2


def test_import_conflict_and_source_disposition_rollback_and_restart_together(upstream):
    from copy import deepcopy

    from sqlalchemy import event, func

    from app.agents.callbacks import CallbackService
    from app.agents.models import ObservationImport, UpstreamEvidence
    from app.dispatch.consumer import LeaseManager
    from app.ledger.service import now

    factory, service, create, *_ = upstream
    task_id = create()
    submit(upstream, task_id)
    assert service.poll_original_task(task_id).state == "SAVING"
    reference = str(uuid4())
    with factory() as session, session.begin():
        original = session.scalar(select(UpstreamEvidence).where(
            UpstreamEvidence.task_id == task_id, UpstreamEvidence.kind == "observation",
        ).order_by(UpstreamEvidence.created_at.desc(), UpstreamEvidence.id.desc()).limit(1))
        payload = deepcopy(original.payload)
        payload["outcome"]["result"]["warnings"] = ["TEST_ONLY changed metadata"]
        session.add(UpstreamEvidence(
            id=reference, task_id=task_id, attempt_id=original.attempt_id,
            kind="observation", payload=payload, created_at=now(),
        ))

    def crash(mapper, connection, target):
        if target.source_ref == reference:
            raise RuntimeError("TEST_ONLY stop before disposition insert")

    manager = LeaseManager(factory)
    lease = manager.claim_task(task_id, "TEST_ONLY_import_rollback")
    event.listen(ObservationImport, "before_insert", crash)
    try:
        with pytest.raises(RuntimeError, match="stop before disposition"):
            CallbackService(service).import_observations(task_id, lease)
    finally:
        event.remove(ObservationImport, "before_insert", crash)
    try:
        with factory() as session:
            assert session.scalar(select(ObservationImport).where(
                ObservationImport.source_ref == reference,
            )) is None
            assert session.scalar(select(func.count()).select_from(UpstreamEvidence).where(
                UpstreamEvidence.task_id == task_id,
                UpstreamEvidence.kind == "callback_conflict",
            )) == 0
        for _ in range(3):
            CallbackService(service).import_observations(task_id, lease)
        with factory() as session:
            receipt = session.scalar(select(ObservationImport).where(
                ObservationImport.source_ref == reference,
            ))
            assert receipt.disposition == "CONFLICT"
            assert session.scalar(select(func.count()).select_from(UpstreamEvidence).where(
                UpstreamEvidence.task_id == task_id,
                UpstreamEvidence.kind == "callback_conflict",
            )) == 1
    finally:
        manager.release(lease)


def test_fresh_callback_can_reduce_blocked_task_without_remote_query(
    upstream, callbacks, monkeypatch,
):
    from app.agents.callbacks import CallbackService
    from app.agents.models import AgentEventDecision
    from app.dispatch.consumer import Lease, LeaseManager
    from app.dispatch.models import OutboxEvent
    from app.tasks.state_machine import TransitionError

    factory, service, create, *_ = upstream
    task_id = create()
    submit(upstream, task_id)
    original = CallbackService._manifest

    def former_policy(*args):
        raise TransitionError("RESULT_POLICY_UNAVAILABLE")

    monkeypatch.setattr(CallbackService, "_manifest", former_policy)
    assert service.poll_original_task(task_id).state == "INVESTIGATING"
    monkeypatch.setattr(CallbackService, "_manifest", original)
    before = calls(upstream, task_id)["query_id"]
    path, ready = event_for(upstream, task_id)
    assert post(callbacks, path, ready).status_code == 202
    with factory() as session:
        task = session.get(GenerationTask, task_id)
        wake = session.scalar(select(OutboxEvent).where(
            OutboxEvent.task_id == task_id, OutboxEvent.state_version == task.state_version,
            OutboxEvent.operation == "recover",
        ))
        wake_id, version, generation = wake.event_id, wake.state_version, wake.dispatch_generation
    manager = LeaseManager(factory)
    lease = manager.claim_dispatch(
        task_id, "TEST_ONLY_callback_unblock", wake_id, version, generation,
    )
    assert isinstance(lease, Lease)
    try:
        assert CallbackService(service).poll_original_task(task_id, lease=lease).state == "SAVING"
    finally:
        manager.release(lease)
    assert calls(upstream, task_id)["query_id"] == before
    with factory() as session:
        decisions = session.scalars(select(AgentEventDecision).where(
            AgentEventDecision.task_id == task_id,
        )).all()
        assert {row.disposition for row in decisions} == {"APPLIED", "CONFLICT"}


@pytest.mark.parametrize("initial", ["SUBMITTING", "INVESTIGATING"])
def test_running_callback_defers_new_version_remote_recovery(
    upstream, callbacks, monkeypatch, initial,
):
    from app.dispatch.consumer import LeaseManager
    from app.dispatch.models import OutboxEvent
    from app.dispatch.recovery import RecoveryScheduler, database_now

    factory, service, create, *_ = upstream
    task_id = create("lost_response" if initial == "INVESTIGATING" else "normal")
    if initial == "SUBMITTING":
        original_apply = service._apply_observation
        monkeypatch.setattr(service, "_apply_observation", lambda *args, **kwargs: None)
    assert submit(upstream, task_id).state == initial
    if initial == "SUBMITTING":
        monkeypatch.setattr(service, "_apply_observation", original_apply)
    path, running = event_for(upstream, task_id, 0)
    assert post(callbacks, path, running).status_code == 202
    assert service.poll_original_task(task_id).state == "RUNNING"
    assert calls(upstream, task_id)["query_id"] == 0
    assert calls(upstream, task_id)["query_external"] == 0
    with factory() as session:
        task = session.get(GenerationTask, task_id)
        wake = session.scalar(select(OutboxEvent).where(
            OutboxEvent.task_id == task_id, OutboxEvent.state_version == task.state_version,
            OutboxEvent.operation == "recover",
        ))
        assert wake.ready_at > database_now(session)
        assert wake.dispatch_generation > 1
        identity = task.id, wake.event_id, wake.state_version, wake.dispatch_generation
    task_id, event_id, version, generation = identity
    manager = LeaseManager(factory)
    assert manager.claim_dispatch(task_id, "TEST_ONLY_old_now", event_id, version,
                                  generation - 1) == "rejected"
    assert manager.claim_dispatch(task_id, "TEST_ONLY_not_due", event_id, version,
                                  generation) == "busy"
    scheduler = RecoveryScheduler(factory, task_ids=[task_id])
    assert scheduler.recover_due_tasks().scheduled == ()


@pytest.mark.parametrize("snapshot_race", [False, True])
def test_new_id_duplicate_keeps_needs_input_after_restart_and_concurrent_commit(
    upstream, callbacks, monkeypatch, snapshot_race,
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    import app.agents.callbacks as module
    from app.agents.callbacks import CallbackService
    from app.agents.contracts import VerifiedEvent
    from app.agents.models import AgentEvent, AgentEventDecision
    from app.catalog.schemas import content_digest
    from app.tasks.repository import locked_execution
    from app.tasks.state_machine import TransitionEvidence, transition_task

    factory, service, create, *_ = upstream
    task_id = create()
    submit(upstream, task_id)
    path, running = event_for(upstream, task_id, 0)
    assert post(callbacks, path, running).status_code == 202
    assert service.poll_original_task(task_id).state == "RUNNING"
    lease = service.leases.claim_task(task_id, "TEST_ONLY_manual_wait")
    try:
        with factory() as session, session.begin():
            task = locked_execution(session, task_id, lease)
            transition_task(session, task_id, task.state_version, "INVESTIGATING",
                            TransitionEvidence(lease))
            task.investigation_reason = "UPSTREAM_NEEDS_INPUT"
    finally:
        service.leases.release(lease)
    with factory() as session:
        task = session.get(GenerationTask, task_id)
        binding = service.registry.bind_task(session, task)
        original = session.scalar(select(AgentEvent).where(
            AgentEvent.task_id == task_id, AgentEvent.source == "callback",
            AgentEvent.sequence == 1,
        ))
        assert original is not None
        assert session.get(AgentEventDecision, original.id).disposition == "APPLIED"
        verified = VerifiedEvent.model_validate(original.payload["event"])
        assert verified.status in {"VERIFIED", "DUPLICATE"}
        assert verified.event_id is not None
    # Internal trusted provider boundary: different event IDs may carry the same
    # semantic event. HTTP mock-v1 nonce-shape validation is tested separately.
    duplicate = verified.model_copy(update={"event_id": verified.event_id + ":another-id"})
    assert duplicate.model_dump(exclude={"event_id"}) == verified.model_dump(exclude={"event_id"})

    def commit_callback():
        return CallbackService(service).apply_verified_agent_event(
            binding, duplicate, raw_digest=content_digest(duplicate.model_dump(mode="json")),
        )

    monkeypatch.setattr(service, "recover_original_task", lambda *args, **kwargs: pytest.fail(
        "Duplicate/stale inbox content must not query a task waiting for user input"))
    resumed = CallbackService(service)
    if snapshot_race:
        snapshot_taken, inbox_committed = Event(), Event()
        monkeypatch.setattr(resumed, "import_observations", lambda *args: None)

        def pause_before_lock(session, current_task, current_lease):
            session.scalar(select(GenerationTask.user_id).where(GenerationTask.id == current_task))
            snapshot_taken.set()
            assert inbox_committed.wait(5)
            return locked_execution(session, current_task, current_lease)

        monkeypatch.setattr(module, "locked_execution", pause_before_lock)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(resumed.poll_original_task, task_id)
            assert snapshot_taken.wait(5)
            try:
                receipt = commit_callback()
            finally:
                inbox_committed.set()
            result = future.result(timeout=10)
    else:
        receipt = commit_callback()
        with factory() as session:
            assert session.get(GenerationTask, task_id).investigation_reason == (
                "CALLBACK_INBOX_PENDING:UPSTREAM_NEEDS_INPUT"
            )
        result = resumed.poll_original_task(task_id)
    assert receipt.status == "ACCEPTED"
    assert result.state == "INVESTIGATING"
    assert result.investigation_reason == "UPSTREAM_NEEDS_INPUT"
    with factory() as session:
        assert session.get(AgentEventDecision, receipt.reference).disposition == "DUPLICATE"
    assert calls(upstream, task_id)["query_id"] == 0


def test_failed_notification_keeps_freeze_and_durable_evidence(upstream, callbacks):
    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    assert post(callbacks, path, changed(event, state="FAILED", result=None)).status_code == 202
    service = reducer(upstream)
    assert service.poll_original_task(task).state == "INVESTIGATING"
    assert service.pending_failure(task) is not None
    assert facts(upstream[0], task)[-1] == "frozen"


def test_callback_does_not_steal_worker_lease(upstream, callbacks):
    from app.dispatch.consumer import LeaseManager

    task = upstream[2]()
    submit(upstream, task)
    manager = LeaseManager(upstream[0])
    lease = manager.claim_task(task, "TEST_ONLY_busy")
    path, event = event_for(upstream, task)
    assert post(callbacks, path, event).status_code == 202
    assert reducer(upstream).poll_original_task(task).state == "RUNNING"
    manager.release(lease)
    assert reducer(upstream).poll_original_task(task).state == "SAVING"


@pytest.mark.parametrize(
    "mutation",
    [
        {"timestamp": 0},
        {"timestamp": 99999999999},
        {"sequence": True},
        {"sequence": 3},
        {"event_id": "different-nonce"},
        {"protocol_version": "unknown"},
        {"test_only": False},
        {"status": "VERIFIED"},
        {"agent_id": "video"},
    ],
)
def test_wire_shape_time_nonce_and_origin_rejected(upstream, callbacks, mutation):
    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    assert post(callbacks, path, changed(event, **mutation)).status_code == 403
    assert upstream[1]._view(task).state == "RUNNING"


def test_same_sequence_callback_poll_conflict_preserves_first_result(upstream, callbacks):
    factory, service, create, server, _ = upstream
    task = create()
    submit(upstream, task)
    # Query first: durable sequence 2. A later signed failure cannot replace it.
    assert reducer(upstream).poll_original_task(task).state == "SAVING"
    path, event = event_for(upstream, task)
    assert post(callbacks, path, changed(event, state="FAILED", result=None)).status_code == 202
    assert service.poll_original_task(task).state == "SAVING"
    assert service.pending_failure(task) is None
    from app.agents.models import AgentEventDecision

    with factory() as s:
        assert s.scalar(
            select(AgentEventDecision).where(
                AgentEventDecision.task_id == task, AgentEventDecision.disposition == "CONFLICT"
            )
        )


@pytest.mark.parametrize("bad", ["partial", "locator", "media_type", "item_key", "count"])
def test_untrusted_manifest_cannot_enter_saving(upstream, callbacks, bad):
    task = upstream[2]("query_unavailable")
    submit(upstream, task)
    path, event = event_for(upstream, task)
    result = json.loads(event["raw"])["result"]
    if bad == "partial":
        result["complete"] = False
    elif bad == "count":
        result["expected_items"] = 2
        result["items"].append(dict(result["items"][0], item_key="original-2"))
    else:
        result["items"][0][bad] = "https://untrusted.invalid/file"
    assert post(callbacks, path, changed(event, result=result)).status_code == 202
    assert reducer(upstream).poll_original_task(task).state == "INVESTIGATING"
    assert reducer(upstream).original_result(task) is None
    assert facts(upstream[0], task)[-1] == "frozen"


def test_concurrent_receipts_reduce_once(upstream, callbacks):
    from concurrent.futures import ThreadPoolExecutor

    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: post(callbacks, path, event).json()["status"], range(2)))
    assert sorted(results) == ["ACCEPTED", "DUPLICATE"]
    service = reducer(upstream)
    assert service.poll_original_task(task).state == "SAVING"
    before = service._view(task).state_version
    assert service.poll_original_task(task).state_version == before


def test_public_verified_dto_without_signature_is_rejected(upstream, callbacks):
    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    body = json.loads(event["raw"]) | {"status": "VERIFIED"}
    assert callbacks.post(path, json=body).status_code == 403


def test_terminal_late_event_is_audited_without_state_or_settlement(upstream, callbacks):
    # Terminal fixture represents T12 having completed settlement; T10 never does so.
    from sqlalchemy import text

    from app.agents.models import AgentEventDecision

    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    with upstream[0]() as s, s.begin():
        s.execute(
            text(
                "UPDATE generation_tasks SET state='FAILED', settlement_state='RELEASED' "
                "WHERE id=:id"
            ),
            {"id": task},
        )
    before = upstream[1]._view(task)
    assert post(callbacks, path, event).status_code == 202
    assert reducer(upstream).poll_original_task(task) == before
    with upstream[0]() as s:
        assert (
            s.scalar(
                select(AgentEventDecision.disposition).where(AgentEventDecision.task_id == task)
            )
            == "TERMINAL_LATE"
        )


def test_production_and_unknown_version_fail_closed(upstream, mysql_settings):
    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    app = create_app(mysql_settings.model_copy(update={"mode": "production", "test_only": False}))
    with TestClient(app) as client:
        assert post(client, path, event).status_code == 403
    with TestClient(create_app(mysql_settings)) as client:
        assert post(client, path.replace("TEST_ONLY_v1", "unknown"), event).status_code == 403


def test_original_result_handoff_is_bound_to_durable_identity(upstream):
    task = upstream[2]()
    submit(upstream, task)
    service = reducer(upstream)
    service.poll_original_task(task)
    delivery = service.original_result(task)
    assert getattr(delivery, "task_id", None) == task
    assert delivery.manifest.complete
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        assert (
            delivery.agent_id,
            delivery.agent_version,
            delivery.external_submission_id,
            delivery.upstream_id,
        ) == (row.agent_id, row.agent_version, row.external_submission_id, row.upstream_id)
    assert delivery.reference


def test_changed_raw_bytes_under_same_nonce_conflict(upstream, callbacks):
    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    assert post(callbacks, path, event).status_code == 202
    # Equivalent JSON has different raw signed bytes. Nonce cannot be reused for it.
    assert post(callbacks, path, changed(event)).status_code == 409


def test_callback_before_upstream_binding_recovers_original(upstream, callbacks):
    task = upstream[2]("lost_response")
    submit(upstream, task)
    path, event = event_for(upstream, task)
    assert post(callbacks, path, event).status_code == 202
    assert reducer(upstream).poll_original_task(task).state == "SAVING"
    assert calls(upstream, task)["submit"] == 1
    assert calls(upstream, task)["query_external"] == 0


def test_expired_fencing_cannot_apply_receipt(upstream, callbacks):
    from app.agents.callbacks import CallbackService
    from app.dispatch.consumer import LeaseManager
    from app.tasks.state_machine import TransitionError

    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    post(callbacks, path, event)
    manager = LeaseManager(upstream[0])
    old = manager.claim_task(task, "TEST_ONLY_old")
    manager.release(old)
    new = manager.claim_task(task, "TEST_ONLY_new")
    with pytest.raises(TransitionError, match="LEASE_LOST"):
        CallbackService(upstream[1]).reduce_pending(task, old)
    assert upstream[1]._view(task).state == "RUNNING"
    manager.release(new)
    assert reducer(upstream).poll_original_task(task).state == "SAVING"


def test_conflicting_receipt_cannot_be_reused_as_original_result_proof(upstream, callbacks):
    from app.agents.callbacks import CallbackService
    from app.agents.models import AgentEventDecision
    from app.tasks.state_machine import TransitionError

    task = upstream[2]()
    submit(upstream, task)
    reducer(upstream).poll_original_task(task)
    path, event = event_for(upstream, task)
    result = json.loads(event["raw"])["result"]
    result["items"][0]["sha256"] = "0" * 64
    assert post(callbacks, path, changed(event, result=result)).status_code == 202
    reducer(upstream).poll_original_task(task)
    with upstream[0]() as s:
        ref = s.scalar(
            select(AgentEventDecision.event_ref).where(
                AgentEventDecision.task_id == task, AgentEventDecision.disposition == "CONFLICT"
            )
        )
        with pytest.raises(TransitionError, match="EVIDENCE"):
            CallbackService(upstream[1]).verify_original_result(
                s, s.get(GenerationTask, task), "SAVING", ref
            )
