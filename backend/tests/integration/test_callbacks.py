"""T10 callbacks exercise the real HTTP boundary and MySQL persistence."""

import hashlib
import hmac
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agents.mock_server import CALLBACK_KEY
from app.main import create_app
from app.tasks.models import GenerationTask
from tests.faults.test_upstream_recovery import calls, facts, submit
from tests.faults.test_upstream_recovery import upstream as upstream_fixture

upstream = upstream_fixture


@pytest.fixture
def callbacks(upstream, mysql_settings):
    with TestClient(create_app(mysql_settings)) as client:
        yield client


def event_for(runtime, task_id, index=1):
    factory, _, _, server, _ = runtime
    with factory() as s:
        task = s.get(GenerationTask, task_id)
        binding = runtime[1].registry.bind_task(s, task)
        _, body = server.simulator.events(binding.wire_agent_id, task.external_submission_id)
        event = body["events"][index]
        return f"/api/v1/agent-callbacks/{task.agent_id}/{task.agent_version}", event


def changed(event, **values):
    payload = json.loads(event["raw"])
    payload.update(values)
    raw = json.dumps(payload).encode()
    return dict(
        raw=raw,
        headers={"X-Mock-Signature": hmac.new(CALLBACK_KEY, raw, hashlib.sha256).hexdigest()},
    )


def post(client, path, event):
    return client.post(path, content=event["raw"], headers=event["headers"])


def reducer(runtime):
    import app.agents.upstream as module

    assert callable(getattr(module.UpstreamService, "poll_original_task", None)), (
        "UpstreamService must expose durable original-task polling"
    )
    return runtime[1]


def test_forged_cross_agent_task(upstream, callbacks):
    task = upstream[2]()
    other = upstream[2](kind="image")
    submit(upstream, task)
    submit(upstream, other)
    path, event = event_for(upstream, task)
    other_path, _ = event_for(upstream, other)
    assert (
        post(callbacks, path, dict(event, headers={"X-Mock-Signature": "0" * 64})).status_code
        == 403
    )
    assert post(callbacks, other_path, event).status_code == 403
    wrong_id = str(uuid4())
    assert (
        post(
            callbacks, path, changed(event, upstream_task_id=wrong_id, event_id=f"{wrong_id}:2")
        ).status_code
        == 409
    )
    assert post(callbacks, path, changed(event, user_id=str(uuid4()))).status_code == 403
    assert facts(upstream[0], task)[-1] == "frozen"


@pytest.mark.parametrize("kind", ["copy", "image", "video"])
def test_duplicate_out_of_order_terminal(upstream, callbacks, kind):
    task = upstream[2](kind=kind)
    submit(upstream, task)
    path, ready = event_for(upstream, task)
    assert post(callbacks, path, ready).status_code == 202
    # New app + adapter instance cannot erase MySQL replay protection.
    assert post(callbacks, path, ready).json()["status"] == "DUPLICATE"
    service = reducer(upstream)
    assert service.poll_original_task(task).state == "SAVING"
    _, running = event_for(upstream, task, 0)
    assert post(callbacks, path, running).status_code == 202
    before = service._view(task).state_version
    assert service.poll_original_task(task).state_version == before
    from app.agents.models import AgentEvent, AgentEventDecision

    with upstream[0]() as s:
        events = s.scalars(select(AgentEvent).where(AgentEvent.task_id == task)).all()
        decisions = s.scalars(
            select(AgentEventDecision).where(AgentEventDecision.task_id == task)
        ).all()
        assert len(events) == 2
        assert {d.disposition for d in decisions} == {"APPLIED", "STALE"}
    assert facts(upstream[0], task)[-1] == "frozen"
    assert calls(upstream, task)["submit"] == 1


def test_same_event_changed_payload_is_durable_conflict(upstream, callbacks):
    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    assert post(callbacks, path, event).status_code == 202
    assert post(callbacks, path, changed(event, state="FAILED", result=None)).status_code == 409
    from app.agents.models import UpstreamEvidence

    with upstream[0]() as s:
        assert s.scalar(
            select(UpstreamEvidence).where(
                UpstreamEvidence.task_id == task, UpstreamEvidence.kind == "callback_conflict"
            )
        )


def test_failed_notification_keeps_freeze_and_durable_evidence(upstream, callbacks):
    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    assert post(callbacks, path, changed(event, state="FAILED", result=None)).status_code == 202
    service = reducer(upstream)
    assert service.poll_original_task(task).state == "INVESTIGATING"
    assert service.pending_failure(task) is not None
    assert facts(upstream[0], task)[-1] == "frozen"


def test_callback_does_not_steal_worker_lease(upstream, callbacks):
    from app.dispatch.consumer import LeaseManager

    task = upstream[2]()
    submit(upstream, task)
    manager = LeaseManager(upstream[0])
    lease = manager.claim_task(task, "TEST_ONLY_busy")
    path, event = event_for(upstream, task)
    assert post(callbacks, path, event).status_code == 202
    assert reducer(upstream).poll_original_task(task).state == "RUNNING"
    manager.release(lease)
    assert reducer(upstream).poll_original_task(task).state == "SAVING"


@pytest.mark.parametrize(
    "mutation",
    [
        {"timestamp": 0},
        {"timestamp": 99999999999},
        {"sequence": True},
        {"sequence": 3},
        {"event_id": "different-nonce"},
        {"protocol_version": "unknown"},
        {"test_only": False},
        {"status": "VERIFIED"},
        {"agent_id": "video"},
    ],
)
def test_wire_shape_time_nonce_and_origin_rejected(upstream, callbacks, mutation):
    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    assert post(callbacks, path, changed(event, **mutation)).status_code == 403
    assert upstream[1]._view(task).state == "RUNNING"


def test_same_sequence_callback_poll_conflict_preserves_first_result(upstream, callbacks):
    factory, service, create, server, _ = upstream
    task = create()
    submit(upstream, task)
    # Query first: durable sequence 2. A later signed failure cannot replace it.
    assert reducer(upstream).poll_original_task(task).state == "SAVING"
    path, event = event_for(upstream, task)
    assert post(callbacks, path, changed(event, state="FAILED", result=None)).status_code == 202
    assert service.poll_original_task(task).state == "SAVING"
    assert service.pending_failure(task) is None
    from app.agents.models import AgentEventDecision

    with factory() as s:
        assert s.scalar(
            select(AgentEventDecision).where(
                AgentEventDecision.task_id == task, AgentEventDecision.disposition == "CONFLICT"
            )
        )


@pytest.mark.parametrize("bad", ["partial", "locator", "media_type", "item_key", "count"])
def test_untrusted_manifest_cannot_enter_saving(upstream, callbacks, bad):
    task = upstream[2]("query_unavailable")
    submit(upstream, task)
    path, event = event_for(upstream, task)
    result = json.loads(event["raw"])["result"]
    if bad == "partial":
        result["complete"] = False
    elif bad == "count":
        result["expected_items"] = 2
        result["items"].append(dict(result["items"][0], item_key="original-2"))
    else:
        result["items"][0][bad] = "https://untrusted.invalid/file"
    assert post(callbacks, path, changed(event, result=result)).status_code == 202
    assert reducer(upstream).poll_original_task(task).state == "INVESTIGATING"
    assert reducer(upstream).original_result(task) is None
    assert facts(upstream[0], task)[-1] == "frozen"


def test_concurrent_receipts_reduce_once(upstream, callbacks):
    from concurrent.futures import ThreadPoolExecutor

    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: post(callbacks, path, event).json()["status"], range(2)))
    assert sorted(results) == ["ACCEPTED", "DUPLICATE"]
    service = reducer(upstream)
    assert service.poll_original_task(task).state == "SAVING"
    before = service._view(task).state_version
    assert service.poll_original_task(task).state_version == before


def test_public_verified_dto_without_signature_is_rejected(upstream, callbacks):
    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    body = json.loads(event["raw"]) | {"status": "VERIFIED"}
    assert callbacks.post(path, json=body).status_code == 403


def test_terminal_late_event_is_audited_without_state_or_settlement(upstream, callbacks):
    # Terminal fixture represents T12 having completed settlement; T10 never does so.
    from sqlalchemy import text

    from app.agents.models import AgentEventDecision

    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    with upstream[0]() as s, s.begin():
        s.execute(
            text(
                "UPDATE generation_tasks SET state='FAILED', settlement_state='RELEASED' "
                "WHERE id=:id"
            ),
            {"id": task},
        )
    before = upstream[1]._view(task)
    assert post(callbacks, path, event).status_code == 202
    assert reducer(upstream).poll_original_task(task) == before
    with upstream[0]() as s:
        assert (
            s.scalar(
                select(AgentEventDecision.disposition).where(AgentEventDecision.task_id == task)
            )
            == "TERMINAL_LATE"
        )


def test_production_and_unknown_version_fail_closed(upstream, mysql_settings):
    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    app = create_app(mysql_settings.model_copy(update={"mode": "production", "test_only": False}))
    with TestClient(app) as client:
        assert post(client, path, event).status_code == 403
    with TestClient(create_app(mysql_settings)) as client:
        assert post(client, path.replace("TEST_ONLY_v1", "unknown"), event).status_code == 403


def test_original_result_handoff_is_bound_to_durable_identity(upstream):
    task = upstream[2]()
    submit(upstream, task)
    service = reducer(upstream)
    service.poll_original_task(task)
    delivery = service.original_result(task)
    assert getattr(delivery, "task_id", None) == task
    assert delivery.manifest.complete
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        assert (
            delivery.agent_id,
            delivery.agent_version,
            delivery.external_submission_id,
            delivery.upstream_id,
        ) == (row.agent_id, row.agent_version, row.external_submission_id, row.upstream_id)
    assert delivery.reference


def test_changed_raw_bytes_under_same_nonce_conflict(upstream, callbacks):
    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    assert post(callbacks, path, event).status_code == 202
    # Equivalent JSON has different raw signed bytes. Nonce cannot be reused for it.
    assert post(callbacks, path, changed(event)).status_code == 409


def test_callback_before_upstream_binding_recovers_original(upstream, callbacks):
    task = upstream[2]("lost_response")
    submit(upstream, task)
    path, event = event_for(upstream, task)
    assert post(callbacks, path, event).status_code == 202
    assert reducer(upstream).poll_original_task(task).state == "SAVING"
    assert calls(upstream, task)["submit"] == 1
    assert calls(upstream, task)["query_external"] == 0


def test_expired_fencing_cannot_apply_receipt(upstream, callbacks):
    from app.agents.callbacks import CallbackService
    from app.dispatch.consumer import LeaseManager
    from app.tasks.state_machine import TransitionError

    task = upstream[2]()
    submit(upstream, task)
    path, event = event_for(upstream, task)
    post(callbacks, path, event)
    manager = LeaseManager(upstream[0])
    old = manager.claim_task(task, "TEST_ONLY_old")
    manager.release(old)
    new = manager.claim_task(task, "TEST_ONLY_new")
    with pytest.raises(TransitionError, match="LEASE_LOST"):
        CallbackService(upstream[1]).reduce_pending(task, old)
    assert upstream[1]._view(task).state == "RUNNING"
    manager.release(new)
    assert reducer(upstream).poll_original_task(task).state == "SAVING"


def test_conflicting_receipt_cannot_be_reused_as_original_result_proof(upstream, callbacks):
    from app.agents.callbacks import CallbackService
    from app.agents.models import AgentEventDecision
    from app.tasks.state_machine import TransitionError

    task = upstream[2]()
    submit(upstream, task)
    reducer(upstream).poll_original_task(task)
    path, event = event_for(upstream, task)
    result = json.loads(event["raw"])["result"]
    result["items"][0]["sha256"] = "0" * 64
    assert post(callbacks, path, changed(event, result=result)).status_code == 202
    reducer(upstream).poll_original_task(task)
    with upstream[0]() as s:
        ref = s.scalar(
            select(AgentEventDecision.event_ref).where(
                AgentEventDecision.task_id == task, AgentEventDecision.disposition == "CONFLICT"
            )
        )
        with pytest.raises(TransitionError, match="EVIDENCE"):
            CallbackService(upstream[1]).verify_original_result(
                s, s.get(GenerationTask, task), "SAVING", ref
            )
