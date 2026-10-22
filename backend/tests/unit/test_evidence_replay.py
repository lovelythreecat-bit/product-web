"""Replay evidence must be bounded without forgetting distinct immutable variants."""

from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.agents.callbacks import CallbackService


class EvidenceSession:
    def __init__(self, rows):
        self.rows = rows

    def get(self, model, key, **kwargs):
        return self.rows.get(key)

    def add(self, row):
        self.rows[row.id] = row

    def flush(self):
        pass


def test_thousand_changed_content_replays_keep_one_conflict_after_restart(monkeypatch):
    import app.agents.callbacks as module

    monkeypatch.setattr(module, "database_now", lambda session: datetime(2026, 10, 19))
    rows = {}
    task = SimpleNamespace(id="task")
    upstream = SimpleNamespace(factory=None, registry=None)
    for _ in range(1000):
        # New service/session proves this is not an in-memory duplicate cache.
        CallbackService(upstream)._conflict(
            EvidenceSession(rows), task, "EVENT_REPLAY_CONFLICT", "original", "changed",
        )
    assert len(rows) == 1
    evidence = next(iter(rows.values()))
    assert evidence.payload == {
        "reason": "EVENT_REPLAY_CONFLICT", "reference": "original", "digest": "changed",
    }
    CallbackService(upstream)._conflict(
        EvidenceSession(rows), task, "EVENT_REPLAY_CONFLICT", "original", "different",
    )
    CallbackService(upstream)._conflict(
        EvidenceSession(rows), task, "EVENT_REPLAY_CONFLICT", "other-original", "changed",
    )
    assert len(rows) == 3


@pytest.mark.parametrize("state", ["INVESTIGATING", "RUNNING"])
def test_known_conflict_does_not_query_upstream_but_reduces_new_receipts(monkeypatch, state):
    upstream = SimpleNamespace(factory=None, registry=None)
    service = CallbackService(upstream)
    view = SimpleNamespace(state=state, investigation_reason="CALLBACK_EVENT_CONFLICT")
    upstream._view = lambda task_id: view
    upstream.recover_original_task = lambda *args, **kwargs: pytest.fail("remote query repeated")
    reduced = []
    monkeypatch.setattr(service, "reduce_pending", lambda *args: reduced.append(args[0]))
    monkeypatch.setattr(service, "pending_failure", lambda task_id: None)
    assert service.poll_original_task("task", lease=object()) is view
    assert reduced == ["task"]


def test_explicit_text_revalidation_preserves_all_existing_warning_metadata():
    import app.results.recovery as module
    from app.agents.contracts import ResultManifest

    original = ResultManifest(complete=True, expected_items=1, items=[dict(
        item_key="original-1", locator="/result/original", media_type="text/plain",
        sha256="a" * 64, byte_length=10,
    )], warnings=["original warning"])
    compatible = getattr(module, "compatible_text_manifest", None)
    assert callable(compatible), "Explicit repair needs a verified warnings-extension rule"
    assert compatible(original, original.model_copy(update={
        "warnings": ("original warning", "additional warning"),
    }))
    assert not compatible(original, original.model_copy(update={"warnings": ()}))
    assert not compatible(original, original.model_copy(update={"warnings": ("replaced",)}))
    assert not compatible(original, original.model_copy(update={"items": (
        original.items[0].model_copy(update={"sha256": "b" * 64}),
    )}))


def test_adapter_advisory_duplicate_status_does_not_create_another_conflict(monkeypatch):
    import app.agents.callbacks as module
    from app.agents.contracts import VerifiedEvent

    monkeypatch.setattr(module, "database_now", lambda session: datetime(2026, 10, 19))
    rows = {}
    upstream = SimpleNamespace(factory=None, registry=None,
                               _identity=lambda *args: {"task_id": "task"},
                               _latest=lambda *args: None)
    service = CallbackService(upstream)
    event = VerifiedEvent(status="VERIFIED", event_id="original:2", state="FAILED")
    for status in ("VERIFIED", "DUPLICATE"):
        result = service._persist(
            EvidenceSession(rows), SimpleNamespace(id="task"), object(),
            event.model_copy(update={"status": status}), "callback", "same-raw-body",
        )
        assert result.status == "CONFLICT"
    assert len(rows) == 1


def test_conflict_checks_current_rows_after_waiting_for_another_transaction(monkeypatch):
    import app.agents.callbacks as module

    monkeypatch.setattr(module, "database_now", lambda session: datetime(2026, 10, 19))
    rows = {}

    class SnapshotSession(EvidenceSession):
        def get(self, model, key, *, with_for_update=False):
            # Both callers established empty REPEATABLE READ snapshots before
            # acquiring the task lock. Only a current read can see the winner.
            return self.rows.get(key) if with_for_update else None

        def add(self, row):
            assert row.id not in rows, "Concurrent replay attempted duplicate primary-key insert"
            super().add(row)

    service = CallbackService(SimpleNamespace(factory=None, registry=None))
    first, second = SnapshotSession(rows), SnapshotSession(rows)
    for session in (first, second):
        service._conflict(session, SimpleNamespace(id="task"), "EVENT_REPLAY_CONFLICT",
                          "original", "same-changed-body")
    assert len(rows) == 1


def test_new_local_running_receipt_does_not_authorize_immediate_remote_query(monkeypatch):
    upstream = SimpleNamespace(factory=None, registry=None)
    service = CallbackService(upstream)
    view = SimpleNamespace(state="RUNNING", investigation_reason=None)
    upstream._view = lambda task_id: view
    upstream.recover_original_task = lambda *args, **kwargs: pytest.fail("remote query repeated")
    monkeypatch.setattr(service, "reduce_pending", lambda *args: True)
    monkeypatch.setattr(service, "pending_failure", lambda task_id: None)
    assert service.poll_original_task("task", lease=object()) is view


@pytest.mark.parametrize("source", ["callback", "poll"])
def test_only_fresh_callback_opens_local_inbox_of_blocked_task(monkeypatch, source):
    import app.agents.callbacks as module
    from app.agents.contracts import VerifiedEvent

    monkeypatch.setattr(module, "database_now", lambda session: datetime(2026, 10, 19))
    monkeypatch.setattr(module, "rearm_outbox", lambda *args: None)
    identity = {"task_id": "task"}
    upstream = SimpleNamespace(factory=None, registry=None, _identity=lambda *args: identity,
                               _latest=lambda *args: SimpleNamespace(**identity))
    service = CallbackService(upstream)
    task = SimpleNamespace(id="task", state="INVESTIGATING", agent_id="agent",
                           agent_version="v1", upstream_id="original",
                           external_submission_id="submission",
                           investigation_reason="CALLBACK_EVENT_CONFLICT")
    binding = SimpleNamespace(wire_agent_id="copy", protocol_version="mock-v1",
                              adapter=SimpleNamespace(test_only=True))
    event = VerifiedEvent(status="VERIFIED", agent_id="copy", protocol_version="mock-v1",
                          test_only=True, event_id="original:1", sequence=1, state="RUNNING",
                          external_submission_id="submission", upstream_task_id="original")

    class InboxSession(EvidenceSession):
        def scalar(self, statement):
            if statement.column_descriptions[0]["name"] == "AgentEvent":
                return next(iter(self.rows.values()), None)
            return None

    session = InboxSession({})
    assert service._persist(session, task, binding, event, source, "raw").status == "ACCEPTED"
    expected_reason = ("CALLBACK_INBOX_PENDING:CALLBACK_EVENT_CONFLICT"
                       if source == "callback" else "CALLBACK_EVENT_CONFLICT")
    assert task.investigation_reason == expected_reason
    task.investigation_reason = "CALLBACK_EVENT_CONFLICT"
    assert service._persist(session, task, binding, event, source, "raw").status == "DUPLICATE"
    assert task.investigation_reason == "CALLBACK_EVENT_CONFLICT"


@pytest.mark.parametrize("blocker", ["UPSTREAM_NEEDS_INPUT", "CALLBACK_EVENT_CONFLICT"])
@pytest.mark.parametrize("sequence, disposition", [(1, "DUPLICATE"), (0, "STALE")])
def test_new_event_id_without_new_progress_preserves_manual_wait(
    monkeypatch, blocker, sequence, disposition,
):
    import app.agents.callbacks as module
    from app.agents.contracts import VerifiedEvent
    from app.agents.models import AgentEvent, AgentEventDecision
    from app.catalog.schemas import content_digest

    monkeypatch.setattr(module, "database_now", lambda session: datetime(2026, 10, 19))
    monkeypatch.setattr(module, "rearm_outbox", lambda *args: None)
    identity = {"task_id": "task"}
    task = SimpleNamespace(id="task", state="INVESTIGATING", state_version=5,
                           agent_id="agent", agent_version="v1", upstream_id="original",
                           external_submission_id="submission", investigation_reason=blocker)
    binding = SimpleNamespace(wire_agent_id="copy", protocol_version="mock-v1",
                              adapter=SimpleNamespace(test_only=True))
    event = VerifiedEvent(status="VERIFIED", agent_id="copy", protocol_version="mock-v1",
                          test_only=True, event_id="original:1", sequence=1, state="RUNNING",
                          external_submission_id="submission", upstream_task_id="original")
    prior = AgentEvent(id="prior", task_id="task", event_id=event.event_id, sequence=1,
                       semantic_digest=content_digest(event.model_dump(
                           mode="json", exclude={"status", "timestamp", "event_id"})))
    rows = [prior]
    decisions = {"prior": SimpleNamespace(disposition="APPLIED")}

    class InboxSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        @contextmanager
        def begin(self):
            yield

        def scalar(self, statement):
            if statement.column_descriptions[0]["name"] == "AgentEvent":
                key = statement.compile().params["event_id_1"]
                return next((row for row in rows if row.event_id == key), None)
            return None

        def scalars(self, statement):
            # The reducer's earlier read can predate a concurrent inbox commit.
            # A locking read must see both the current task marker and its row.
            visible = list(rows) if statement._for_update_arg is not None else [prior]
            return SimpleNamespace(all=lambda: visible)

        def get(self, model, key, **kwargs):
            return decisions.get(key) if model is AgentEventDecision else None

        def add(self, row):
            if isinstance(row, AgentEventDecision):
                decisions[row.event_ref] = row
            else:
                rows.append(row)

        def flush(self):
            pass

    upstream = SimpleNamespace(factory=InboxSession, registry=None,
                               _identity=lambda *args: identity,
                               _latest=lambda *args: SimpleNamespace(**identity),
                               _view=lambda task_id: task)
    upstream.recover_original_task = lambda *args, **kwargs: pytest.fail(
        "A duplicate/stale new event ID must not authorize remote transport")
    service = CallbackService(upstream)
    monkeypatch.setattr(module, "locked_execution", lambda *args: task)
    monkeypatch.setattr(service, "import_observations", lambda *args: None)
    monkeypatch.setattr(service, "install_verifiers", lambda *args: None)
    monkeypatch.setattr(service, "pending_failure", lambda *args: None)
    receipt = service._persist(InboxSession(), task, binding, event.model_copy(update={
        "event_id": "fresh-id", "sequence": sequence,
    }), "callback", "fresh-body")
    assert receipt.status == "ACCEPTED"
    assert task.investigation_reason == "CALLBACK_INBOX_PENDING:" + blocker
    second = service._persist(InboxSession(), task, binding, event.model_copy(update={
        "event_id": "second-fresh-id", "sequence": sequence,
    }), "callback", "second-fresh-body")
    assert second.status == "ACCEPTED"
    assert task.investigation_reason == "CALLBACK_INBOX_PENDING:" + blocker
    # Restart after both inbox receipts commit; no instance memory carries the block.
    service = CallbackService(upstream)
    monkeypatch.setattr(service, "import_observations", lambda *args: None)
    monkeypatch.setattr(service, "install_verifiers", lambda *args: None)
    monkeypatch.setattr(service, "pending_failure", lambda *args: None)
    result = service.poll_original_task("task", lease=SimpleNamespace(fencing_token=1))
    assert result.investigation_reason == blocker
    assert decisions[receipt.reference].disposition == disposition
    assert decisions[second.reference].disposition == disposition
