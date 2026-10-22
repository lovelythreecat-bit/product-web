"""Dispatch authorization without a database or Redis connection.

In-memory rows replace storage only; consumer routing and claim authorization run
unchanged. Real transaction races are covered by the dispatch fault suite.
"""

from contextlib import nullcontext
from datetime import datetime, timedelta

import pytest

from app.dispatch.consumer import TaskConsumer
from app.dispatch.models import OutboxEvent
from app.tasks.models import GenerationTask


@pytest.fixture
def dispatch(monkeypatch):
    current = datetime(2026, 10, 19, 1)
    task = GenerationTask(
        id="task", state="RUNNING", state_version=3, fencing_token=0,
        agent_id="agent", agent_version="1", external_submission_id="intent",
        upstream_id="original", recovery_due_at=current + timedelta(seconds=30),
    )
    event = OutboxEvent(
        event_id="event", task_id="task", state_version=3, operation="recover",
        ready_at=current,
    )
    event.dispatch_generation, event.claimed_generation = 2, 1

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def begin(self):
            return nullcontext()

        def scalar(self, query):
            model = query.column_descriptions[0]["entity"]
            return task if model is GenerationTask else event

        def get(self, model, key):
            return task if model is GenerationTask else event

    monkeypatch.setattr("app.dispatch.consumer.database_now", lambda session: current)
    seen = []
    consumer = TaskConsumer(Session, None, "stream", "group", "worker",
                            handlers={"query_original": seen.append})

    def release(lease):
        task.lease_owner = task.lease_expires_at = None
        return True

    monkeypatch.setattr(consumer.leases, "release", release)
    fields = {"event_id": "event", "task_id": "task", "state_version": "3",
              "dispatch_generation": "2"}
    return consumer, task, event, fields, seen, current


def test_same_generation_cannot_query_twice_after_release(dispatch):
    consumer, task, event, fields, seen, _ = dispatch
    assert consumer.process_message(fields) == "handled"
    assert consumer.process_message(fields) in {"rejected", "busy"}
    assert len(seen) == 1
    assert task.fencing_token == 1
    assert event.claimed_generation == 2


@pytest.mark.parametrize("invalid", ["version", "future", "generation", "legacy", "operation"])
def test_stale_or_early_message_never_queries_original(dispatch, invalid):
    consumer, task, event, fields, seen, current = dispatch
    if invalid == "version":
        task.state_version = 4
    elif invalid == "future":
        event.ready_at = current + timedelta(seconds=30)
    elif invalid == "generation":
        fields["dispatch_generation"] = "1"
    elif invalid == "legacy":
        del fields["dispatch_generation"]
    else:
        event.operation = "save"
    assert consumer.process_message(fields) in {"rejected", "busy"}
    assert not seen
    assert task.fencing_token == 0


def test_next_generation_at_same_task_version_remains_recoverable(dispatch):
    consumer, task, event, fields, seen, _ = dispatch
    assert consumer.process_message(fields) == "handled"
    event.dispatch_generation = 3
    fields["dispatch_generation"] = "3"
    assert consumer.process_message(fields) == "handled"
    assert len(seen) == 2
    assert task.state_version == 3


@pytest.mark.parametrize("reason", ["UPSTREAM_NEEDS_INPUT", "CALLBACK_EVENT_CONFLICT"])
def test_manual_wait_blocks_automatic_claim_but_allows_admin(dispatch, reason):
    consumer, task, _, fields, seen, _ = dispatch
    task.investigation_reason = reason
    assert consumer.process_message(fields) in {"rejected", "busy"}
    assert not seen
    assert consumer.leases.claim_task(task.id, "administrator") is not None


def test_rearm_first_generation_and_existing_generation_use_distinct_tokens():
    from app.dispatch.outbox import rearm_outbox

    task = GenerationTask(id="task", user_id="user", state_version=3)

    class Session:
        row = None

        def scalar(self, query):
            return task if query.column_descriptions[0]["entity"] is GenerationTask else self.row

        def add(self, row):
            self.row = row

        def flush(self):
            if self.row.dispatch_generation is None:
                self.row.dispatch_generation = 1
                self.row.claimed_generation = 0

        def execute(self, query):
            pass

    session = Session()
    first = rearm_outbox(session, task.id, "recover")
    assert first.dispatch_generation == 1
    first.claimed_generation = 1
    next_time = datetime(2026, 10, 19, 3)
    second = rearm_outbox(session, task.id, "recover", ready_at=next_time)
    assert second.event_id == first.event_id
    assert (second.dispatch_generation, second.claimed_generation) == (2, 1)
    assert second.ready_at == next_time
    assert second.dispatched_at is None


def test_handler_and_release_errors_are_diagnosed_without_sensitive_text(
    dispatch, monkeypatch, caplog, operations_log_capture
):
    consumer, _, _, fields, _, _ = dispatch

    def fail(*args):
        raise RuntimeError("TEST_ONLY_SECRET upstream response content")

    consumer.handlers["query_original"] = fail
    monkeypatch.setattr(consumer.leases, "release", fail)
    assert consumer.process_message(fields) == "failed"
    assert "TEST_ONLY_SECRET" not in caplog.text
    assert "STAGE_EXCEPTION" in caplog.text
    assert '"stage":"consume"' in caplog.text
