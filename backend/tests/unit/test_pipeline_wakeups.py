"""Exercise the actual browser drive method against an isolated in-memory record set."""

from contextlib import nullcontext
from threading import RLock
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.auth.models import User
from app.dispatch.models import OutboxEvent
from app.tasks.models import GenerationTask
from tests.browser_support.runtime import Runtime


def driver(*, state="RUNNING", reason=None):
    task = SimpleNamespace(id=str(uuid4()), user_id=str(uuid4()), agent_id="test-agent",
                           state=state, state_version=7, upstream_id="original",
                           investigation_reason=reason)
    stale = OutboxEvent(event_id=str(uuid4()), task_id=task.id, user_id=task.user_id,
                        state_version=1, operation="submit", dispatch_generation=1,
                        claimed_generation=1)
    operation = "save" if state in {"SAVING", "SAVE_RECOVERY"} else "recover"
    current = OutboxEvent(event_id=str(uuid4()), task_id=task.id, user_id=task.user_id,
                          state_version=7, operation=operation, dispatch_generation=3,
                          claimed_generation=3)
    records, delivered = [stale, current], []
    owner = SimpleNamespace(account_normalized="TEST_ONLY_run:user")

    class Session:
        def begin(self):
            return nullcontext()

        def get(self, model, key):
            if model is GenerationTask:
                return task if key == task.id else None
            if model is User:
                return owner
            raise AssertionError("Unexpected record type")

        def scalar(self, query):
            if query.column_descriptions[0]["entity"] is GenerationTask:
                return task
            params = query.compile().params
            return next((row for row in records
                         if row.task_id == params["task_id_1"]
                         and row.state_version == params["state_version_1"]
                         and row.operation == params["operation_1"]), None)

        def add(self, row):
            records.append(row)

        def flush(self):
            for row in records:
                if row.dispatch_generation is None:
                    row.dispatch_generation, row.claimed_generation = 1, 0

        def execute(self, statement):
            return None

    runtime = Runtime.__new__(Runtime)
    runtime.lock, runtime.owned = RLock(), [task.id]
    runtime.prefix, runtime.agents = "TEST_ONLY_run:", {"text": task.agent_id}
    runtime.factory = lambda: nullcontext(Session())
    runtime.worker = SimpleNamespace(consumer=SimpleNamespace(
        process_message=lambda fields: delivered.append(fields) or "handled",
    ))
    runtime.inspect = lambda task_id: {"task_id": task_id, "state": task.state}
    return runtime, task, owner, records, delivered


@pytest.mark.parametrize("state,operation", [
    ("RUNNING", "recover"), ("INVESTIGATING", "recover"),
    ("SAVING", "save"), ("SAVE_RECOVERY", "save"),
])
def test_drive_rearms_current_stage_and_delivers_persisted_generation(state, operation):
    runtime, task, _, records, delivered = driver(state=state)
    assert runtime.drive(task.id)["state"] == state
    assert delivered == [{"event_id": records[1].event_id, "task_id": task.id,
                          "state_version": "7", "dispatch_generation": "4"}]
    assert records[1].operation == operation
    assert records[0].state_version == 1 and records[0].dispatch_generation == 1
    runtime.drive(task.id)
    assert delivered[-1]["dispatch_generation"] == "5"
    assert len(records) == 2


@pytest.mark.parametrize("violation", ["unregistered", "different_owner", "different_agent"])
def test_drive_cannot_wake_tasks_outside_the_test_run(violation):
    runtime, task, owner, records, delivered = driver()
    if violation == "unregistered":
        runtime.owned.clear()
    elif violation == "different_owner":
        owner.account_normalized = "another-run:user"
    else:
        task.agent_id = "another-agent"
    with pytest.raises(ValueError, match="outside this run"):
        runtime.drive(task.id)
    assert not delivered
    assert records[1].dispatch_generation == 3


@pytest.mark.parametrize("state,reason", [
    ("INVESTIGATING", "UPSTREAM_NEEDS_INPUT"),
    ("INVESTIGATING", "CALLBACK_EVENT_CONFLICT"),
    ("SUCCEEDED", None), ("FAILED", None), ("MANUALLY_CLOSED", None),
])
def test_drive_does_not_rearm_terminal_or_manual_wait_tasks(state, reason):
    runtime, task, _, records, delivered = driver(state=state, reason=reason)
    assert runtime.drive(task.id)["state"] == state
    assert not delivered and records[1].dispatch_generation == 3
