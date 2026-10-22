"""T08 crash recovery on real MySQL and isolated Redis keys."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.auth.models import User
from app.dispatch.models import OutboxEvent
from app.dispatch.outbox import enqueue_outbox
from app.dispatch.recovery import database_now
from app.events.models import DurableEvent
from app.ledger.models import CreditAccount, CreditLedger, CreditReservation
from app.ledger.service import freeze_credits, now
from app.tasks.models import GenerationTask, TaskSnapshot, TaskStateEvent


@pytest.fixture
def task_factory(mysql_engine, ledger_task):
    def create(state="SUBMITTED", upstream_id=None):
        task_id, user_id = str(uuid4()), str(uuid4())
        with Session(mysql_engine) as s, s.begin():
            s.add(
                User(
                    id=user_id,
                    account_normalized="t08_" + uuid4().hex,
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
            task = ledger_task(s, user_id, task_id)
            freeze_credits(s, user_id, task_id, 30)
            task.state, task.upstream_id = state, upstream_id
            s.add(
                TaskStateEvent(
                    id=str(uuid4()),
                    task_id=task_id,
                    user_id=user_id,
                    state_version=1,
                    from_state=None,
                    to_state=state,
                    evidence={"fixture": "TEST_ONLY"},
                    created_at=now(),
                )
            )
            enqueue_outbox(s, task_id, "submit")
        create.task_ids.append(task_id)
        return task_id

    create.task_ids = []
    return create


@pytest.fixture
def runtime(mysql_engine, redis_namespace, task_factory):
    from app.dispatch.consumer import TaskConsumer
    from app.dispatch.outbox import OutboxDispatcher
    from app.dispatch.recovery import RecoveryScheduler

    redis, prefix = redis_namespace
    factory = sessionmaker(mysql_engine, expire_on_commit=False)
    stream = prefix + "dispatch"
    return (
        factory,
        redis,
        stream,
        OutboxDispatcher(factory, redis, stream, task_ids=task_factory.task_ids),
        RecoveryScheduler(factory, task_ids=task_factory.task_ids),
        TaskConsumer(factory, redis, stream, "workers", "worker-a"),
    )


def facts(factory, task_id):
    with factory() as s:
        task = s.get(GenerationTask, task_id)
        snap = s.get(TaskSnapshot, task_id)
        return (
            task.id,
            task.external_submission_id,
            snap.input_snapshot,
            snap.quote,
            s.scalar(
                select(func.count())
                .select_from(CreditLedger)
                .where(CreditLedger.task_id == task_id, CreditLedger.kind == "freeze")
            ),
            s.scalar(select(CreditReservation.state).where(CreditReservation.task_id == task_id)),
        )


@pytest.mark.parametrize("host_offset_seconds", [-30, 30])
def test_initial_outbox_is_immediately_due_despite_host_clock_skew(
    task_factory, runtime, monkeypatch, host_offset_seconds
):
    from app.ledger import service

    class SkewedHostDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz) + timedelta(seconds=host_offset_seconds)

    monkeypatch.setattr(service, "datetime", SkewedHostDatetime)
    factory, redis, stream, dispatcher, _, _ = runtime
    with factory() as s:
        before = database_now(s)
    task_id = task_factory()
    original = facts(factory, task_id)
    with factory() as s:
        row = s.scalar(select(OutboxEvent).where(OutboxEvent.task_id == task_id))
        # Immediate admission uses the same clock as dispatch, in either skew direction.
        assert before <= row.ready_at <= database_now(s)
    assert dispatcher.dispatch_pending(1000).dispatched == 1
    records = redis.xrange(stream)
    assert len(records) == 1
    assert records[0][1][b"task_id"].decode() == task_id
    assert facts(factory, task_id) == original


def test_commit_then_redis_failure(task_factory, runtime):
    factory, redis, stream, dispatcher, _, _ = runtime
    task_id = task_factory()
    original = facts(factory, task_id)
    # Real Redis WRONGTYPE: only this test's owned random stream key is affected.
    redis.set(stream, "TEST_ONLY fault")
    report = dispatcher.dispatch_pending(1000)
    assert report.failed >= 1
    with factory() as s:
        row = s.scalar(select(OutboxEvent).where(OutboxEvent.task_id == task_id))
        assert row.dispatched_at is None
        assert row.attempts == 1
    redis.delete(stream)
    assert dispatcher.dispatch_pending(1000).dispatched >= 1
    assert any(fields[b"task_id"].decode() == task_id for _, fields in redis.xrange(stream))
    assert facts(factory, task_id) == original


def test_stream_deleted_ack_then_crash(task_factory, runtime):
    factory, redis, stream, dispatcher, scheduler, consumer = runtime
    task_id = task_factory("SUBMITTING")
    original = facts(factory, task_id)
    dispatcher.dispatch_pending(1000)
    consumer.ensure_group()
    messages = redis.xreadgroup("workers", "crashing-worker", {stream: ">"}, count=1000)
    for _, items in messages:
        for message_id, _ in items:
            redis.xack(stream, "workers", message_id)
    redis.delete(stream)
    report = scheduler.recover_due_tasks(now(), batch_size=1000)
    assert task_id in report.scheduled
    assert dispatcher.dispatch_pending(1000).dispatched >= 1
    assert any(fields[b"task_id"].decode() == task_id for _, fields in redis.xrange(stream))
    # Stream/group recreation and absent handlers must preserve unknown acceptance.
    result = consumer.consume_once(1000)
    assert result.unhandled >= 1
    with factory() as s:
        assert s.get(GenerationTask, task_id).state == "SUBMITTING"
    assert facts(factory, task_id) == original


def test_two_workers_fencing(task_factory, runtime):
    from app.dispatch.consumer import LeaseManager
    from app.tasks.state_machine import TransitionError, TransitionEvidence, transition_task

    factory, _, _, _, _, _ = runtime
    task_id = task_factory()
    manager = LeaseManager(factory)
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda worker: manager.claim_task(task_id, worker), ["a", "b"]))
    winners = [lease for lease in claims if lease is not None]
    assert len(winners) == 1
    old = winners[0]
    with factory() as s, s.begin():
        s.execute(
            text(
                "UPDATE generation_tasks SET lease_expires_at=UTC_TIMESTAMP(6) "
                "- INTERVAL 1 SECOND WHERE id=:id"
            ),
            {"id": task_id},
        )
    new = manager.claim_task(task_id, "replacement")
    assert new.fencing_token > old.fencing_token
    with factory() as s, s.begin():
        with pytest.raises(TransitionError, match="LEASE_LOST"):
            transition_task(s, task_id, 1, "QUEUED", TransitionEvidence(old))
    with factory() as s, s.begin():
        receipt = transition_task(s, task_id, 1, "QUEUED", TransitionEvidence(new))
        assert receipt.state_version == 2
    with factory() as s, s.begin():
        with pytest.raises(TransitionError, match="VERSION_CONFLICT"):
            transition_task(s, task_id, 1, "SUBMITTING", TransitionEvidence(new))
    with factory() as s:
        assert (
            s.scalar(
                select(func.count())
                .select_from(TaskStateEvent)
                .where(TaskStateEvent.task_id == task_id)
            )
            == 2
        )
        assert (
            s.scalar(
                select(func.count())
                .select_from(DurableEvent)
                .where(DurableEvent.task_id == task_id)
            )
            == 1
        )


def test_saving_no_regression(task_factory, runtime):
    from app.dispatch.consumer import LeaseManager
    from app.dispatch.recovery import recovery_action
    from app.tasks.state_machine import TransitionError, TransitionEvidence, transition_task

    factory, _, _, _, scheduler, _ = runtime
    task_id = task_factory("SAVING", "TEST_ONLY_original")
    original = facts(factory, task_id)
    lease = LeaseManager(factory).claim_task(task_id, "saving-worker")
    assert lease is not None
    with factory() as s, s.begin():
        with pytest.raises(TransitionError, match="INVALID_TRANSITION"):
            transition_task(s, task_id, 1, "RUNNING", TransitionEvidence(lease))
        assert recovery_action(s.get(GenerationTask, task_id)) == "save_original"
    with factory() as s, s.begin():
        with pytest.raises(TransitionError, match="EVIDENCE_REQUIRED"):
            transition_task(s, task_id, 1, "SUCCEEDED", TransitionEvidence(lease))
    assert task_id not in scheduler.recover_due_tasks(now() + timedelta(days=1000), 1000).scheduled
    with factory() as s:
        assert s.get(GenerationTask, task_id).state == "SAVING"
    assert facts(factory, task_id) == original


def test_transition_rollback_is_atomic(task_factory, runtime):
    from app.dispatch.consumer import LeaseManager
    from app.tasks.state_machine import TransitionEvidence, transition_task

    factory = runtime[0]
    task_id = task_factory()
    lease = LeaseManager(factory).claim_task(task_id, "rollback-worker")
    with pytest.raises(RuntimeError, match="TEST_ONLY crash"):
        with factory() as s, s.begin():
            transition_task(s, task_id, 1, "QUEUED", TransitionEvidence(lease))
            raise RuntimeError("TEST_ONLY crash")
    with factory() as s:
        task = s.get(GenerationTask, task_id)
        assert (task.state, task.state_version) == ("SUBMITTED", 1)
        assert (
            s.scalar(
                select(func.count())
                .select_from(TaskStateEvent)
                .where(TaskStateEvent.task_id == task_id)
            )
            == 1
        )
        assert (
            s.scalar(
                select(func.count())
                .select_from(DurableEvent)
                .where(DurableEvent.task_id == task_id)
            )
            == 0
        )
        assert (
            s.scalar(
                select(func.count()).select_from(OutboxEvent).where(OutboxEvent.task_id == task_id)
            )
            == 1
        )


def test_lease_renewal_and_expiration_are_fenced(task_factory, runtime):
    from app.dispatch.consumer import LeaseManager
    from app.tasks.state_machine import TransitionError, TransitionEvidence, transition_task

    factory = runtime[0]
    task_id = task_factory()
    leases = LeaseManager(factory)
    first = leases.claim_task(task_id, "first")
    renewed = leases.renew(first)
    assert renewed.expires_at >= first.expires_at
    with factory() as s, s.begin():
        s.execute(
            text(
                "UPDATE generation_tasks SET lease_expires_at=UTC_TIMESTAMP(6) "
                "- INTERVAL 1 SECOND WHERE id=:id"
            ),
            {"id": task_id},
        )
    assert leases.renew(first) is None
    assert not leases.release(first)
    with factory() as s, s.begin():
        with pytest.raises(TransitionError, match="LEASE_LOST"):
            transition_task(s, task_id, 1, "QUEUED", TransitionEvidence(first))
    replacement = leases.claim_task(task_id, "replacement")
    assert replacement.fencing_token > first.fencing_token
    assert not leases.release(first)
    assert leases.renew(replacement) is not None


@pytest.mark.parametrize(
    "state,target",
    [
        ("SUBMITTING", "RUNNING"),
        ("SUBMITTING", "SAVING"),
        ("INVESTIGATING", "SUBMITTING"),
        ("INVESTIGATING", "QUEUED"),
        ("INVESTIGATING", "FAILED"),
        ("SAVE_RECOVERY", "MANUALLY_CLOSED"),
        ("SAVE_RECOVERY", "SAVING"),
        ("SAVING", "SUCCEEDED"),
    ],
)
def test_unverified_evidence_cannot_advance(task_factory, runtime, state, target):
    from app.dispatch.consumer import LeaseManager
    from app.tasks.state_machine import TransitionError, TransitionEvidence, transition_task

    factory = runtime[0]
    task_id = task_factory(state)
    original = facts(factory, task_id)
    lease = LeaseManager(factory).claim_task(task_id, "proof-worker")
    with factory() as s, s.begin():
        with pytest.raises(TransitionError, match="EVIDENCE_REQUIRED"):
            transition_task(
                s,
                task_id,
                1,
                target,
                TransitionEvidence(lease, "TEST_ONLY_404_timeout_or_deadline"),
            )
    assert facts(factory, task_id) == original
    with factory() as s:
        assert (
            s.get(GenerationTask, task_id).state,
            s.get(GenerationTask, task_id).state_version,
        ) == (state, 1)


@pytest.mark.parametrize("state", ["SUCCEEDED", "FAILED", "MANUALLY_CLOSED"])
def test_terminal_tasks_are_not_reclaimed(task_factory, runtime, state):
    from app.dispatch.consumer import LeaseManager

    factory, _, _, _, scheduler, _ = runtime
    task_id = task_factory(state)
    assert LeaseManager(factory).claim_task(task_id, "late") is None
    assert task_id not in scheduler.recover_due_tasks(batch_size=1000).scheduled


def test_duplicate_message_rechecks_stage_and_handler_runs_outside_locks(task_factory, runtime):
    from app.tasks.state_machine import TransitionEvidence, transition_task

    factory, redis, stream, dispatcher, _, consumer = runtime
    task_id = task_factory()
    original = facts(factory, task_id)
    dispatcher.dispatch_pending(1000)
    for _, fields in redis.xrange(stream):
        redis.xadd(stream, fields)

    def prepare(context):
        with factory() as s, s.begin():
            s.execute(text("SET SESSION innodb_lock_wait_timeout=1"))
            receipt = transition_task(
                s,
                context.task_id,
                context.state_version,
                "SUBMITTING",
                TransitionEvidence(context.lease),
            )
            assert receipt.state_version == 2

    consumer.handlers["prepare_submission"] = prepare
    report = consumer.consume_once(1000)
    assert (report.handled, report.rejected, report.failed) == (1, 1, 0)
    with factory() as s:
        assert s.get(GenerationTask, task_id).state == "SUBMITTING"
    assert facts(factory, task_id) == original


def test_cross_task_message_cannot_claim(task_factory, runtime):
    factory, redis, stream, dispatcher, _, consumer = runtime
    first, second = task_factory(), task_factory()
    dispatcher.dispatch_pending(1000)
    fields = next(
        fields for _, fields in redis.xrange(stream) if fields[b"task_id"].decode() == first
    )
    fields[b"task_id"] = second.encode()
    assert consumer.process_message(fields) == "rejected"
    with factory() as s:
        assert s.get(GenerationTask, second).fencing_token == 0


def test_same_generation_duplicates_query_once_and_next_generation_recovers(task_factory, runtime):
    factory, redis, stream, dispatcher, scheduler, consumer = runtime
    task_id = task_factory("RUNNING", "TEST_ONLY_original")
    # Recovery supersedes the fixture's admission hint at this task version.
    assert task_id in scheduler.recover_due_tasks().scheduled
    assert dispatcher.dispatch_pending().dispatched == 1
    fields = redis.xrange(stream)[0][1]
    seen = []
    consumer.handlers["query_original"] = seen.append
    assert consumer.process_message(fields) == "handled"
    assert consumer.process_message(fields) == "rejected"
    assert len(seen) == 1
    assert task_id not in scheduler.recover_due_tasks().scheduled
    with factory() as s, s.begin():
        s.get(GenerationTask, task_id).recovery_due_at = database_now(s) - timedelta(seconds=1)
    assert task_id in scheduler.recover_due_tasks().scheduled
    assert consumer.process_message(fields) == "rejected"
    assert dispatcher.dispatch_pending().dispatched == 1
    fresh_fields = redis.xrange(stream)[-1][1]
    assert fresh_fields[b"event_id"] == fields[b"event_id"]
    assert int(fresh_fields[b"dispatch_generation"]) > int(fields[b"dispatch_generation"])
    assert consumer.process_message(fresh_fields) == "handled"
    assert len(seen) == 2


def test_two_dispatch_claimers_spend_one_generation(task_factory, runtime):
    factory, redis, stream, dispatcher, _, consumer = runtime
    task_id = task_factory()
    dispatcher.dispatch_pending()
    fields = redis.xrange(stream)[0][1]
    event_id = fields[b"event_id"].decode()
    generation = int(fields[b"dispatch_generation"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(
            lambda worker: consumer.leases.claim_dispatch(task_id, worker, event_id, 1, generation),
            ["one", "two"],
        ))
    from app.dispatch.consumer import Lease

    assert sum(isinstance(claim, Lease) for claim in claims) == 1
    with factory() as s:
        assert s.get(OutboxEvent, event_id).claimed_generation == generation
        assert s.get(GenerationTask, task_id).fencing_token == 1


@pytest.mark.parametrize("reason", ["UPSTREAM_NEEDS_INPUT", "CALLBACK_EVENT_CONFLICT"])
def test_manual_wait_is_not_rearmed(task_factory, runtime, reason):
    factory, _, _, _, scheduler, _ = runtime
    task_id = task_factory("INVESTIGATING", "TEST_ONLY_original")
    with factory() as s, s.begin():
        s.get(GenerationTask, task_id).investigation_reason = reason
    assert task_id not in scheduler.recover_due_tasks().scheduled


def test_future_generation_and_legacy_message_wait_for_scheduler(task_factory, runtime):
    from app.dispatch.outbox import rearm_outbox

    factory, redis, stream, dispatcher, scheduler, consumer = runtime
    task_id = task_factory()
    dispatcher.dispatch_pending()
    old = redis.xrange(stream)[0][1]
    legacy = {key: value for key, value in old.items() if key != b"dispatch_generation"}
    assert consumer.process_message(legacy) == "rejected"
    with factory() as s, s.begin():
        event = rearm_outbox(s, task_id, "submit",
                             ready_at=database_now(s) + timedelta(seconds=60))
        future = dict(old, dispatch_generation=str(event.dispatch_generation))
        future.pop(b"dispatch_generation")
    assert consumer.process_message(future) == "busy"
    assert consumer.process_message(old) == "rejected"
    assert task_id not in scheduler.recover_due_tasks().scheduled
    with factory() as s, s.begin():
        row = s.get(OutboxEvent, old[b"event_id"].decode())
        row.ready_at = database_now(s) - timedelta(seconds=1)
    assert task_id in scheduler.recover_due_tasks().scheduled
    assert dispatcher.dispatch_pending().dispatched == 1
    assert consumer.process_message(redis.xrange(stream)[-1][1]) == "unhandled"


def test_obsolete_future_operation_cannot_starve_current_stage(task_factory, runtime):
    factory, _, _, _, scheduler, _ = runtime
    task_id = task_factory("SAVING", "TEST_ONLY_original")
    with factory() as s, s.begin():
        stale = s.scalar(select(OutboxEvent).where(OutboxEvent.task_id == task_id))
        stale.ready_at = database_now(s) + timedelta(days=1)
    assert task_id in scheduler.recover_due_tasks().scheduled
    with factory() as s:
        current = s.scalar(select(OutboxEvent).where(
            OutboxEvent.task_id == task_id, OutboxEvent.operation == "save"))
        assert current.ready_at <= database_now(s)


def test_dispatch_mark_cannot_hide_a_concurrently_rearmed_generation(
    task_factory, runtime, monkeypatch
):
    from app.dispatch.outbox import rearm_outbox

    factory, redis, stream, dispatcher, _, consumer = runtime
    task_id = task_factory()
    original_xadd = redis.xadd

    def rearm_after_send(*args, **kwargs):
        result = original_xadd(*args, **kwargs)
        with factory() as s, s.begin():
            rearm_outbox(s, task_id, "submit")
        return result

    monkeypatch.setattr(redis, "xadd", rearm_after_send)
    assert dispatcher.dispatch_pending().dispatched == 1
    stale = redis.xrange(stream)[0][1]
    with factory() as s:
        row = s.get(OutboxEvent, stale[b"event_id"].decode())
        assert row.dispatched_at is None
        assert row.dispatch_generation == int(stale[b"dispatch_generation"]) + 1
    assert consumer.process_message(stale) == "rejected"
    monkeypatch.setattr(redis, "xadd", original_xadd)
    assert dispatcher.dispatch_pending().dispatched == 1
    assert consumer.process_message(redis.xrange(stream)[-1][1]) == "unhandled"


def test_redis_success_then_db_mark_crash_replays_same_intent(task_factory, runtime):
    from sqlalchemy import event

    factory, redis, stream, dispatcher, _, _ = runtime
    task_id = task_factory()
    original = facts(factory, task_id)
    engine = factory.kw["bind"]

    def fail_mark(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE dispatch_outbox SET dispatched_at"):
            raise RuntimeError("TEST_ONLY dispatcher crash")

    event.listen(engine, "before_cursor_execute", fail_mark)
    try:
        with pytest.raises(RuntimeError, match="TEST_ONLY dispatcher crash"):
            dispatcher.dispatch_pending(1000)
    finally:
        event.remove(engine, "before_cursor_execute", fail_mark)
    assert redis.xlen(stream) == 1
    assert dispatcher.dispatch_pending(1000).dispatched == 1
    records = redis.xrange(stream)
    assert records[0][1] == records[1][1]
    assert facts(factory, task_id) == original


def test_boolean_and_cross_identity_publication_proofs_are_rejected(task_factory, runtime):
    from app.dispatch.consumer import LeaseManager
    from app.tasks.state_machine import (
        TransitionError,
        TransitionEvidence,
        TransitionVerifiers,
        VerifiedTransition,
        transition_task,
    )

    factory = runtime[0]
    task_id = task_factory("SAVING")
    lease = LeaseManager(factory).claim_task(task_id, "publisher")
    with factory() as s, s.begin():
        s.info["transition_verifiers"] = TransitionVerifiers({"publication": lambda *args: True})
        with pytest.raises(TransitionError, match="EVIDENCE_MISMATCH"):
            transition_task(
                s, task_id, 1, "SUCCEEDED", TransitionEvidence(lease, "TEST_ONLY_proof")
            )
        task = s.get(GenerationTask, task_id)

        def wrong_identity(*args):
            return VerifiedTransition(
                str(uuid4()),
                task.agent_id,
                task.agent_version,
                task.external_submission_id,
                "publication",
                "TEST_ONLY_proof",
                "TEST_ONLY_protocol",
            )

        s.info["transition_verifiers"] = TransitionVerifiers({"publication": wrong_identity})
        with pytest.raises(TransitionError, match="EVIDENCE_MISMATCH"):
            transition_task(
                s, task_id, 1, "SUCCEEDED", TransitionEvidence(lease, "TEST_ONLY_proof")
            )

        def valid_identity(*args):
            return VerifiedTransition(
                task.id,
                task.agent_id,
                task.agent_version,
                task.external_submission_id,
                "publication",
                "TEST_ONLY_proof",
                "TEST_ONLY_protocol",
            )

        s.info["transition_verifiers"] = TransitionVerifiers({"publication": valid_identity})
        with pytest.raises(TransitionError, match="SETTLEMENT_REQUIRED"):
            transition_task(
                s, task_id, 1, "SUCCEEDED", TransitionEvidence(lease, "TEST_ONLY_proof")
            )


def test_worker_tick_preserves_task_when_handlers_missing(task_factory, runtime):
    from worker.main import Worker

    factory, redis, stream, dispatcher, scheduler, consumer = runtime
    task_id = task_factory("SUBMITTING")
    original = facts(factory, task_id)
    result = Worker(dispatcher, scheduler, consumer).tick()
    assert result[2].unhandled >= 1
    assert facts(factory, task_id) == original
    with factory() as s:
        assert s.get(GenerationTask, task_id).state == "SUBMITTING"


def test_safe_retry_requires_protocol_basis_and_preserves_original(task_factory, runtime):
    from app.dispatch.consumer import LeaseManager
    from app.tasks.state_machine import (
        TransitionError,
        TransitionEvidence,
        TransitionVerifiers,
        VerifiedTransition,
        transition_task,
    )

    factory = runtime[0]
    task_id = task_factory("INVESTIGATING")
    lease = LeaseManager(factory).claim_task(task_id, "retry-worker")
    original = facts(factory, task_id)
    with factory() as s, s.begin():
        task = s.get(GenerationTask, task_id)

        def insufficient(*args):
            return VerifiedTransition(
                task.id,
                task.agent_id,
                task.agent_version,
                task.external_submission_id,
                "safe_retry",
                "TEST_ONLY_proof",
                "TEST_ONLY_protocol",
            )

        s.info["transition_verifiers"] = TransitionVerifiers({"safe_retry": insufficient})
        with pytest.raises(TransitionError, match="EVIDENCE_REQUIRED"):
            transition_task(
                s, task_id, 1, "SUBMITTING", TransitionEvidence(lease, "TEST_ONLY_proof")
            )
    assert facts(factory, task_id) == original


def test_safe_retry_never_binds_new_upstream_and_resubmits(task_factory, runtime):
    from app.dispatch.consumer import LeaseManager
    from app.tasks.state_machine import (
        TransitionError,
        TransitionEvidence,
        TransitionVerifiers,
        VerifiedTransition,
        transition_task,
    )

    factory = runtime[0]
    task_id = task_factory("INVESTIGATING")
    lease = LeaseManager(factory).claim_task(task_id, "retry-worker")
    with factory() as s, s.begin():
        task = s.get(GenerationTask, task_id)

        def found_original(*args):
            return VerifiedTransition(
                task.id,
                task.agent_id,
                task.agent_version,
                task.external_submission_id,
                "safe_retry",
                "TEST_ONLY_proof",
                "TEST_ONLY_protocol",
                upstream_id="TEST_ONLY_already_found",
            )

        s.info["transition_verifiers"] = TransitionVerifiers({"safe_retry": found_original})
        with pytest.raises(TransitionError, match="QUERY_ORIGINAL_REQUIRED"):
            transition_task(
                s, task_id, 1, "SUBMITTING", TransitionEvidence(lease, "TEST_ONLY_proof")
            )


@pytest.mark.parametrize("state", ["QUEUED", "INVESTIGATING"])
def test_known_original_cannot_be_resubmitted(task_factory, runtime, state):
    from app.dispatch.consumer import LeaseManager
    from app.tasks.state_machine import TransitionError, TransitionEvidence, transition_task

    factory = runtime[0]
    task_id = task_factory(state, "TEST_ONLY_original")
    lease = LeaseManager(factory).claim_task(task_id, "retry-worker")
    with factory() as s, s.begin():
        with pytest.raises(TransitionError, match="QUERY_ORIGINAL_REQUIRED"):
            transition_task(s, task_id, 1, "SUBMITTING", TransitionEvidence(lease))


@pytest.mark.parametrize("basis", ["reliable_idempotency", "proven_not_accepted"])
@pytest.mark.parametrize("proof_offset_seconds", [0, 30])
def test_verified_original_retry_is_same_task_and_one_freeze(
    task_factory, runtime, basis, proof_offset_seconds
):
    from app.dispatch.consumer import LeaseManager
    from app.tasks.state_machine import (
        SafeRetryEvidence,
        TransitionError,
        TransitionEvidence,
        TransitionVerifiers,
        VerifiedTransition,
        transition_task,
    )

    factory = runtime[0]
    task_id = task_factory("INVESTIGATING")
    lease = LeaseManager(factory).claim_task(task_id, "retry-worker")
    original = facts(factory, task_id)
    with factory() as s, s.begin():
        task = s.get(GenerationTask, task_id)

        def verified(*args):
            # This fixture verifier reads the durable task/event in the same transaction;
            # T09 must additionally validate its persisted D-01 protocol proof.
            source = s.scalar(select(TaskStateEvent).where(TaskStateEvent.task_id == task_id))
            assert source.to_state == "INVESTIGATING"
            return VerifiedTransition(
                task.id,
                task.agent_id,
                task.agent_version,
                task.external_submission_id,
                "safe_retry",
                source.id,
                "TEST_ONLY_protocol",
                safe_retry=SafeRetryEvidence(
                    "TEST_ONLY_protocol",
                    basis,
                    source.id,
                    "TEST_ONLY_verifier",
                    database_now(s) + timedelta(seconds=proof_offset_seconds),
                ),
            )

        source_id = s.scalar(select(TaskStateEvent.id).where(TaskStateEvent.task_id == task_id))
        s.info["transition_verifiers"] = TransitionVerifiers({"safe_retry": verified})
        if proof_offset_seconds > 0:
            with pytest.raises(TransitionError, match="EVIDENCE_REQUIRED"):
                transition_task(s, task_id, 1, "SUBMITTING", TransitionEvidence(lease, source_id))
            assert (task.state, task.state_version) == ("INVESTIGATING", 1)
            assert facts(factory, task_id) == original
            return
        receipt = transition_task(s, task_id, 1, "SUBMITTING", TransitionEvidence(lease, source_id))
        assert receipt.state == "SUBMITTING"
    assert facts(factory, task_id) == original
    with factory() as s:
        evidence = s.scalar(
            select(TaskStateEvent.evidence).where(
                TaskStateEvent.task_id == task_id, TaskStateEvent.state_version == 2
            )
        )
        assert evidence["retry_basis"] == basis
        assert evidence["verified_by"] == "TEST_ONLY_verifier"


@pytest.mark.parametrize(
    "state,upstream,expected",
    [
        ("SUBMITTING", None, "reconcile_submission"),
        ("RUNNING", "TEST_ONLY_original", "query_original"),
        ("INVESTIGATING", None, "investigate"),
        ("SAVE_RECOVERY", "TEST_ONLY_original", "save_original"),
    ],
)
def test_expired_worker_recovers_persisted_stage(task_factory, runtime, state, upstream, expected):
    from app.dispatch.consumer import LeaseManager

    factory, _, _, dispatcher, scheduler, consumer = runtime
    task_id = task_factory(state, upstream)
    original = facts(factory, task_id)
    dead_lease = LeaseManager(factory).claim_task(task_id, "TEST_ONLY_dead_worker")
    assert task_id not in scheduler.recover_due_tasks(batch_size=1000).scheduled
    with factory() as s, s.begin():
        s.execute(
            text(
                "UPDATE generation_tasks SET lease_expires_at=UTC_TIMESTAMP(6) "
                "- INTERVAL 1 SECOND WHERE id=:id"
            ),
            {"id": task_id},
        )
    assert task_id in scheduler.recover_due_tasks(batch_size=1000).scheduled
    dispatcher.dispatch_pending(1000)
    seen = []

    def recovered(context):
        assert context.lease.fencing_token > dead_lease.fencing_token
        seen.append((context.task_id, context.action, context.upstream_id))

    consumer.handlers[expected] = recovered
    assert consumer.consume_once(1000).handled >= 1
    assert seen and set(seen) == {(task_id, expected, upstream)}
    assert facts(factory, task_id) == original
    with factory() as s:
        assert s.get(GenerationTask, task_id).state == state


def test_verified_acceptance_binds_original_identity_atomically(task_factory, runtime):
    from app.dispatch.consumer import LeaseManager
    from app.tasks.state_machine import (
        TransitionError,
        TransitionEvidence,
        TransitionVerifiers,
        VerifiedTransition,
        transition_task,
    )

    factory = runtime[0]
    task_id = task_factory("SUBMITTING")
    lease = LeaseManager(factory).claim_task(task_id, "acceptance-worker")
    original = facts(factory, task_id)
    with factory() as s, s.begin():
        task = s.get(GenerationTask, task_id)

        def accepted(*args):
            return VerifiedTransition(
                task.id,
                task.agent_id,
                task.agent_version,
                task.external_submission_id,
                "accepted",
                "TEST_ONLY_accept",
                "TEST_ONLY_protocol",
                upstream_id="TEST_ONLY_original",
            )

        s.info["transition_verifiers"] = TransitionVerifiers({"accepted": accepted})
        assert (
            transition_task(
                s, task_id, 1, "RUNNING", TransitionEvidence(lease, "TEST_ONLY_accept")
            ).state_version
            == 2
        )
        with pytest.raises(TransitionError, match="VERSION_CONFLICT"):
            transition_task(s, task_id, 1, "RUNNING", TransitionEvidence(lease, "TEST_ONLY_accept"))
    with factory() as s:
        task = s.get(GenerationTask, task_id)
        assert (task.state, task.upstream_id) == ("RUNNING", "TEST_ONLY_original")
        assert (
            s.scalar(
                select(func.count())
                .select_from(DurableEvent)
                .where(DurableEvent.task_id == task_id)
            )
            == 1
        )
    assert facts(factory, task_id) == original
