"""Every publication write rolls back as one unit; original durable bytes survive."""

import re

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session

from app.ledger.models import CreditAccount, CreditLedger
from app.tasks.models import GenerationTask
from tests.faults.test_result_persistence import ready as ready_fixture
from tests.faults.test_upstream_recovery import calls
from tests.integration.test_settlement import assert_facts, publisher
from tests.t12_fixtures import upstream as upstream_fixture

ready = ready_fixture
upstream = upstream_fixture

WRITE_POINTS = [
    "INSERT INTO messages",
    "INSERT INTO works",
    "INSERT INTO work_items",
    "INSERT INTO file_refs",
    "UPDATE credit_accounts",
    "UPDATE credit_reservations",
    "INSERT INTO credit_ledger",
    "UPDATE storage_accounts",
    "UPDATE storage_pools",
    "UPDATE capacity_reservations",
    "UPDATE generation_tasks",
    "UPDATE generation_tasks CAS",
    "INSERT INTO task_state_events",
    "INSERT INTO durable_events",
]


@pytest.mark.parametrize("point", WRITE_POINTS + ["before_commit", "after_commit"])
def test_each_publish_write_interruption(upstream, ready, tmp_path, point):
    from app.conversations.models import Message
    from app.works.models import Work

    task = ready(count=2)
    service = publisher(upstream, tmp_path)
    delivery = service.persistence.save_original(task)
    before = calls(upstream, task)
    fired = []
    engine = upstream[0].kw["bind"]

    armed = []

    def write_fault(conn, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO messages"):
            armed.append(True)
        matches = bool(re.match(re.escape(point) + r"\b", statement, re.I))
        if point == "UPDATE generation_tasks CAS":
            matches = statement.startswith("UPDATE generation_tasks SET ") and bool(
                re.search(r"\bstate_version\s*=", statement.split(" WHERE ")[0])
            )
        if armed and matches and not fired:
            fired.append(point)
            raise RuntimeError("TEST_ONLY publication interrupted " + point)

    def mark(s, *_):
        if any(isinstance(x, Message) and x.task_id == task for x in s.new):
            s.info["t12_publication"] = True

    def commit_fault(s):
        if s.info.get("t12_publication") and not fired:
            fired.append(point)
            raise RuntimeError("TEST_ONLY publication interrupted " + point)

    if point in ("before_commit", "after_commit"):
        event.listen(Session, "before_flush", mark)
        event.listen(Session, point, commit_fault)
    else:
        event.listen(engine, "after_cursor_execute", write_fault)
    try:
        if point == "after_commit":
            assert service.run(task).state == "SUCCEEDED"
        else:
            with pytest.raises(RuntimeError, match="publication interrupted"):
                service.run(task)
    finally:
        if point in ("before_commit", "after_commit"):
            event.remove(Session, "before_flush", mark)
            event.remove(Session, point, commit_fault)
        else:
            event.remove(engine, "after_cursor_execute", write_fault)
    assert fired == [point]
    if point != "after_commit":
        with upstream[0]() as s:
            row = s.get(GenerationTask, task)
            assert row.state == "SAVING" and row.settlement_state == "FROZEN"
            assert s.get(CreditAccount, row.user_id).frozen == 30
            assert not s.scalars(select(Work).where(Work.task_id == task)).all()
            assert not s.scalars(
                select(Message).where(Message.task_id == task, Message.kind == "final")
            ).all()
            assert not s.scalars(
                select(CreditLedger).where(
                    CreditLedger.task_id == task, CreditLedger.kind == "consume"
                )
            ).all()
    assert len(list(tmp_path.rglob("*.blob"))) == 2
    assert service.run(task).state == "SUCCEEDED"
    final = assert_facts(upstream, task)
    assert final["manifest"] == delivery.manifest_id
    assert calls(upstream, task) == before
    print("T12_FAULT_RECOVERED", point, final)


def test_worker_failure_ack_still_recovers_from_database(
    upstream, ready, tmp_path, redis_namespace
):
    from app.storage.local_store import LocalStore
    from app.works.models import Work
    from worker.main import compose_worker

    task = ready(count=2)
    redis, prefix = redis_namespace
    worker = compose_worker(
        upstream[0],
        redis,
        prefix + "worker",
        "workers",
        "t12",
        registry=upstream[1].registry,
        task_ids=[task],
        store=LocalStore(tmp_path),
    )

    def fail(mapper, connection, target):
        raise RuntimeError("TEST_ONLY worker publication fails")

    event.listen(Work, "after_insert", fail)
    try:
        assert worker.tick()[2].failed >= 1
    finally:
        event.remove(Work, "after_insert", fail)
    before = calls(upstream, task)
    with upstream[0]() as s, s.begin():
        row = s.get(GenerationTask, task)
        assert row.state == "SAVING" and row.settlement_state == "FROZEN"
        s.execute(
            text("UPDATE generation_tasks SET recovery_due_at=UTC_TIMESTAMP(6) WHERE id=:id"),
            {"id": task},
        )
    redis.delete(prefix + "worker")
    assert worker.tick()[2].failed == 0
    assert_facts(upstream, task)
    assert calls(upstream, task) == before


def test_blob_corruption_never_charges(upstream, ready, tmp_path):
    task = ready(count=2)
    service = publisher(upstream, tmp_path)
    assert service.persistence.save_original(task)
    blob = next(tmp_path.rglob("*.blob"))
    blob.write_bytes(b"TEST_ONLY corrupt")
    before = calls(upstream, task)
    assert service.run(task) is None
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        assert row.state == "SAVE_RECOVERY" and row.settlement_state == "FROZEN"
    assert blob.read_bytes() == b"TEST_ONLY corrupt"
    assert calls(upstream, task) == before


def test_caller_rollback_and_stale_fencing(upstream, ready, tmp_path):
    from app.results.publisher import publish_and_settle
    from app.tasks.state_machine import TransitionError
    from app.works.models import Work

    task = ready(count=2)
    service = publisher(upstream, tmp_path)
    lease = service.leases.claim_task(task, "t12-owned")
    prepared = service.prepare(task, lease=lease)
    with upstream[0]() as s:
        version = s.get(GenerationTask, task).state_version
    try:
        with upstream[0]() as s:
            service.install_verifiers(s, prepared)
            assert (
                publish_and_settle(s, task, prepared.delivery.manifest_id, version).state
                == "SUCCEEDED"
            )
            s.rollback()
        with upstream[0]() as s:
            assert s.get(GenerationTask, task).state == "SAVING"
            assert not s.scalar(select(Work).where(Work.task_id == task))
        with upstream[0]() as s, s.begin():
            s.execute(
                text(
                    "UPDATE generation_tasks SET lease_expires_at="
                    "UTC_TIMESTAMP(6)-INTERVAL 1 SECOND "
                    "WHERE id=:id"
                ),
                {"id": task},
            )
        with upstream[0]() as s, s.begin():
            service.install_verifiers(s, prepared)
            with pytest.raises(TransitionError, match="LEASE_LOST"):
                publish_and_settle(s, task, prepared.delivery.manifest_id, version)
        assert service.run(task).state == "SUCCEEDED"
    finally:
        service.leases.release(lease)


@pytest.mark.parametrize("phase", ["before_commit", "after_commit"])
def test_actual_worker_commit_uncertainty(upstream, ready, tmp_path, redis_namespace, phase):
    from app.conversations.models import Message
    from app.storage.local_store import LocalStore
    from worker.main import compose_worker

    task = ready(count=2)
    redis, prefix = redis_namespace
    worker = compose_worker(
        upstream[0],
        redis,
        prefix + "uncertain",
        "workers",
        "t12",
        registry=upstream[1].registry,
        task_ids=[task],
        store=LocalStore(tmp_path),
    )
    fired = []

    def mark(s, *_):
        if any(isinstance(x, Message) and x.task_id == task for x in s.new):
            s.info["t12_uncertain"] = True

    def fail(s):
        if s.info.get("t12_uncertain") and not fired:
            fired.append(True)
            raise RuntimeError("TEST_ONLY commit uncertainty")

    event.listen(Session, "before_flush", mark)
    event.listen(Session, phase, fail)
    try:
        outcome = worker.tick()[2]
        assert outcome.failed == (1 if phase == "before_commit" else 0)
    finally:
        event.remove(Session, "before_flush", mark)
        event.remove(Session, phase, fail)
    assert fired
    before = calls(upstream, task)
    if phase == "before_commit":
        with upstream[0]() as s, s.begin():
            s.execute(
                text("UPDATE generation_tasks SET recovery_due_at=UTC_TIMESTAMP(6) WHERE id=:id"),
                {"id": task},
            )
        assert worker.tick()[2].failed == 0
    assert_facts(upstream, task)
    assert publisher(upstream, tmp_path).run(task).state == "SUCCEEDED"
    assert calls(upstream, task) == before
