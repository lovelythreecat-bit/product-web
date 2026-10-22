"""Real SQL leases/receipts, shared async slots and controlled media HTTP."""

import json
from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.agents.execution_pool import MediaExecutionPool, execution_scope
from app.agents.image import ImageAgentAdapter
from app.agents.media_execution import MediaExecution, MediaTaskStore, new_execution
from app.agents.models import UpstreamAttempt
from app.agents.registry import AgentBinding
from app.agents.upstream import UpstreamService
from app.catalog.schemas import content_digest
from app.ledger.models import CreditLedger
from app.tasks.models import GenerationTask
from tests.integration.test_image_agent_pipeline import image_http_runtime as image_http_fixture
from tests.t12_fixtures import upstream as upstream_fixture

upstream = upstream_fixture
image_http_runtime = image_http_fixture


@pytest.fixture
def image_queue(upstream, image_http_runtime):
    factory, _, create, _, _ = upstream
    original_adapter, snapshot, _, remote = image_http_runtime
    prototype = original_adapter()

    def stamp(connection, target):
        target.agent_snapshot = dict(target.agent_snapshot, protocol_version="image-agent-v1")
        target.input_snapshot = deepcopy(snapshot["input_snapshot"])

    task_id = create(kind="image", snapshot_transform=stamp)
    with factory.begin() as session:
        session.add(new_execution(task_id, "image"))

    class Registry:
        settings = None

        def bind_task(self, session, task):
            from app.dispatch.consumer import Lease

            lease = (Lease(task.id, task.lease_owner, task.fencing_token, task.lease_expires_at)
                     if task.lease_owner else None)
            state = MediaTaskStore(factory, task.id, "image", lease)
            adapter = ImageAgentAdapter(
                profile=prototype.profile, external_submission_id=task.external_submission_id,
                load_state=state.load, save_state=state.save,
                authorize_submission_retry=state.can_retry_rejected_submission,
                material_loader=prototype.material_loader,
            )
            return AgentBinding(task.agent_id, task.agent_version, "image", "image-agent-v1",
                                content_digest(prototype.profile.base_url), adapter)

    service = UpstreamService(factory, Registry())

    def submit():
        lease = service.leases.claim_task(task_id, "TEST_ONLY_image_queue")
        assert lease is not None
        try:
            return service.submit_original_task(task_id, lease)
        finally:
            service.leases.release(lease)

    def due():
        with factory.begin() as session:
            session.execute(text("UPDATE generation_tasks "
                                 "SET submission_not_before=UTC_TIMESTAMP(6) "
                                 "WHERE id=:id"), {"id": task_id})

    return factory, service, task_id, submit, due, remote, create, prototype.profile


def test_image_queue_refusal_retries_under_real_durable_authorization(image_queue):
    factory, service, task_id, submit, due, remote, _, profile = image_queue
    assert submit().state == "QUEUED"
    assert submit().state == "QUEUED"
    assert len(remote["posts"]) == 1
    due()
    assert submit().state == "RUNNING"
    assert len(remote["posts"]) == 2
    assert json.loads(remote["posts"][0][0]) == json.loads(remote["posts"][1][0])
    assert remote["posts"][0][1] == remote["posts"][1][1]
    assert len(remote["uploads"]) == 1
    with factory() as session:
        assert len(session.scalars(select(UpstreamAttempt).where(
            UpstreamAttempt.task_id == task_id,
        )).all()) == 2
        assert session.get(GenerationTask, task_id).settlement_state == "FROZEN"
        kinds = session.scalars(select(CreditLedger.kind).where(
            CreditLedger.task_id == task_id,
        )).all()
        assert kinds.count("freeze") == 1 and "consume" not in kinds and "release" not in kinds
    scope = execution_scope("image-agent-v1", profile.base_url)
    pool = MediaExecutionPool(factory, 1)
    assert pool.acquire(scope, str(uuid4())) is None, "202 must retain its async execution slot"


def test_image_retry_disconnect_cannot_reuse_earlier_refusal(image_queue):
    _, service, task_id, submit, due, remote, _, _ = image_queue
    remote["scenario"] = "full_then_disconnect"
    assert submit().state == "QUEUED"
    due()
    assert submit().state == "INVESTIGATING"
    assert service.recover_original_task(task_id).state == "INVESTIGATING"
    assert len(remote["posts"]) == 2


def test_image_restart_after_durable_marker_before_receipt_can_requeue(image_queue, monkeypatch):
    _, service, task_id, submit, due, remote, _, _ = image_queue
    observe = service._observe
    monkeypatch.setattr(service, "_observe", lambda *a, **kw: (
        _ for _ in ()).throw(RuntimeError("stopped after adapter rejection marker")))
    with pytest.raises(RuntimeError, match="stopped after"):
        submit()
    monkeypatch.setattr(service, "_observe", observe)
    assert service.recover_original_task(task_id).state == "QUEUED"
    due()
    assert submit().state == "RUNNING"
    assert len(remote["posts"]) == 2 and len(remote["uploads"]) == 1


def test_image_full_local_pool_never_uploads_or_creates_attempt(image_queue):
    factory, service, task_id, submit, due, remote, create, profile = image_queue
    scope = execution_scope("image-agent-v1", profile.base_url)
    pool = MediaExecutionPool(factory, 6)
    holders = [create(kind="image") for _ in range(6)]
    for owner in holders:
        assert pool.acquire(scope, owner) == owner
    assert submit().state == "QUEUED"
    assert remote["posts"] == [] and remote["uploads"] == []
    with factory() as session:
        assert session.scalar(select(UpstreamAttempt).where(
            UpstreamAttempt.task_id == task_id,
        )) is None
    pool.release(scope, holders[0])
    due()
    # First real POST reaches the controlled upstream's queue refusal.
    assert submit().state == "QUEUED"
    assert len(remote["posts"]) == 1


def test_video_waiting_plan_releases_slot_but_inflight_confirmation_keeps_it(upstream):
    factory, _, create, _, _ = upstream
    first, second, third = [create(kind="video") for _ in range(3)]
    scope = execution_scope("video-agent-v1", f"http://{uuid4().hex}.invalid:8015")
    pool = MediaExecutionPool(factory, 1)
    with factory.begin() as session:
        row = new_execution(first, "video")
        row.state = {"status": "planning"}
        session.add(row)
    assert pool.acquire(scope, first) == first
    assert pool.acquire(scope, second) is None
    with factory.begin() as session:
        session.get(MediaExecution, first).state = {"status": "awaiting_confirmation"}
    assert pool.acquire(scope, second) == second
    pool.release(scope, second)
    assert pool.acquire(scope, first, phase="confirm") == first
    assert pool.acquire(scope, third) is None, "Confirm HTTP has not updated upstream status yet"


@pytest.mark.parametrize("operation", ["confirm", "inputs", "revise"])
def test_explicit_video_command_waits_locally_then_worker_runs_same_command(upstream, operation):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    from app.agents.media_execution import MediaCommand, new_command
    from app.agents.video import VideoAgentAdapter, VideoAgentProfile
    from app.agents.video_commands import (
        execute_video_command,
        queue_authorized_command,
        resume_queued_video_command,
    )

    factory, _, create, _, _ = upstream

    def stamp(connection, snapshot):
        snapshot.agent_snapshot = dict(snapshot.agent_snapshot, protocol_version="video-agent-v1")

    task_id = create(kind="video", snapshot_transform=stamp)
    blocker = create(kind="video")
    upstream_id, generation_id = str(uuid4()), str(uuid4())
    with factory() as session:
        task = session.get(GenerationTask, task_id)
        body = {"product_info": {"name": "TEST_ONLY cup", "category": None,
                  "selling_points": [], "specs": None, "extra": {}},
                "user_prompt": "original", "images": [str(uuid4())],
                "first_frame_asset_id": str(uuid4()), "video_options": {}, "audio_options": {},
                "external_request_id": task.external_submission_id,
                "external_user_id": task.user_id}
    posted = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            suffix = "plan-revisions" if operation == "revise" else "confirm"
            assert self.path == f"/api/v1/tasks/{upstream_id}/{suffix}"
            self.reply_command()

        def do_PATCH(self):
            assert self.path == f"/api/v1/tasks/{upstream_id}/inputs"
            self.reply_command()

        def reply_command(self):
            posted.append((self.headers["Idempotency-Key"],
                           json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            view = {**body, "task_id": upstream_id, "head_plan_version": 2,
                    "image_asset_ids": body["images"]}
            if operation == "confirm":
                view.update(status="generating", confirmed_plan_version=2,
                            generation_id=generation_id)
            elif operation == "inputs":
                view.update(status="planning", user_prompt=upstream_body["user_prompt"])
            else:
                view.update(status="planning")
            data = json.dumps(view).encode()
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    profile = VideoAgentProfile(base_url=f"http://127.0.0.1:{server.server_port}",
                               service_key="TEST_ONLY_video_key", max_result_bytes=8192)

    class Registry:
        settings = None

        def bind_task(self, session, task):
            from app.dispatch.consumer import Lease

            lease = Lease(task.id, task.lease_owner, task.fencing_token, task.lease_expires_at)
            store = MediaTaskStore(factory, task.id, "video", lease)
            adapter = VideoAgentAdapter(profile=profile,
                external_submission_id=task.external_submission_id,
                load_state=store.load, save_state=store.save)
            return AgentBinding(task.agent_id, task.agent_version, "video", "video-agent-v1",
                                content_digest(profile.base_url), adapter)

    with factory.begin() as session:
        task = session.get(GenerationTask, task_id)
        task.state, task.upstream_id = "RUNNING", upstream_id
        row = new_execution(task_id, "video")
        row.state = {"request_body": body, "upstream_task_id": upstream_id,
                     "status": ("awaiting_confirmation" if operation in {"confirm", "revise"}
                                else "awaiting_input"),
                     "head_plan_version": 2,
                     "plan": {"task_id": upstream_id, "plan_version": 2}}
        session.add(row)
        upstream_body = ({"plan_version": 2} if operation == "confirm" else
                         {"plan_version": 2, "instruction": "TEST_ONLY replan"}
                         if operation == "revise" else
                         {"user_prompt": "original\n补充资料：extra"})
        command = new_command(task_id, operation, "TEST_ONLY_original_confirmation", upstream_body)
        command.request = {"input": upstream_body, "upstream_body": upstream_body}
        session.add(command)
        command_id = command.id
        queue_authorized_command(session, task, row, command_id)
    service = UpstreamService(factory, Registry())
    scope = execution_scope("video-agent-v1", profile.base_url)
    pool = service.media_pools["video-agent-v1"]
    assert pool.acquire(scope, blocker) == blocker
    lease = service.leases.claim_task(task_id, "TEST_ONLY_queued_confirm")
    try:
        assert execute_video_command(service, task_id, lease, command_id)["status"] == "queued"
        assert posted == []
        with factory.begin() as session:
            row = session.get(MediaExecution, task_id)
            assert "confirmation_intent" not in row.state
            assert session.get(MediaCommand, command_id).response is None
            waiting = dict(row.state["command_queue"], not_before="2000-01-01T00:00:00")
            row.state = dict(row.state, command_queue=waiting)
            session.get(GenerationTask, task_id).state = "INVESTIGATING"
        # A transient binding failure must reconcile its original task before
        # resuming the command, rather than rejecting its already authorized intent.
        assert resume_queued_video_command(service, task_id, lease) is False
        with factory.begin() as session:
            session.get(GenerationTask, task_id).state = "RUNNING"
        pool.release(scope, blocker)
        assert resume_queued_video_command(service, task_id, lease) is False
        response = execute_video_command(service, task_id, lease, command_id)
        if operation == "confirm":
            assert response["generation_id"] == generation_id
        else:
            assert response["status"] == "planning"
        expected_body = ({"instruction": upstream_body["instruction"]}
                         if operation == "revise" else upstream_body)
        assert posted == [("TEST_ONLY_original_confirmation", expected_body)]
        assert pool.acquire(scope, blocker) is None
        # Recreate the crash boundary: adapter facts are durable but the command
        # response and queue cleanup have not committed. Resume must allow polling.
        with factory.begin() as session:
            row = session.get(MediaExecution, task_id)
            row.state = dict(row.state, command_queue={
                "command_id": command_id, "not_before": "2000-01-01T00:00:00",
            })
            session.get(MediaCommand, command_id).response = None
        assert resume_queued_video_command(service, task_id, lease) is False
        assert len(posted) == 1
        with factory() as session:
            assert session.get(GenerationTask, task_id).settlement_state == "FROZEN"
            assert session.get(MediaCommand, command_id).response == response
    finally:
        service.leases.release(lease)
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_existing_video_job_is_adopted_before_new_local_admission(upstream):
    factory, _, create, _, _ = upstream
    origin = f"http://{uuid4().hex}.invalid:8015"

    def stamp(connection, snapshot):
        snapshot.routing_snapshot = {"protocol_version": "video-agent-v1", "base_url": origin}

    existing, waiter = [create(kind="video", snapshot_transform=stamp) for _ in range(2)]
    with factory.begin() as session:
        task = session.get(GenerationTask, existing)
        task.state, task.upstream_id = "RUNNING", str(uuid4())
        execution = new_execution(existing, "video")
        execution.state = {"status": "generating", "generation_id": str(uuid4())}
        session.add(execution)
    scope = execution_scope("video-agent-v1", origin)
    pool = MediaExecutionPool(factory, 1)
    assert pool.acquire(scope, waiter, protocol="video-agent-v1", base_url=origin) is None


def test_stale_worker_cannot_release_successors_async_slot(upstream):
    factory, _, create, _, _ = upstream
    owner, waiter = create(kind="image"), create(kind="image")
    pool = MediaExecutionPool(factory, 1)
    scope = uuid4().hex
    from app.dispatch.consumer import LeaseManager

    leases = LeaseManager(factory)
    first = leases.claim_task(owner, "TEST_ONLY_old_worker")
    assert pool.acquire(scope, owner, lease=first) == owner
    with factory.begin() as session:
        session.execute(text("UPDATE generation_tasks SET lease_expires_at=UTC_TIMESTAMP(6) "
                             "- INTERVAL 1 SECOND WHERE id=:id"), {"id": owner})
    second = leases.claim_task(owner, "TEST_ONLY_new_worker")
    assert pool.acquire(scope, owner, lease=second) == owner
    assert pool.release(scope, owner, lease=first) is False
    assert pool.acquire(scope, waiter) is None
    assert pool.release(scope, owner, lease=second) is True
    assert pool.acquire(scope, waiter) == waiter
    leases.release(second)
