"""Real publication/ledger behavior, including two separate MySQL connections."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.ledger.models import CreditAccount, CreditLedger, CreditReservation
from app.storage.models import CapacityReservation
from app.tasks.models import GenerationTask
from tests.faults.test_result_persistence import persistence
from tests.faults.test_result_persistence import ready as ready_fixture
from tests.faults.test_upstream_recovery import calls, submit
from tests.integration.test_callbacks import callbacks as callbacks_fixture
from tests.integration.test_callbacks import changed, event_for, post
from tests.t12_fixtures import upstream as upstream_fixture

ready = ready_fixture
upstream = upstream_fixture
callbacks = callbacks_fixture


def publisher(runtime, root):
    from app.results.publisher import ResultPublisher

    root.mkdir(parents=True, exist_ok=True)
    return ResultPublisher(persistence(runtime, root))


def assert_facts(runtime, task, state="SUCCEEDED", count=2):
    from app.conversations.models import Message
    from app.works.models import Work, WorkItem

    with runtime[0]() as s:
        row = s.get(GenerationTask, task)
        account = s.get(CreditAccount, row.user_id)
        reservation = s.scalar(select(CreditReservation).where(CreditReservation.task_id == task))
        capacity = s.get(CapacityReservation, row.capacity_reservation_id)
        ledger = s.scalars(
            select(CreditLedger).where(
                CreditLedger.task_id == task, CreditLedger.kind.in_(["consume", "release"])
            )
        ).all()
        works = s.scalars(select(Work).where(Work.task_id == task)).all()
        messages = s.scalars(
            select(Message).where(Message.task_id == task, Message.kind == "final")
        ).all()
        assert row.state == state
        assert len(ledger) == 1
        assert account.available + account.frozen + account.consumed == account.credited_total
        assert account.frozen == 0
        if state == "SUCCEEDED":
            assert row.settlement_state == "CONSUMED" and reservation.state == "consumed"
            assert account.available == 70 and account.consumed == 30
            assert ledger[0].kind == "consume" and ledger[0].amount == 30
            assert len(works) == len(messages) == 1
            items = s.scalars(select(WorkItem).where(WorkItem.work_id == works[0].id)).all()
            assert len(items) == count
            assert capacity.state == "finalized"
            assert capacity.actual_bytes == sum(
                i["actual_bytes"] for i in messages[0].content["items"]
            )
            assert all(
                i.get("text")
                for i in messages[0].content["items"]
                if i["media_type"] == "text/plain"
            )
        else:
            assert row.settlement_state == "RELEASED" and reservation.state == "released"
            assert account.available == 100 and account.consumed == 0
            assert ledger[0].kind == "release" and not works and not messages
            assert capacity.state == "released" and capacity.actual_bytes == 0
        result = dict(
            task=task,
            state=row.state,
            work_ids=[w.id for w in works],
            ledger_ids=[x.id for x in ledger],
            capacity=capacity.actual_bytes,
            balances=[account.available, account.frozen, account.consumed],
            manifest=works[0].manifest_id if works else None,
        )
        print("T12_FACTS", result, calls(runtime, task))
        return result


def test_complete_publication_once(upstream, ready, tmp_path, redis_namespace):
    from app.storage.local_store import LocalStore
    from worker.main import compose_worker

    task = ready(count=2)
    redis, prefix = redis_namespace
    worker = compose_worker(
        upstream[0],
        redis,
        prefix + "t12",
        "workers",
        "t12",
        registry=upstream[1].registry,
        task_ids=[task],
        store=LocalStore(tmp_path),
    )
    assert worker.tick()[2].failed == 0
    original = assert_facts(upstream, task)
    before = calls(upstream, task)
    result = publisher(upstream, tmp_path).run(task)
    assert [str(x) for x in result.work_ids] == original["work_ids"]
    assert assert_facts(upstream, task) == original
    assert calls(upstream, task) == before


def failure(runtime, client):
    task = runtime[2]()
    submit(runtime, task)
    path, wire = event_for(runtime, task)
    assert post(client, path, changed(wire, state="FAILED", result=None)).status_code == 202
    runtime[1].poll_original_task(task)
    return task, runtime[1].pending_failure(task)


@pytest.mark.parametrize("has_store", [True, False])
def test_actual_worker_retains_failed_hold_until_owner_choice(
    upstream, callbacks, tmp_path, redis_namespace, has_store
):
    from app.storage.local_store import LocalStore
    from worker.main import compose_worker

    task, ref = failure(upstream, callbacks)
    assert ref
    redis, prefix = redis_namespace
    worker = compose_worker(
        upstream[0],
        redis,
        prefix + "failed",
        "workers",
        "t12",
        registry=upstream[1].registry,
        task_ids=[task],
        store=LocalStore(tmp_path) if has_store else None,
    )
    assert worker.tick()[2].failed == 0
    with upstream[0]() as session:
        row = session.get(GenerationTask, task)
        reservation = session.scalar(select(CreditReservation).where(
            CreditReservation.task_id == task))
        account = session.get(CreditAccount, row.user_id)
        assert row.state == "FAILED" and row.settlement_state == "FROZEN"
        assert reservation.state == "frozen"
        assert (account.available, account.frozen, account.consumed) == (70, 30, 0)
        assert not session.scalars(select(CreditLedger).where(
            CreditLedger.task_id == task, CreditLedger.kind.in_(["release", "consume"]),
        )).all()
    before = calls(upstream, task)
    assert publisher(upstream, tmp_path).run(task) is None
    assert calls(upstream, task) == before


@pytest.mark.parametrize("same_kind", [False, True])
def test_concurrent_settle_release_exclusive(upstream, ready, callbacks, tmp_path, same_kind):
    from app.agents.models import AgentEventDecision
    from app.ledger.service import release_credits
    from app.results.publisher import publish_and_settle
    from app.tasks.state_machine import TransitionError, TransitionEvidence

    task = ready(count=2)
    service = publisher(upstream, tmp_path)
    path, wire = event_for(upstream, task)
    assert post(callbacks, path, changed(wire, state="FAILED", result=None)).status_code == 202
    upstream[1].poll_original_task(task)
    with upstream[0]() as s:
        conflict = s.scalar(
            select(AgentEventDecision.event_ref).where(
                AgentEventDecision.task_id == task, AgentEventDecision.disposition == "CONFLICT"
            )
        )
        version = s.get(GenerationTask, task).state_version
    lease = service.leases.claim_task(task, "t12-race")
    prepared = service.prepare(task, lease=lease)
    barrier = Barrier(2)
    connection_ids = []

    def contender(consume):
        try:
            with upstream[0]() as s, s.begin():
                connection_ids.append(s.scalar(text("SELECT CONNECTION_ID()")))
                service.install_verifiers(s, prepared)
                barrier.wait(timeout=10)
                if consume:
                    publish_and_settle(s, task, prepared.delivery.manifest_id, version)
                else:
                    release_credits(s, task, TransitionEvidence(lease, conflict))
            return "committed"
        except TransitionError:
            return "rejected"

    try:
        with ThreadPoolExecutor(2) as pool:
            a, b = pool.submit(contender, True), pool.submit(contender, same_kind)
            assert [a.result(), b.result()].count("committed") == (2 if same_kind else 1)
        assert len(set(connection_ids)) == 2
        assert_facts(upstream, task)
    finally:
        service.leases.release(lease)


def test_failure_wins_and_duplicate_release_race(upstream, callbacks, tmp_path):
    from app.ledger.service import release_credits, settle_credits
    from app.tasks.state_machine import TransitionError, TransitionEvidence

    task, ref = failure(upstream, callbacks)
    service = publisher(upstream, tmp_path)
    lease = service.leases.claim_task(task, "t12-release-race")
    barrier = Barrier(2)
    ids = []

    def release():
        with upstream[0]() as s, s.begin():
            ids.append(s.scalar(text("SELECT CONNECTION_ID()")))
            service.install_verifiers(s)
            barrier.wait(timeout=10)
            return release_credits(s, task, TransitionEvidence(lease, ref))

    try:
        with ThreadPoolExecutor(2) as pool:
            a, b = pool.submit(release), pool.submit(release)
            receipts = [a.result(), b.result()]
        assert len(set(ids)) == 2 and sum(r.changed for r in receipts) == 1
        with upstream[0]() as s, s.begin():
            service.install_verifiers(s)
            with pytest.raises(TransitionError):
                settle_credits(s, task, TransitionEvidence(lease, ref))
        assert_facts(upstream, task, "FAILED")
        assert service.run(task) is None
    finally:
        service.leases.release(lease)


@pytest.mark.parametrize("scenario", ["partial", "expired_link"])
def test_no_delivery_no_charge(upstream, ready, tmp_path, scenario):
    task = ready(scenario)
    assert publisher(upstream, tmp_path).run(task) is None
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        assert row.settlement_state == "FROZEN"
        assert s.get(CreditAccount, row.user_id).frozen == 30
    assert calls(upstream, task)["submit"] == 1


def test_bare_dto_and_success_cannot_settle(upstream, ready, tmp_path):
    from app.ledger.service import release_credits, settle_credits
    from app.tasks.state_machine import TransitionError

    task = ready()
    service = publisher(upstream, tmp_path)
    dto = service.persistence.save_original(task)
    for evidence in (True, dto):
        with upstream[0]() as s, s.begin():
            service.install_verifiers(s)
            for operation in (settle_credits, release_credits):
                with pytest.raises(TransitionError, match="EVIDENCE_REQUIRED"):
                    operation(s, task, evidence)


def test_all_operations_conserve_ledger(upstream, ready, callbacks, tmp_path):
    import importlib.util

    import app.ledger as module

    assert importlib.util.find_spec(module.__name__ + ".reconcile"), (
        "Read-only reconciliation missing"
    )
    from app.common.types import Principal
    from app.ledger.reconcile import reconcile_accounts
    from app.ledger.service import grant_credits

    good = ready(count=2)
    publisher(upstream, tmp_path / "good").run(good)
    bad, _ = failure(upstream, callbacks)
    service = publisher(upstream, tmp_path / "bad")
    lease = service.leases.claim_task(bad, "t12-release")
    from app.dispatch.consumer import HandlerContext

    service.handle(HandlerContext(bad, "INVESTIGATING", 1, "", "", "", None, "investigate", lease))
    service.leases.release(lease)
    with upstream[0]() as s, s.begin():
        uid = s.get(GenerationTask, good).user_id
        grant_credits(
            s,
            uid,
            "admin",
            uuid4().hex,
            7,
            "TEST_ONLY grant",
            Principal(user_id=uid, role="admin", session_id=uuid4(), auth_version=0),
        )
    with upstream[0]() as s:
        uids = {s.get(GenerationTask, t).user_id for t in (good, bad)}
        before = [
            (x.user_id, x.available, x.frozen, x.consumed)
            for x in s.scalars(select(CreditAccount).where(CreditAccount.user_id.in_(uids)))
        ]
        report = reconcile_accounts(s)
        assert not [d for d in report.differences if d.user_id in uids]
        assert before == [
            (x.user_id, x.available, x.frozen, x.consumed)
            for x in s.scalars(select(CreditAccount).where(CreditAccount.user_id.in_(uids)))
        ]


def test_final_message_constraint_and_history(upstream, ready, tmp_path):
    from datetime import timedelta

    from sqlalchemy.exc import IntegrityError

    from app.auth.models import AuthSession
    from app.common.types import Principal
    from app.conversations.models import Message
    from app.conversations.service import ConversationService
    from app.ledger.service import now

    task = ready(count=2)
    view = publisher(upstream, tmp_path).run(task)
    with upstream[0]() as s, s.begin():
        row = s.get(GenerationTask, task)
        auth_id = str(uuid4())
        s.add(
            AuthSession(
                id=auth_id,
                user_id=row.user_id,
                token_hash=uuid4().hex,
                csrf_hash=uuid4().hex,
                auth_version=0,
                expires_at=now() + timedelta(hours=1),
            )
        )
        s.flush()
        history = ConversationService(s).read_conversation(
            Principal(user_id=row.user_id, role="user", session_id=auth_id, auth_version=0),
            row.conversation_id,
        )
        final = [m for m in history.messages.items if m.kind == "final"]
        assert len(final) == 1 and final[0].content["work_ids"] == [str(w) for w in view.work_ids]
        assert history.tasks.items[0].work_ids == view.work_ids
        with pytest.raises(IntegrityError), s.begin_nested():
            s.add(
                Message(
                    id=str(uuid4()),
                    user_id=row.user_id,
                    conversation_id=row.conversation_id,
                    task_id=task,
                    kind="final",
                    role="assistant",
                    content={},
                    created_at=now(),
                )
            )
            s.flush()


def test_reconcile_reports_without_repair(upstream, ready):
    from app.ledger.reconcile import reconcile_accounts

    task = ready("partial")
    with upstream[0]() as s:
        uid = s.get(GenerationTask, task).user_id
        s.execute(
            text(
                "UPDATE credit_accounts SET available=available-1, consumed=consumed+1 "
                "WHERE user_id=:uid"
            ),
            {"uid": uid},
        )
        report = reconcile_accounts(s)
        assert {"LEDGER_ACCOUNT_MISMATCH", "RESERVATION_BALANCE_MISMATCH"} <= {
            d.code for d in report.differences if d.user_id == uid
        }
        row = s.get(CreditAccount, uid)
        assert row.available == 69 and row.consumed == 1
        s.rollback()


def test_failure_precedes_result_with_two_real_connections(upstream, callbacks, tmp_path):
    from app.agents.models import AgentEventDecision
    from app.ledger.service import release_credits, settle_credits
    from app.tasks.state_machine import TransitionError, TransitionEvidence

    task, failure_ref = failure(upstream, callbacks)
    upstream[1].recover_original_task(task)
    upstream[1].poll_original_task(task)
    with upstream[0]() as s:
        conflict_ref = s.scalar(
            select(AgentEventDecision.event_ref).where(
                AgentEventDecision.task_id == task, AgentEventDecision.disposition == "CONFLICT"
            )
        )
    assert conflict_ref
    service = publisher(upstream, tmp_path)
    lease = service.leases.claim_task(task, "t12-failure-first")
    barrier = Barrier(2)
    ids = []

    def contend(release):
        try:
            with upstream[0]() as s, s.begin():
                ids.append(s.scalar(text("SELECT CONNECTION_ID()")))
                service.install_verifiers(s)
                barrier.wait(timeout=10)
                if release:
                    release_credits(s, task, TransitionEvidence(lease, failure_ref))
                else:
                    settle_credits(s, task, TransitionEvidence(lease, conflict_ref))
            return "committed"
        except TransitionError:
            return "rejected"

    try:
        with ThreadPoolExecutor(2) as pool:
            a, b = pool.submit(contend, True), pool.submit(contend, False)
            assert [a.result(), b.result()] == ["committed", "rejected"]
        assert len(set(ids)) == 2
        assert_facts(upstream, task, "FAILED")
    finally:
        service.leases.release(lease)


def test_reconcile_ignores_clock_skew_in_real_settlement(upstream, ready, tmp_path, monkeypatch):
    from datetime import timedelta

    import app.ledger.service as ledger_service
    from app.ledger.reconcile import reconcile_accounts

    # Actual grant/freeze writers use app time; actual settle writer uses DB time.
    clock = ledger_service.now
    monkeypatch.setattr(ledger_service, "now", lambda: clock() + timedelta(seconds=120))
    task = ready(count=2)
    assert publisher(upstream, tmp_path).run(task).state == "SUCCEEDED"
    with upstream[0]() as s:
        user_id = s.get(GenerationTask, task).user_id
        rows = s.scalars(select(CreditLedger).where(CreditLedger.user_id == user_id)).all()
        moments = {row.kind: row.created_at for row in rows}
        assert moments["consume"] < moments["signup"] <= moments["freeze"]
        account = s.get(CreditAccount, user_id)
        assert (account.available, account.frozen, account.consumed) == (70, 0, 30)
        differences = [d for d in reconcile_accounts(s).differences if d.user_id == user_id]
        print(
            "T12_FIX1_CLOCK", task, [(r.id, r.kind, str(r.created_at)) for r in rows], differences
        )
        assert differences == []
