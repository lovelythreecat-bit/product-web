"""Real HTTP and MySQL video confirmation recovery; no provider calls."""

import json
import socket
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from uuid import uuid4

import pytest

from app.agents.media_execution import MediaExecution, MediaTaskStore, new_execution
from app.agents.media_http import MediaServiceError
from app.agents.video import VideoAgentAdapter, VideoAgentProfile, build_video_request
from app.dispatch.consumer import LeaseManager
from app.tasks.models import GenerationTask
from tests.t12_fixtures import upstream as upstream_fixture

upstream = upstream_fixture


@pytest.mark.parametrize("scenario", ["accepted_lost_reply", "generic_429"])
def test_confirmation_recovers_after_adapter_restart_without_second_post(upstream, scenario):
    factory, _, create, _, _ = upstream
    task_id = create(kind="video")
    asset_id, upstream_id, generation_id = [str(uuid4()) for _ in range(3)]
    with factory() as session:
        task = session.get(GenerationTask, task_id)
        external, owner = task.external_submission_id, task.user_id
    file_id = str(uuid4())
    body = build_video_request(
        {"input_snapshot": {
            "product": {"name": "TEST_ONLY cup"}, "instruction": "original instruction",
            "parameters": {"first_frame_file_id": file_id},
            "material_versions": [{"file_id": file_id, "version": "v1"}],
        }},
        {file_id + ":v1": {"asset_id": asset_id}},
    )
    body.update(external_request_id=external, external_user_id=owner)
    original = {
        "request_body": body, "upstream_task_id": upstream_id,
        "status": "awaiting_confirmation", "head_plan_version": 2,
        "plan": {"task_id": upstream_id, "plan_version": 2},
        "uploads": {file_id + ":v1": {"asset_id": asset_id}},
    }
    transport = {"posts": [], "gets": [], "accepted": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, value):
            data = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            assert self.path == f"/api/v1/tasks/{upstream_id}/confirm"
            assert self.headers["Authorization"] == "Bearer TEST_ONLY_video_key"
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            transport["posts"].append((self.headers["Idempotency-Key"], payload))
            if scenario == "generic_429":
                self.reply(429, {"error": {"code": "HTTP_ERROR", "retryable": True}})
                return
            transport["accepted"] = True
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()

        def do_GET(self):
            transport["gets"].append(self.path)
            if not transport["accepted"]:
                self.reply(503, {"error": {"code": "DEPENDENCY_UNAVAILABLE"}})
            elif self.path == f"/api/v1/tasks/{upstream_id}":
                self.reply(200, {
                    **body, "task_id": upstream_id, "image_asset_ids": body["images"],
                    "status": "generating", "head_plan_version": 2,
                    "confirmed_plan_version": 2, "generation_id": generation_id,
                })
            else:
                assert self.path == f"/api/v1/generations/{generation_id}"
                self.reply(200, {
                    "task_id": upstream_id, "generation_id": generation_id,
                    "plan_version": 2, "status": "queued",
                })

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    leases = LeaseManager(factory)
    lease = leases.claim_task(task_id, "TEST_ONLY_video_confirmation")
    assert lease is not None
    with factory.begin() as session:
        task = session.get(GenerationTask, task_id)
        task.state, task.upstream_id = "RUNNING", upstream_id
        row = new_execution(task_id, "video")
        row.state = deepcopy(original)
        session.add(row)
    store = MediaTaskStore(factory, task_id, "video", lease)
    profile = VideoAgentProfile(
        base_url=f"http://127.0.0.1:{server.server_port}",
        service_key="TEST_ONLY_video_key", max_result_bytes=8192,
    )

    def adapter():
        return VideoAgentAdapter(
            profile=profile, external_submission_id=external,
            load_state=store.load, save_state=store.save,
        )

    try:
        with pytest.raises(MediaServiceError):
            adapter().confirm(2, "TEST_ONLY_original_confirm")
        with factory() as session:
            persisted = session.get(MediaExecution, task_id).state
            assert persisted["confirmation_attempted"] is True
            assert persisted["confirmation_intent"] == {
                "plan_version": 2, "idempotency_key": "TEST_ONLY_original_confirm"
            }
        if scenario == "accepted_lost_reply":
            for _ in range(2):
                recovered = adapter().confirm(2, "TEST_ONLY_original_confirm")
                assert recovered["generation_id"] == generation_id
        else:
            with pytest.raises(MediaServiceError):
                adapter().confirm(2, "TEST_ONLY_original_confirm")
        assert transport["posts"] == [("TEST_ONLY_original_confirm", {"plan_version": 2})]
        assert transport["gets"][0] == f"/api/v1/tasks/{upstream_id}"
        with factory() as session:
            persisted = session.get(MediaExecution, task_id).state
            assert persisted["request_body"] == original["request_body"]
            assert persisted["uploads"] == original["uploads"]
            assert session.get(GenerationTask, task_id).settlement_state == "FROZEN"
    finally:
        leases.release(lease)
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
