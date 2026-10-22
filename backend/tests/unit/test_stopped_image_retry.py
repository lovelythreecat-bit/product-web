from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.tasks import stopped_image_retry as retry


def stopped():
    task = SimpleNamespace(state="INVESTIGATING", settlement_state="FROZEN",
                           investigation_reason="UPSTREAM_NEEDS_INPUT", upstream_id="remote",
                           external_submission_id="original")
    execution = SimpleNamespace(kind="image", state={"status": "completed",
        "core_status": "needs_input", "upstream_task_id": "remote",
        "external_submission_id": "original"})
    return task, execution


@pytest.mark.parametrize("field,value", [("kind", "video"), ("status", "running"),
    ("core_status", "succeeded"), ("upstream_task_id", "other"),
    ("external_submission_id", "other")])
def test_stopped_retry_rejects_wrong_kind_state_or_identity(field, value):
    task, execution = stopped()
    assert retry.stopped_input(task, execution)
    if field == "kind":
        execution.kind = value
    else:
        execution.state[field] = value
    assert not retry.stopped_input(task, execution)


def test_retry_checks_owner_before_accessing_media_or_claiming_lease(monkeypatch):
    session = Mock()
    monkeypatch.setattr(retry.FailedTaskActions, "_owned", Mock(side_effect=HTTPException(404)))
    with pytest.raises(HTTPException) as denied:
        retry.prepare_stopped_image_retry(session, Mock(), "private-task", Mock())
    assert denied.value.status_code == 404
    session.get.assert_not_called()
    session.get_bind.assert_not_called()


@pytest.mark.parametrize("state", ["FAILED", "RUNNING", "SUCCEEDED"])
def test_existing_retry_states_do_not_query_or_change_media(monkeypatch, state):
    task, _ = stopped()
    task.state = state
    session = Mock()
    monkeypatch.setattr(retry.FailedTaskActions, "_owned", lambda *args: task)
    retry.prepare_stopped_image_retry(session, Mock(), "task", Mock())
    session.get.assert_not_called()
    session.rollback.assert_not_called()
