"""Offline recovery boundary regressions; fake storage, no real upstream requests."""

import json
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agents import upstream
from app.agents.contracts import QueryOutcome
from app.agents.upstream import UpstreamService


def harness(monkeypatch, *, status="UNAVAILABLE", reason=None):
    task = SimpleNamespace(id=str(uuid4()), state="INVESTIGATING", state_version=4,
                           upstream_id="original", external_submission_id="external",
                           investigation_reason=reason, settlement_state="FROZEN")
    outcome = QueryOutcome(status=status, upstream_task_id="original",
                           external_submission_id="external")
    row = SimpleNamespace(payload={"operation": "query", "outcome": outcome.model_dump()})
    session = SimpleNamespace(begin=lambda: nullcontext(), get=lambda *args: row)
    service = UpstreamService(lambda: nullcontext(session), SimpleNamespace())
    monkeypatch.setattr(upstream, "locked_execution", lambda *args: task)
    monkeypatch.setattr(service, "_accepted", lambda *args: SimpleNamespace(upstream_id="original"))
    return service, task


def test_needs_input_preserves_identity_and_frozen_settlement(monkeypatch):
    service, task = harness(monkeypatch, status="NEEDS_INPUT")
    service._apply_observation(task.id, None, "observation")
    assert task.state == "INVESTIGATING"
    assert task.investigation_reason == "UPSTREAM_NEEDS_INPUT"
    assert task.upstream_id == "original"
    assert task.external_submission_id == "external"
    assert task.settlement_state == "FROZEN"
    assert task.state_version == 4


@pytest.mark.parametrize("reason", ["UPSTREAM_NEEDS_INPUT", "CALLBACK_EVENT_CONFLICT"])
def test_automatic_unavailable_does_not_erase_manual_wait(monkeypatch, reason):
    service, task = harness(monkeypatch, reason=reason)
    service._apply_observation(task.id, None, "observation")
    assert task.investigation_reason == reason


def test_transient_unavailable_remains_recoverable(monkeypatch):
    service, task = harness(monkeypatch)
    service._apply_observation(task.id, None, "observation")
    assert task.investigation_reason == "UPSTREAM_ACCEPTANCE_UNCONFIRMED"
    assert task.state == "INVESTIGATING"
    assert task.settlement_state == "FROZEN"


def test_stage_diagnostic_logs_only_allowlisted_context(caplog, operations_log_capture):
    from app.operations.telemetry import stage_diagnostic

    task_id, event_id = str(uuid4()), str(uuid4())
    stage_diagnostic(stage="consume", task_id=task_id, event_id=event_id,
                     state_version=3, action="query_original",
                     lease=SimpleNamespace(fencing_token=7, owner="secret-owner"),
                     error=ValueError("secret-error SQL password"), code="STAGE_EXCEPTION",
                     http_status=503, outcome="error")
    payload = json.loads(caplog.records[-1].message)
    assert payload["task_id"] == task_id and payload["event_id"] == event_id
    assert payload["fencing_token"] == 7 and payload["state_version"] == 3
    assert payload["error_type"] == "ValueError" and payload["http_status"] == 503
    assert "secret" not in caplog.text and "password" not in caplog.text
    stage_diagnostic(stage="secret-stage", task_id="private task", code="private code",
                     action="private action", error=Exception("private error"))
    assert "private" not in caplog.text and "secret-stage" not in caplog.text


@pytest.mark.parametrize("age,lease_seconds,expected", [
    (59, None, False), (60, None, True), (61, 1, False), (61, -1, True),
])
def test_running_watchdog_respects_exact_policy_deadline_and_live_lease(
    age, lease_seconds, expected,
):
    from datetime import datetime, timedelta

    from app.investigations.service import running_watchdog_due

    now = datetime(2026, 10, 19, 1, 0)
    task = SimpleNamespace(state="RUNNING", lease_expires_at=(
        now + timedelta(seconds=lease_seconds) if lease_seconds is not None else None
    ))
    assert running_watchdog_due(task, now - timedelta(seconds=age), now,
                                SimpleNamespace(deadline_seconds=60)) is expected


def test_history_recovery_reads_pages_without_resource_locks_and_renews_lease(monkeypatch):
    from datetime import datetime

    rows = [SimpleNamespace(id=f"row-{i}", created_at=datetime(2026, 1, 1),
                            payload={"operation": "query", "outcome": {
                                "status": "UNAVAILABLE"}}) for i in range(100)]
    found = SimpleNamespace(id="found", created_at=datetime(2026, 1, 1), payload={
        "operation": "query", "outcome": {"status": "FOUND", "state": "RUNNING",
                                           "upstream_task_id": "original"}})
    pages, renewals = iter([rows, [found]]), []

    class Session:
        def scalars(self, query):
            assert query._limit_clause.value == 100
            assert query._for_update_arg is None
            return SimpleNamespace(all=lambda: next(pages))

    service = UpstreamService(lambda: nullcontext(Session()), SimpleNamespace())
    monkeypatch.setattr(service.leases, "renew", lambda lease: renewals.append(lease) or lease)
    assert service._pending_observation("task", "lease") == "found"
    assert renewals == ["lease", "lease"]


@pytest.mark.parametrize("reason", [
    "UPSTREAM_NEEDS_INPUT", "CALLBACK_EVENT_CONFLICT",
    "CALLBACK_INBOX_PENDING:UPSTREAM_NEEDS_INPUT",
    "CALLBACK_INBOX_PENDING:CALLBACK_EVENT_CONFLICT",
])
def test_automatic_recovery_of_manual_wait_performs_no_transport(monkeypatch, reason):
    service, task = harness(monkeypatch, reason=reason)
    monkeypatch.setattr(upstream, "task_view", lambda session, task: task)
    # Registry has no bind/query operation: reaching transport would fail this test.
    assert service.recover_original_task(task.id, lease=object()) is task
    assert task.investigation_reason == reason
    assert task.state == "INVESTIGATING" and task.settlement_state == "FROZEN"


def test_lost_renewal_keeps_original_transport_observation(monkeypatch):
    from threading import Event

    service = UpstreamService(None, None)
    entered = Event()
    renewals = []

    def renew(lease):
        renewals.append(lease)
        if len(renewals) == 1:
            return lease
        entered.set()
        raise OSError("private connection")

    def operation():
        assert entered.wait(2)
        return "original observation"

    monkeypatch.setattr(upstream, "SUBMIT_LEASE_REFRESH_SECONDS", 0.01)
    monkeypatch.setattr(service.leases, "renew", renew)
    assert service._leased_transport(operation, (), "lease") == "original observation"
    assert len(renewals) == 2


def test_finished_transport_timeout_is_not_mistaken_for_a_heartbeat_timeout(monkeypatch):
    service = UpstreamService(None, None)
    monkeypatch.setattr(service.leases, "renew", lambda lease: lease)

    class Pending:
        reads = 0

        def result(self, timeout=None):
            self.reads += 1
            if self.reads > 2:
                raise AssertionError("completed transport was polled repeatedly")
            raise TimeoutError("transport itself timed out")

        def done(self):
            return True

    pool = SimpleNamespace(submit=lambda *args: Pending())
    monkeypatch.setattr(upstream, "ThreadPoolExecutor", lambda **kwargs: nullcontext(pool))
    with pytest.raises(TimeoutError):
        service._leased_transport(lambda: None, (), "lease")


def test_stalled_running_scan_assigns_review_without_failure_or_refund(monkeypatch):
    from datetime import datetime, timedelta

    from app.audit.models import AuditEvent
    from app.auth.models import User
    from app.investigations import service as investigations
    from app.investigations.models import Investigation, InvestigationAlert
    from app.tasks.models import GenerationTask, TaskSnapshot, TaskStateEvent

    now = datetime(2026, 10, 19, 1, 0)
    task = SimpleNamespace(id=str(uuid4()), user_id=str(uuid4()), state="RUNNING",
                           state_version=3, lease_expires_at=None,
                           created_at=now - timedelta(seconds=61), settlement_state="FROZEN",
                           upstream_id="original", investigation_reason=None)
    owner = SimpleNamespace(id=str(uuid4()), role="admin", status="active")
    policy = SimpleNamespace(deadline_seconds=60, responsible_user_id=owner.id,
                             escalation_ref="operations:investigations")
    added = []

    class Session:
        def begin(self):
            return nullcontext()

        def get(self, model, key):
            if model is GenerationTask:
                return task
            if model is TaskSnapshot:
                return SimpleNamespace(policy_versions={"D-08": "policy-v1"})
            if model is User:
                return owner
            if model is InvestigationAlert:
                return next((row for row in added if isinstance(row, model) and row.key == key),
                            None)
            return None

        def scalar(self, query):
            model = query.column_descriptions[0]["entity"]
            if model is User:
                return owner
            if model is TaskStateEvent:
                return task.created_at
            return None

        def scalars(self, query):
            if query.column_descriptions[0]["entity"] is GenerationTask:
                # Execute the scope of the emitted candidate query in this fake.
                states = next(value for value in query.compile().params.values()
                              if isinstance(value, list))
                return SimpleNamespace(all=lambda: [task.id] if task.state in states else [])
            return []

        def add(self, row):
            added.append(row)

        def flush(self):
            pass

    svc = investigations.InvestigationService(lambda: nullcontext(Session()), upstream=None)
    monkeypatch.setattr(svc, "policy", lambda *args: policy)
    monkeypatch.setattr(investigations, "database_now", lambda session: now)
    monkeypatch.setattr(investigations, "lock_task_resources", lambda *args: (task, None, None))
    svc.scan()
    case = next(row for row in added if isinstance(row, Investigation))
    assert case.status == "overdue" and case.owner == owner.id
    assert case.deadline_at == now - timedelta(seconds=1)
    assert {row.kind for row in added if isinstance(row, InvestigationAlert)} == {
        "STALLED_RUNNING", "OVERDUE",
    }
    assert any(isinstance(row, AuditEvent) and row.action == "investigation.auto_assign"
               for row in added)
    assert task.state == "RUNNING" and task.settlement_state == "FROZEN"
    assert task.upstream_id == "original" and task.state_version == 3
