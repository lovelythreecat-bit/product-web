"""Durable imports use transaction fakes; no network or development database."""
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.agents.callbacks import CallbackService, EventReceipt
from app.tasks.state_machine import TransitionError


@pytest.fixture
def import_runtime(monkeypatch):
    import app.agents.callbacks as module

    state = SimpleNamespace(markers=[], writes=[], locks=set(), scanned=0, crash=False,
                            identity="original", rule="v1")
    task = SimpleNamespace(id="task", upstream_id="upstream")
    rows = [SimpleNamespace(id=str(i), task_id="task", attempt_id="attempt",
                            payload={"identity": "original"}, kind="observation")
            for i in range(1000)]
    rows.append(SimpleNamespace(id="changed", task_id="task", attempt_id="attempt",
                                payload={"identity": "changed"}, kind="observation"))

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            state.locks.discard(self)

        @contextmanager
        def begin(self):
            before = len(state.markers), len(state.writes)
            try:
                yield
                if state.crash:
                    raise RuntimeError("commit interrupted")
            except BaseException:
                del state.markers[before[0]:]
                del state.writes[before[1]:]
                raise

        def get(self, model, key):
            return task

        def scalars(self, statement):
            params = statement.compile().params
            if statement.column_descriptions[0]["name"] == "source_ref":
                context = params["context_digest_1"]
                return [m.source_ref for m in state.markers if m.context_digest == context
                        and m.source_ref in params["source_ref_1"]]
            assert statement.get_execution_options().get("yield_per") == 100
            context = params.get("context_digest_1")
            def history():
                for row in rows:
                    assert not state.locks, "History scan holds the account lock"
                    if any(m.source_ref == row.id and m.context_digest == context
                           for m in state.markers):
                        continue
                    state.scanned += 1
                    yield row
            return history()

        def scalar(self, statement):
            params = statement.compile().params
            return next((m for m in state.markers
                         if m.fingerprint == params["fingerprint_1"]
                         and m.context_digest == params["context_digest_1"]), None)

        def add_all(self, markers):
            state.markers.extend(markers)

        def flush(self):
            pass

    def lock(session, task_id, lease):
        state.locks.add(session)
        return task

    def verify(session, task, reference, kind):
        assert session in state.locks
        if reference == "changed":
            raise TransitionError("EVIDENCE_MISMATCH")

    binding = SimpleNamespace(wire_agent_id="copy", protocol_version="mock-v1",
                              endpoint_digest="endpoint", adapter=SimpleNamespace(test_only=True))
    outcome = SimpleNamespace(status="FOUND", state="RUNNING", protocol_version="mock-v1",
                              test_only=True, external_submission_id="submission",
                              upstream_task_id="upstream", result=None)
    upstream = SimpleNamespace(factory=Session, registry=SimpleNamespace(
        bind_task=lambda session, task: binding), _parse=lambda row: outcome,
        _verify_row=verify, _identity=lambda *args: {"identity": state.identity},
        _latest=lambda *args: SimpleNamespace(id="attempt"))
    monkeypatch.setattr(module, "locked_execution", lock)
    monkeypatch.setattr(module, "database_now", lambda session: datetime(2026, 10, 19))

    def service():
        callback = CallbackService(upstream)
        monkeypatch.setattr(callback, "_conflict", lambda *args, **kwargs:
                            state.writes.append("identity-conflict"))
        def persist(session, task, binding, event, source, digest, reference):
            assert session in state.locks
            state.writes.append(reference)
            return EventReceipt("CONFLICT", "prior-event")
        monkeypatch.setattr(callback, "_persist", persist)
        return callback
    return state, rows, service


def test_history_scan_does_not_hold_account_lock_and_rechecks_changed_payloads(import_runtime):
    state, rows, service = import_runtime
    service().import_observations("task", object())
    assert state.writes == ["0", "identity-conflict"]
    assert len(state.markers) == 1001
    assert not state.locks
    scanned = state.scanned
    service().import_observations("task", object())
    assert state.writes == ["0", "identity-conflict"]
    assert state.scanned == scanned, "Restart scanned already imported sources"
    rows.append(SimpleNamespace(id="new", task_id="task", attempt_id="attempt",
                                payload={"identity": "original"}, kind="observation"))
    service().import_observations("task", object())
    assert state.writes == ["0", "identity-conflict"]
    assert len(state.markers) == 1002


def test_failed_commit_does_not_cache_conflict_or_drop_sources(import_runtime):
    state, rows, service = import_runtime
    state.crash = True
    with pytest.raises(RuntimeError, match="commit interrupted"):
        service().import_observations("task", object())
    assert state.markers == []
    assert state.writes == []
    state.crash = False
    service().import_observations("task", object())
    assert state.writes == ["0", "identity-conflict"]
    assert len(state.markers) == 1001


def test_new_identity_and_rule_require_revalidation(import_runtime):
    state, _, service = import_runtime
    service().import_observations("task", object())
    state.identity = "new-snapshot"
    service().import_observations("task", object())
    assert state.writes == ["0", "identity-conflict"] * 2
    service().import_observations("task", object(), rule_version="observation-v2")
    assert state.writes == ["0", "identity-conflict"] * 3


@pytest.mark.parametrize("lost", [False, True])
def test_history_scan_renews_lease_without_account_lock_and_fails_closed(
    import_runtime, monkeypatch, lost,
):
    import app.agents.callbacks as module

    state, _, service = import_runtime
    callback = service()
    clock = iter(range(0, 100000, 21))
    monkeypatch.setattr(module, "monotonic", lambda: next(clock), raising=False)
    renewed = []
    def renew(lease):
        assert not state.locks
        renewed.append(lease)
        return None if lost else lease
    callback.upstream.leases = SimpleNamespace(renew=renew)
    if lost:
        with pytest.raises(TransitionError, match="LEASE_LOST"):
            callback.import_observations("task", object())
        assert state.markers == []
        assert state.writes == []
    else:
        callback.import_observations("task", object())
        assert state.writes == ["0", "identity-conflict"]
        assert len(state.markers) == 1001
    assert renewed
