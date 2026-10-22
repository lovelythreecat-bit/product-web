"""Real local HTTP image submission; no provider calls or paid generation.

SQL lease/every-attempt authorization is covered by the shared media queue suite.
This boundary suite keeps the actual transport, multipart encoder and monotonic
execution-state merge. Only the trusted composition authorization is substituted.
"""

import json
from copy import deepcopy
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from threading import Event, Thread
from uuid import uuid4

import pytest
from PIL import Image

from app.agents.image import ImageAgentAdapter, ImageAgentProfile
from app.agents.media_execution import merge_execution_state
from app.catalog.schemas import content_digest


@pytest.fixture
def image_http_runtime():
    image = BytesIO()
    Image.new("RGB", (3, 4), "blue").save(image, format="PNG")
    data = image.getvalue()
    upstream = {"scenario": "full_then_accepted", "posts": [], "uploads": []}
    execution = {}
    release = Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, payload):
            raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def full(self):
            self.reply(429, {
                "code": "queue_full", "message": "Task queue is full", "request_id": str(uuid4()),
            })

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            assert self.headers["Authorization"] == "Bearer TEST_ONLY_image_key"
            scenario = upstream["scenario"]
            if self.path == "/api/v1/media":
                upstream["uploads"].append(raw)
                if scenario == "upload_full":
                    self.full()
                    return
                assert data in raw
                self.reply(201, dict(media_id="media-1", mime_type="image/png",
                                     byte_size=len(data), sha256=sha256(data).hexdigest()))
                return
            assert self.path == "/api/v1/tasks"
            upstream["posts"].append((raw, self.headers["Idempotency-Key"]))
            if scenario.startswith("full_then_") and len(upstream["posts"]) == 1:
                self.full()
                return
            if scenario in {"full_then_disconnect", "full_then_timeout"}:
                if scenario == "full_then_timeout":
                    release.wait(timeout=1)
                self.close_connection = True
                return
            if scenario == "invalid_code":
                self.reply(429, {"code": "rate_limit", "request_id": str(uuid4())})
            elif scenario == "invalid_json":
                self.reply(429, b"not JSON")
            elif scenario == "accepted_resource":
                self.reply(429, {"code": "queue_full", "task_id": "already-accepted"})
            elif scenario == "missing_code":
                self.reply(429, {"message": "Task queue is full"})
            else:
                self.reply(202, dict(task_id="image-task-1", status="queued", core_status=None,
                                     config_versions={"agent": "1"}, progress={}))

        def do_GET(self):
            assert self.headers["Authorization"] == "Bearer TEST_ONLY_image_key"
            if self.path.endswith("/result"):
                self.reply(200, {"status": "needs_input", "assets": [],
                                 "usage": {"image_calls": remote_calls()}})
            else:
                self.reply(200, {"task_id": "image-task-1", "status": "completed",
                                 "core_status": "needs_input"})

    def remote_calls():
        return upstream.get("image_calls", 0)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    profile = ImageAgentProfile(
        base_url=f"http://127.0.0.1:{server.server_port}", service_key="TEST_ONLY_image_key",
        agent_config_id="config-1",
    )
    snapshot = {"input_snapshot": {
        "product": {"name": "TEST_ONLY cup", "category": "cup"},
        "instruction": "Keep original product",
        "parameters": {"platform": "taobao", "output_type": "main_image"},
        "material_versions": [{"file_id": "file-1", "version": "v1"}],
    }}

    def save(patch):
        merged = merge_execution_state(execution, patch)
        execution.clear()
        execution.update(merged)

    def authorized():
        marker = execution.get("submission_rejection")
        return bool(marker and marker["attempt_id"] == execution["submission_attempt_id"]
                    and marker["external_submission_id"] == "external-1"
                    and marker["scope"] == adapter().retry_scope()
                    and marker["request_body_digest"] == content_digest(execution["request_body"]))

    def adapter():
        return ImageAgentAdapter(
            profile=profile, external_submission_id="external-1",
            load_state=lambda: deepcopy(execution), save_state=save,
            authorize_submission_retry=authorized,
            material_loader=lambda: [dict(file_id="file-1", version="v1", content=data,
                                          media_type="image/png", sha256=sha256(data).hexdigest())],
        )

    try:
        yield adapter, snapshot, execution, upstream
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_flat_queue_full_http_response_retries_same_body_upload_and_idempotency(image_http_runtime):
    adapter, snapshot, state, upstream = image_http_runtime
    first = adapter().submit(snapshot, "external-1")
    assert first.status == "RATE_LIMITED"
    assert first.retry_after_seconds == 5  # Actual upstream provides no Retry-After.
    first_attempt = state["submission_attempt_id"]
    assert state["submission_started"] is True
    assert adapter().submit(snapshot, "external-1").status == "ACCEPTED"
    assert state["submission_attempt_id"] != first_attempt
    assert state["upstream_task_id"] == "image-task-1"
    assert state["submission_rejection"] is None
    assert len(upstream["uploads"]) == 1
    assert len(upstream["posts"]) == 2
    assert upstream["posts"][0] == upstream["posts"][1]
    assert upstream["posts"][0][1] == "external-1"
    assert json.loads(upstream["posts"][0][0]) == state["request_body"]


@pytest.mark.parametrize("scenario", ["full_then_disconnect", "full_then_timeout"])
def test_lost_reply_after_queue_retry_invalidates_earlier_rejection(image_http_runtime, scenario):
    adapter, snapshot, state, upstream = image_http_runtime
    upstream["scenario"] = scenario
    assert adapter().submit(snapshot, "external-1").status == "RATE_LIMITED"
    retry = adapter()
    retry.client.timeout = 0.05
    assert retry.submit(snapshot, "external-1").status == "UNKNOWN"
    assert state["submission_rejection"] is None
    assert adapter().submit(snapshot, "external-1").status == "UNKNOWN"
    assert len(upstream["posts"]) == 2
    assert len(upstream["uploads"]) == 1


@pytest.mark.parametrize("scenario", [
    "invalid_code", "invalid_json", "accepted_resource", "missing_code", "upload_full",
])
def test_ambiguous_http429_and_upload_rejection_never_authorize_retry(image_http_runtime, scenario):
    adapter, snapshot, state, upstream = image_http_runtime
    upstream["scenario"] = scenario
    assert adapter().submit(snapshot, "external-1").status == "UNKNOWN"
    assert adapter().submit(snapshot, "external-1").status == "UNKNOWN"
    assert state.get("submission_rejection") is None
    assert len(upstream["uploads"]) == 1
    assert len(upstream["posts"]) == (0 if scenario == "upload_full" else 1)
