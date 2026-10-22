"""Event persistence and idle stream behavior without database fixtures or SQL I/O."""

from contextlib import nullcontext
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agents.media_execution import MediaExecution, MediaTaskStore
from app.auth.models import User
from app.events import routes
from app.events.models import DurableEvent, EventHead, EventReceipt
from app.events.service import payload_digest
from app.tasks.models import GenerationTask


class EventSession:
    def __init__(self):
        self.task = SimpleNamespace(id=str(uuid4()), user_id=str(uuid4()),
                                    conversation_id=str(uuid4()), state="RUNNING", state_version=3)
        self.execution = SimpleNamespace(kind="video", state={"status": "planning"}, revision=1)
        self.head = SimpleNamespace(last_seq=0, pruned_through=0)
        self.added, self.queries = [], []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def begin(self):
        return nullcontext()

    def get(self, model, identity, **kwargs):
        return self.execution if model is MediaExecution else self.head

    def scalar(self, statement):
        self.queries.append(statement)
        entity = statement.column_descriptions[0].get("entity")
        return {User: SimpleNamespace(id=self.task.user_id), GenerationTask: self.task,
                EventReceipt: None, EventHead: self.head, DurableEvent: None}.get(entity)

    def add(self, row):
        self.added.append(row)

    def flush(self):
        pass


def test_media_public_changes_emit_durable_events_in_the_state_transaction(monkeypatch):
    from app.tasks import repository

    session = EventSession()
    monkeypatch.setattr(repository, "locked_execution", lambda *args: session.task)
    store = MediaTaskStore(lambda: session, session.task.id, "video", lease=object())
    store.save({"status": "awaiting_confirmation", "head_plan_version": 2})
    events = [row for row in session.added if isinstance(row, DurableEvent)]
    assert len(events) == 1
    assert events[0].payload == {
        "task_id": session.task.id, "state": "RUNNING", "state_version": 3,
        "media_revision": 2, "conversation_id": session.task.conversation_id,
    }
    assert events[0].user_id == session.task.user_id
    assert session.head.last_seq == 1
    assert session.execution.state["status"] == "awaiting_confirmation"
    assert session.task.state_version == 3
    store.save({"uploads": {"material": {"private": "upstream-id"}}})
    store.save({"status": "awaiting_confirmation"})
    assert len([row for row in session.added if isinstance(row, DurableEvent)]) == 1


def test_event_digests_preserve_old_receipts_and_distinguish_media_revisions():
    payload = {"task_id": str(uuid4()), "state": "RUNNING", "state_version": 3}
    expected = sha256(f"task.updated|{payload['task_id']}|RUNNING|3".encode()).hexdigest()
    assert payload_digest("task.updated", payload) == expected
    assert payload_digest("task.updated", {**payload, "conversation_id": str(uuid4())}) == expected
    assert payload_digest("task.updated", {**payload, "media_revision": 1}) != payload_digest(
        "task.updated", {**payload, "media_revision": 2})


def test_idle_stream_reads_do_not_lock_users_or_prune_unexpired_events(monkeypatch):
    session = EventSession()
    principal = SimpleNamespace(user_id=session.task.user_id)
    monkeypatch.setattr(routes, "Session", lambda engine: session)
    monkeypatch.setattr(routes.AuthService, "require_active_principal",
                        lambda *args, **kwargs: principal)

    def unexpected_prune(*args):
        pytest.fail("Idle delivery must not acquire retention write locks")

    monkeypatch.setattr(routes, "prune_events", unexpected_prune)
    cursor = f"{session.task.user_id}:0"
    assert routes.read_next(None, "cookie", principal, cursor, 86400, None, None) == (
        cursor, None, False)
    assert all(query._for_update_arg is None for query in session.queries)


def test_media_projection_exposes_revision_for_out_of_order_gets():
    from app.agents.media_execution import public_media_state

    assert public_media_state("video", {"status": "planning"}, revision=4) == {
        "kind": "video", "status": "planning", "revision": 4}
