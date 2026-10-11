"""T09: real MySQL/Redis and HTTP simulator; only fixture-owned task identities."""

from threading import Thread
from uuid import uuid4

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.agents.mock import MockAgentAdapter
from app.agents.mock_server import PROTOCOL, BoundedServer, Simulator
from app.auth.models import User
from app.catalog.models import AgentRecord
from app.dispatch.consumer import LeaseManager
from app.dispatch.outbox import enqueue_outbox
from app.ledger.models import CreditAccount, CreditLedger, CreditReservation
from app.ledger.service import freeze_credits, now
from app.tasks.models import GenerationTask, TaskSnapshot


@pytest.fixture
def upstream(mysql_engine, redis_namespace, ledger_task, monkeypatch):
    from worker import main

    # Missing trusted worker composition is a business failure, not an import error.
    assert callable(getattr(main, "compose_worker", None)), "Worker has no upstream handlers"
    from app.agents.registry import AgentRegistry
    from app.agents.upstream import UpstreamService

    monkeypatch.setenv("APP_TEST_ONLY", "true")
    server = BoundedServer(("127.0.0.1", 0))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    factory = sessionmaker(mysql_engine, expire_on_commit=False)
    registry = AgentRegistry(mode="mock", test_only=True)
    service = UpstreamService(factory, registry)
    owned = []

    def create(scenario="normal", kind="copy", agent_identity=None):
        task_id, user_id = str(uuid4()), str(uuid4())
        with Session(mysql_engine) as s, s.begin():
            s.add(
                User(
                    id=user_id,
                    account_normalized="t09_" + uuid4().hex,
                    password_hash="TEST_ONLY_unusable",
                    created_at=now(),
                )
            )
            s.flush()
            s.add(
                CreditAccount(
                    user_id=user_id, available=100, frozen=0, consumed=0, credited_total=100
                )
            )
            s.flush()

            def snapshot_before_insert(mapper, connection, target):
                target.agent_snapshot = dict(
                    agent_id=agent_identity or target.agent_snapshot["agent_id"],
                    version="TEST_ONLY_v1",
                    kind=kind,
                    name="TEST_ONLY Agent",
                    mode="mock",
                    test_only=True,
                    enabled=True,
                    protocol_version=PROTOCOL,
                    input_support=dict(
                        product_required_fields=[],
                        instruction_required=False,
                        min_materials=0,
                        max_materials=0,
                    ),
                    policy_versions={},
                    secret_configured=False,
                )

            def identity_before_insert(mapper, connection, target):
                if agent_identity:
                    target.agent_id = agent_identity

            event.listen(GenerationTask, "before_insert", identity_before_insert)
            event.listen(TaskSnapshot, "before_insert", snapshot_before_insert)
            try:
                task = ledger_task(s, user_id, task_id)
            finally:
                event.remove(TaskSnapshot, "before_insert", snapshot_before_insert)
                event.remove(GenerationTask, "before_insert", identity_before_insert)
            freeze_credits(s, user_id, task_id, 30)
            snapshot = s.get(TaskSnapshot, task_id).agent_snapshot
            if s.get(AgentRecord, (task.agent_id, task.agent_version)) is None:
                s.add(
                    AgentRecord(
                        agent_id=task.agent_id,
                        version=task.agent_version,
                        snapshot=snapshot,
                        endpoint=url,
                    )
                )
            external = task.external_submission_id
            enqueue_outbox(s, task_id, "submit")
        owned.append(task_id)
        with server.simulator.lock:
            server.simulator.configure(kind, external, {"scenario": scenario})
        return task_id

    def worker():
        redis, prefix = redis_namespace
        return main.compose_worker(
            factory, redis, prefix + "dispatch", "workers", "t09", registry=registry, task_ids=owned
        )

    yield factory, service, create, server, worker
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def facts(factory, task_id):
    with factory() as s:
        task = s.get(GenerationTask, task_id)
        snap = s.get(TaskSnapshot, task_id)
        freezes = s.scalar(
            select(func.count())
            .select_from(CreditLedger)
            .where(CreditLedger.task_id == task_id, CreditLedger.kind == "freeze")
        )
        reservation = s.scalar(
            select(CreditReservation.state).where(CreditReservation.task_id == task_id)
        )
        return task.external_submission_id, snap.input_snapshot, snap.quote, freezes, reservation


def calls(runtime, task_id):
    factory, _, _, server, _ = runtime
    with factory() as s:
        task = s.get(GenerationTask, task_id)
        kind = s.get(TaskSnapshot, task_id).agent_snapshot["kind"]
        with server.simulator.lock:
            return dict(server.simulator.record(kind, task.external_submission_id)["calls"])


def submit(runtime, task_id):
    factory, service, *_ = runtime
    manager = LeaseManager(factory)
    lease = manager.claim_task(task_id, "TEST_ONLY_submitter")
    try:
        return service.submit_original_task(task_id, lease)
    finally:
        manager.release(lease)


def test_lost_response_reliable_idempotency(upstream):
    factory, service, create, server, _ = upstream
    task = create("lost_response")
    original = facts(factory, task)
    assert submit(upstream, task).state == "INVESTIGATING"
    # Hide external lookup without changing the accepted original or its HTTP identity.
    with server.simulator.lock:
        record = next(iter(server.simulator.records.values()))
        record["scenario"] = "not_found"
    # Explicit evidence acquisition is trusted; NOT_FOUND itself cannot issue a proof.
    proof = service.collect_retry_evidence(task, kind="reliable_idempotency")
    assert service.recover_original_task(task, proof).state == "RUNNING"
    assert calls(upstream, task)["submit"] == 2
    assert calls(upstream, task)["generation_intents"] == 1
    assert facts(factory, task) == original


@pytest.mark.parametrize("scenario", ["not_found", "query_unavailable", "unsupported"])
def test_not_found_is_not_safe_retry(upstream, scenario):
    factory, service, create, _, _ = upstream
    task = create("lost_response")
    original = facts(factory, task)
    # Persisted intent without known upstream identity models process death after send.
    from app.agents.models import UpstreamAttempt

    submit(upstream, task)
    server = upstream[3]
    with server.simulator.lock:
        next(iter(server.simulator.records.values()))["scenario"] = scenario
    assert service.recover_original_task(task).state == "INVESTIGATING"
    assert calls(upstream, task)["submit"] == 1
    with factory() as s:
        assert (
            s.scalar(
                select(func.count())
                .select_from(UpstreamAttempt)
                .where(UpstreamAttempt.task_id == task)
            )
            == 1
        )
    assert facts(factory, task) == original


def test_known_id_queries_original(upstream):
    factory, service, create, _, _ = upstream
    task = create("query_unavailable")
    original = facts(factory, task)
    assert submit(upstream, task).state == "RUNNING"
    service.recover_original_task(task)
    assert calls(upstream, task)["query_id"] == 1
    assert calls(upstream, task)["query_external"] == 0
    assert calls(upstream, task)["submit"] == 1
    assert facts(factory, task) == original


@pytest.mark.parametrize("phase", ["before_call", "before_bind", "after_bind"])
def test_crash_before_after_bind(upstream, monkeypatch, phase):
    factory, service, create, _, _ = upstream
    task = create()
    original = facts(factory, task)
    from app.agents.models import UpstreamAttempt

    if phase == "before_call":
        real = MockAgentAdapter.submit_scoped

        def crash(*args, **kwargs):
            with factory() as s:
                assert s.get(GenerationTask, task).state == "SUBMITTING"
                assert (
                    s.scalar(
                        select(func.count())
                        .select_from(UpstreamAttempt)
                        .where(UpstreamAttempt.task_id == task)
                    )
                    == 1
                )
            raise SystemExit("TEST_ONLY crash before call")

        monkeypatch.setattr(MockAgentAdapter, "submit_scoped", crash)
    else:
        real = service._apply_observation

        def crash(*args, **kwargs):
            if phase == "after_bind":
                real(*args, **kwargs)
            raise SystemExit("TEST_ONLY crash around binding")

        monkeypatch.setattr(service, "_apply_observation", crash)
    with pytest.raises(SystemExit):
        submit(upstream, task)
    if phase == "before_call":
        monkeypatch.setattr(MockAgentAdapter, "submit_scoped", real)
    else:
        monkeypatch.setattr(service, "_apply_observation", real)
    result = service.recover_original_task(task)
    assert result.state == ("INVESTIGATING" if phase == "before_call" else "RUNNING")
    assert calls(upstream, task)["submit"] == (0 if phase == "before_call" else 1)
    assert facts(factory, task) == original


def test_expired_lease_not_nonacceptance(upstream, monkeypatch):
    factory, service, create, _, _ = upstream
    task = create()
    real = MockAgentAdapter.submit_scoped

    def expire(*args, **kwargs):
        response = real(*args, **kwargs)
        with factory() as s, s.begin():
            s.execute(
                text(
                    "UPDATE generation_tasks SET lease_expires_at=UTC_TIMESTAMP(6) "
                    "- INTERVAL 1 SECOND WHERE id=:id"
                ),
                {"id": task},
            )
        return response

    monkeypatch.setattr(MockAgentAdapter, "submit_scoped", expire)
    from app.tasks.state_machine import TransitionError

    with pytest.raises(TransitionError, match="LEASE_LOST"):
        submit(upstream, task)
    with factory() as s:
        assert s.get(GenerationTask, task).upstream_id is None
    assert service.recover_original_task(task).state == "RUNNING"
    assert calls(upstream, task)["submit"] == 1


@pytest.mark.parametrize("kind", ["copy", "image", "video"])
def test_real_worker_routes_platform_uuid_to_pinned_wire_kind(upstream, kind):
    factory, _, create, _, worker = upstream
    task = create(kind=kind)
    report = worker().tick()
    assert report[2].handled >= 1 and report[2].failed == 0
    with factory() as s:
        row = s.get(GenerationTask, task)
        # A tick may also consume an already-due recovery wake-up after submission.
        # T10's worker test separately requires original-result reduction to SAVING.
        assert row.state in {"RUNNING", "SAVING"} and row.upstream_id
        assert row.settlement_state == "FROZEN"
    assert calls(upstream, task)["generation_intents"] == 1


def test_old_instance_retry_proof_cannot_authorize_new_generation(upstream):
    _, service, create, server, _ = upstream
    task = create("lost_response")
    submit(upstream, task)
    proof = service.collect_retry_evidence(task, kind="reliable_idempotency")
    server.simulator = Simulator()
    result = service.recover_original_task(task, proof)
    assert result.state == "INVESTIGATING"
    assert calls(upstream, task)["submit"] == 0


def test_forged_and_cross_task_evidence_rejected(upstream):
    _, service, create, _, _ = upstream
    from app.tasks.state_machine import SafeRetryEvidence, TransitionError

    first, second = create("lost_response"), create("lost_response")
    submit(upstream, first)
    submit(upstream, second)
    proof = service.collect_retry_evidence(first, kind="reliable_idempotency")
    forged = SafeRetryEvidence(PROTOCOL, "reliable_idempotency", str(uuid4()), "client", now())
    for invalid in (True, forged, proof):
        with pytest.raises(TransitionError, match="EVIDENCE"):
            service.recover_original_task(second, invalid)
    assert calls(upstream, second)["submit"] == 1


def test_proven_nonacceptance_is_persisted_and_bound(upstream):
    factory, service, create, _, _ = upstream
    task = create("proven_not_accepted")
    original = facts(factory, task)
    assert submit(upstream, task).state == "INVESTIGATING"
    proof = service.collect_retry_evidence(task, kind="proven_not_accepted")
    assert proof is not None
    assert service.recover_original_task(task, proof).state == "INVESTIGATING"
    assert calls(upstream, task)["submit"] == 2
    assert calls(upstream, task)["generation_intents"] == 0
    assert facts(factory, task) == original


def test_worker_composition_exists():
    from worker import main

    assert callable(getattr(main, "compose_worker", None)), "Worker has no upstream handlers"


@pytest.mark.parametrize("probe", ["unavailable", "new_instance"])
def test_retry_probe_failure_or_new_scope_cannot_replace_old_evidence(upstream, monkeypatch, probe):
    factory, service, create, server, _ = upstream
    task = create("lost_response")
    original = facts(factory, task)
    submit(upstream, task)
    proof = service.collect_retry_evidence(task, kind="reliable_idempotency")
    if probe == "new_instance":
        server.simulator = Simulator()
    else:
        monkeypatch.setattr(MockAgentAdapter, "retry_scope", lambda *_: None)
        with server.simulator.lock:
            next(iter(server.simulator.records.values()))["scenario"] = "not_found"
    assert service.collect_retry_evidence(task, kind="reliable_idempotency") is None
    assert service.recover_original_task(task, proof).state == "INVESTIGATING"
    assert calls(upstream, task)["submit"] == (0 if probe == "new_instance" else 1)
    assert facts(factory, task) == original


def test_instance_changes_between_probe_and_submit_is_rejected_at_server(upstream, monkeypatch):
    _, service, create, server, _ = upstream
    task = create("lost_response")
    submit(upstream, task)
    proof = service.collect_retry_evidence(task, kind="reliable_idempotency")
    with server.simulator.lock:
        next(iter(server.simulator.records.values()))["scenario"] = "not_found"
    real = MockAgentAdapter.submit_scoped

    def reboot(*args, **kwargs):
        server.simulator = Simulator()
        return real(*args, **kwargs)

    monkeypatch.setattr(MockAgentAdapter, "submit_scoped", reboot)
    assert service.recover_original_task(task, proof).state == "INVESTIGATING"
    assert calls(upstream, task)["submit"] == 0
    assert calls(upstream, task)["generation_intents"] == 0


def test_crash_after_response_before_observation_recovers_original(upstream, monkeypatch):
    factory, service, create, _, _ = upstream
    task = create()
    original = facts(factory, task)
    real = service._observe

    def crash(*args, **kwargs):
        raise SystemExit("TEST_ONLY response crash")

    monkeypatch.setattr(service, "_observe", crash)
    with pytest.raises(SystemExit):
        submit(upstream, task)
    monkeypatch.setattr(service, "_observe", real)
    assert service.recover_original_task(task).state == "RUNNING"
    assert calls(upstream, task)["submit"] == 1
    assert facts(factory, task) == original


def test_queued_task_with_old_intent_still_cannot_blind_submit(upstream):
    factory, _, create, _, worker = upstream
    task = create("lost_response")
    submit(upstream, task)
    server = upstream[3]
    with server.simulator.lock:
        next(iter(server.simulator.records.values()))["scenario"] = "not_found"
    with factory() as s, s.begin():
        row = s.get(GenerationTask, task)
        row.state, row.upstream_id = "QUEUED", None
        enqueue_outbox(s, task, "recover")
    assert worker().tick()[2].failed == 0
    assert calls(upstream, task)["submit"] == 1
    with factory() as s:
        assert s.get(GenerationTask, task).state == "INVESTIGATING"


def test_cross_external_identity_conflict_preserves_original_and_audit(upstream, monkeypatch):
    factory, service, create, _, _ = upstream
    first, second = create(), create("lost_response")
    submit(upstream, first)
    submit(upstream, second)
    with factory() as s, s.begin():
        original_id = s.get(GenerationTask, first).upstream_id
    from app.agents.contracts import QueryOutcome
    from app.agents.models import UpstreamEvidence

    real = MockAgentAdapter.query_by_external

    def cross(adapter, external):
        real(adapter, external)
        return QueryOutcome(
            status="FOUND",
            state="RUNNING",
            protocol_version=PROTOCOL,
            test_only=True,
            external_submission_id="wrong-external",
            upstream_task_id=original_id,
        )

    monkeypatch.setattr(MockAgentAdapter, "query_by_external", cross)
    assert service.recover_original_task(second).state == "INVESTIGATING"
    with factory() as s:
        assert s.get(GenerationTask, second).upstream_id is None
        assert (
            s.scalar(
                select(func.count())
                .select_from(UpstreamEvidence)
                .where(UpstreamEvidence.task_id == second, UpstreamEvidence.kind == "conflict")
            )
            == 1
        )
    assert calls(upstream, second)["submit"] == 1


def test_production_registry_cannot_accept_test_only_evidence(upstream):
    factory, service, create, _, _ = upstream
    task = create("lost_response")
    submit(upstream, task)
    proof = service.collect_retry_evidence(task, kind="reliable_idempotency")
    from app.agents.registry import AgentRegistry
    from app.agents.upstream import UpstreamService

    production = UpstreamService(factory, AgentRegistry(mode="production", test_only=False))
    with pytest.raises(LookupError, match="confirmed"):
        production.recover_original_task(task, proof)
    assert calls(upstream, task)["submit"] == 1


def test_attempt_and_evidence_are_database_immutable(upstream):
    factory, _, create, _, _ = upstream
    task = create()
    submit(upstream, task)
    from sqlalchemy.exc import DBAPIError

    for table in ("upstream_attempts", "upstream_evidence"):
        for statement in (
            f"UPDATE {table} SET kind='unsafe' WHERE task_id=:id"
            if table == "upstream_evidence"
            else f"UPDATE {table} SET wire_agent_id='video' WHERE task_id=:id",
            f"DELETE FROM {table} WHERE task_id=:id",
        ):
            with factory() as s, pytest.raises(DBAPIError, match="Immutable upstream provenance"):
                s.execute(text(statement), {"id": task})


def test_durable_accepted_response_recovers_when_later_query_is_unavailable(upstream, monkeypatch):
    _, service, create, _, _ = upstream
    task = create("query_unavailable")
    real = service._apply_observation

    def crash(*args, **kwargs):
        raise SystemExit("TEST_ONLY before binding")

    monkeypatch.setattr(service, "_apply_observation", crash)
    with pytest.raises(SystemExit):
        submit(upstream, task)
    monkeypatch.setattr(service, "_apply_observation", real)
    assert service.recover_original_task(task).state == "RUNNING"
    assert calls(upstream, task)["submit"] == 1


def test_network_calls_have_no_live_database_transaction(upstream, monkeypatch):
    factory, service, create, _, _ = upstream
    task = create("lost_response")
    engine = factory.kw["bind"]
    active = set()

    def begin(connection):
        active.add(connection)

    def end(connection):
        active.discard(connection)

    event.listen(engine, "begin", begin)
    event.listen(engine, "commit", end)
    event.listen(engine, "rollback", end)
    real = MockAgentAdapter._request

    def assert_boundary(*args, **kwargs):
        assert not active, "Network operation ran with a live database transaction"
        return real(*args, **kwargs)

    monkeypatch.setattr(MockAgentAdapter, "_request", assert_boundary)
    try:
        submit(upstream, task)
        # Re-entering submit for an existing intent must route recovery outside its read scope.
        submit(upstream, task)
        assert service.recover_original_task(task).state == "RUNNING"
    finally:
        event.remove(engine, "begin", begin)
        event.remove(engine, "commit", end)
        event.remove(engine, "rollback", end)


def test_future_absence_coverage_cannot_authorize_retry(upstream, monkeypatch):
    _, service, create, server, _ = upstream
    task = create("proven_not_accepted")
    real = server.simulator.proof

    def future(*args):
        proof = real(*args)
        proof["coverage_end"] += 3600
        proof["verified_at"] += 3600
        return proof

    monkeypatch.setattr(server.simulator, "proof", future)
    submit(upstream, task)
    from app.tasks.state_machine import TransitionError

    with pytest.raises(TransitionError, match="EVIDENCE"):
        service.collect_retry_evidence(task, kind="proven_not_accepted")
    assert calls(upstream, task)["submit"] == 1


def test_upstream_unique_binding_conflict_is_audited_without_overwriting(upstream, monkeypatch):
    factory, service, create, _, _ = upstream
    first = create()
    submit(upstream, first)
    with factory() as s:
        row = s.get(GenerationTask, first)
        agent_id, first_upstream = row.agent_id, row.upstream_id
    second = create("lost_response", agent_identity=agent_id)
    submit(upstream, second)
    from app.agents.contracts import QueryOutcome
    from app.agents.models import UpstreamEvidence

    def conflict(adapter, external):
        return QueryOutcome(
            status="FOUND",
            state="RUNNING",
            protocol_version=PROTOCOL,
            test_only=True,
            external_submission_id=external,
            upstream_task_id=first_upstream,
        )

    monkeypatch.setattr(MockAgentAdapter, "query_by_external", conflict)
    assert service.recover_original_task(second).state == "INVESTIGATING"
    with factory() as s:
        assert s.get(GenerationTask, first).upstream_id == first_upstream
        assert s.get(GenerationTask, first).state == "RUNNING"
        assert s.get(GenerationTask, second).upstream_id is None
        assert (
            s.scalar(
                select(func.count())
                .select_from(UpstreamEvidence)
                .where(UpstreamEvidence.task_id == second, UpstreamEvidence.kind == "conflict")
            )
            == 1
        )
    assert calls(upstream, second)["submit"] == 1


@pytest.mark.parametrize("initial_state", ["SUBMITTED", "QUEUED"])
def test_first_scope_failure_recovers_through_real_worker(upstream, monkeypatch, initial_state):
    factory, _, create, _, worker = upstream
    task = create()
    original = facts(factory, task)
    from app.agents.models import UpstreamAttempt

    real = MockAgentAdapter.retry_scope
    healthy = False

    def temporary_failure(adapter):
        return real(adapter) if healthy else None

    monkeypatch.setattr(MockAgentAdapter, "retry_scope", temporary_failure)
    with factory() as s, s.begin():
        s.get(GenerationTask, task).state = initial_state
    assert worker().tick()[2].failed == 0
    with factory() as s, s.begin():
        row = s.get(GenerationTask, task)
        assert row.state == initial_state
        assert row.investigation_reason == "UPSTREAM_SCOPE_UNCONFIRMED"
        assert (
            s.scalar(
                select(func.count())
                .select_from(UpstreamAttempt)
                .where(UpstreamAttempt.task_id == task)
            )
            == 0
        )
        row.recovery_due_at = s.scalar(text("SELECT UTC_TIMESTAMP(6)"))
    assert calls(upstream, task)["submit"] == 0
    healthy = True
    assert worker().tick()[2].failed == 0
    with factory() as s:
        assert s.get(GenerationTask, task).state == "RUNNING"
        assert (
            s.scalar(
                select(func.count())
                .select_from(UpstreamAttempt)
                .where(UpstreamAttempt.task_id == task)
            )
            == 1
        )
    assert calls(upstream, task)["submit"] == 1
    assert calls(upstream, task)["generation_intents"] == 1
    assert facts(factory, task) == original


@pytest.mark.parametrize("clock_offset", [-30, 30])
def test_absence_proof_uses_protocol_order_not_database_wall_clock(
    upstream, monkeypatch, clock_offset
):
    import time
    from types import SimpleNamespace

    from app.agents import mock_server

    _, service, create, server, _ = upstream
    monkeypatch.setattr(
        mock_server,
        "time",
        SimpleNamespace(time=lambda: time.time() + clock_offset, monotonic=time.monotonic),
    )
    server.simulator = Simulator()
    task = create("proven_not_accepted")
    assert submit(upstream, task).state == "INVESTIGATING"
    proof = service.collect_retry_evidence(task, kind="proven_not_accepted")
    assert proof is not None
    assert service.recover_original_task(task, proof).state == "INVESTIGATING"
    assert calls(upstream, task)["submit"] == 2
    assert calls(upstream, task)["generation_intents"] == 0


def test_absence_proof_survives_mysql_json_numeric_roundtrip(upstream, monkeypatch):
    import time
    from types import SimpleNamespace

    from app.agents import mock_server

    _, service, create, server, _ = upstream
    # This exact double changes by 1 ULP when MySQL serializes JSON (diagnosed separately).
    monkeypatch.setattr(
        mock_server,
        "time",
        SimpleNamespace(time=lambda: 1791735933.4548957, monotonic=time.monotonic),
    )
    server.simulator = Simulator()
    task = create("proven_not_accepted")
    assert submit(upstream, task).state == "INVESTIGATING"
    proof = service.collect_retry_evidence(task, kind="proven_not_accepted")
    assert proof is not None
    assert service.recover_original_task(task, proof).state == "INVESTIGATING"
    assert calls(upstream, task)["submit"] == 2


@pytest.mark.parametrize(
    "fault",
    [
        "missing_sequence",
        "wrong_instance",
        "insufficient_sequence",
        "future_sequence",
        "wrong_source",
        "fractional_clock",
    ],
)
def test_invalid_protocol_absence_cannot_authorize_retry(upstream, monkeypatch, fault):
    _, service, create, server, _ = upstream
    task = create("proven_not_accepted")
    submit(upstream, task)
    real = server.simulator.proof

    def invalid(*args):
        value = real(*args)
        if fault == "missing_sequence":
            value.pop("coverage_end_sequence")
        elif fault == "wrong_instance":
            value["scope_instance_id"] = str(uuid4())
        elif fault == "insufficient_sequence":
            value["coverage_end_sequence"] = value["verified_sequence"] = 0
        elif fault == "future_sequence":
            value["coverage_end_sequence"] = value["verified_sequence"] = 2**52
        elif fault == "wrong_source":
            value["verified_by"] = "TEST_ONLY.client_claim"
        elif fault == "fractional_clock":
            value["coverage_end"] += 0.5
        return value

    monkeypatch.setattr(server.simulator, "proof", invalid)
    from app.tasks.state_machine import TransitionError

    try:
        proof = service.collect_retry_evidence(task, kind="proven_not_accepted")
    except TransitionError as error:
        assert str(error) == "EVIDENCE_REQUIRED"
    else:
        assert proof is None
    assert calls(upstream, task)["submit"] == 1


def test_absence_query_cannot_cover_unknown_inflight_submission(upstream):
    _, service, create, server, _ = upstream
    task = create("lost_response")
    submit(upstream, task)
    with server.simulator.lock:
        # Deliberately inconsistent upstream query cannot replace the absent submit reply.
        next(iter(server.simulator.records.values()))["scenario"] = "proven_not_accepted"
    from app.tasks.state_machine import TransitionError

    with pytest.raises(TransitionError, match="EVIDENCE_REQUIRED"):
        service.collect_retry_evidence(task, kind="proven_not_accepted")
    assert calls(upstream, task)["submit"] == 1
    assert calls(upstream, task)["generation_intents"] == 1
