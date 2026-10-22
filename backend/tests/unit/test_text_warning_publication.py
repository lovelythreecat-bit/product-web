import json
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.results.persistence import DurableItem
from app.results.publisher import ResultPublisher


def test_publication_carries_warnings_separately_from_the_original_text():
    delivery = SimpleNamespace(
        manifest_id="manifest", warnings=("材质待核实",),
        items=(DurableItem("original-1", "file", "v1", "a" * 64, 6, "text/plain"),),
    )
    content = ResultPublisher._content(delivery, "work", (("original-1", "正文"),))
    assert content["warnings"] == ["材质待核实"]
    assert content["items"][0]["text"] == "正文"


def test_old_publication_content_does_not_gain_empty_metadata():
    delivery = SimpleNamespace(manifest_id="manifest", warnings=(), items=())
    content = ResultPublisher._content(delivery, "work", ())
    assert content == {"work_ids": ["work"], "manifest_id": "manifest", "items": []}


def publisher_case(*, state="RUNNING", reason=None, advance=False):
    task = SimpleNamespace(id=str(uuid4()), state=state, state_version=4,
                           investigation_reason=reason, settlement_state="FROZEN")

    def handle(context):
        if advance:
            task.state_version += 1
            task.state = "SAVING"

    upstream = SimpleNamespace(pending_failure=lambda _: None, handle=handle,
                               original_result=lambda _: None)
    session = SimpleNamespace(get=lambda *args: task, scalar=lambda *args: None)
    publisher = ResultPublisher(SimpleNamespace(factory=lambda: nullcontext(session),
                                                upstream=upstream, store=None))
    context = SimpleNamespace(task_id=task.id, state_version=4, action="query_original",
                              lease=SimpleNamespace(fencing_token=2))
    return publisher, task, context


def test_publisher_no_progress_is_diagnosed_without_mutating_task(caplog, operations_log_capture):
    publisher, task, context = publisher_case()
    assert publisher.handle(context) is None
    events = [json.loads(row.message) for row in caplog.records
              if row.name == "operations"]
    assert any(event.get("code") == "NO_PROGRESS" and event.get("outcome") == "no_progress"
               and event.get("task_id") == task.id and event.get("state_version") == 4
               and event.get("fencing_token") == 2 for event in events)
    assert task.state == "RUNNING" and task.state_version == 4
    assert task.settlement_state == "FROZEN"


@pytest.mark.parametrize("reason", ["UPSTREAM_NEEDS_INPUT", "CALLBACK_EVENT_CONFLICT"])
def test_publisher_manual_wait_reports_wait_not_no_progress(caplog, reason, operations_log_capture):
    publisher, task, context = publisher_case(state="INVESTIGATING", reason=reason)
    assert publisher.handle(context) is None
    events = [json.loads(row.message) for row in caplog.records if row.name == "operations"]
    assert any(event.get("code") == reason and event.get("outcome") == "wait"
               for event in events)
    assert "NO_PROGRESS" not in caplog.text
    assert task.investigation_reason == reason and task.settlement_state == "FROZEN"


@pytest.mark.parametrize("state", ["SUCCEEDED", "FAILED", "MANUALLY_CLOSED"])
def test_publisher_terminal_replay_is_not_no_progress(caplog, state, operations_log_capture):
    publisher, _, context = publisher_case(state=state)
    publisher.handle(context)
    assert "NO_PROGRESS" not in caplog.text


def test_publisher_successful_stage_change_is_not_no_progress(caplog, operations_log_capture):
    publisher, task, context = publisher_case(advance=True)
    assert publisher.handle(context) is None
    assert task.state == "SAVING" and task.state_version == 5
    assert "NO_PROGRESS" not in caplog.text
