"""Exercise the real TEST_ONLY HTTP simulator, never a patched transport."""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection, HTTPResponse
from http.server import ThreadingHTTPServer
from importlib.util import find_spec
from pathlib import Path
from queue import Queue
from threading import Event, Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from app.agents.mock_server import Handler


class Plain404Handler(Handler):
    def do_GET(self):
        self.respond(404, {"error": "NOT_FOUND"})


@pytest.fixture
def server(monkeypatch, request):
    monkeypatch.setenv("APP_MODE", "mock")
    monkeypatch.setenv("APP_TEST_ONLY", "true")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), getattr(request, "param", Handler))
    thread = Thread(target=lambda: httpd.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)


def call(server, method, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    request = Request(server + path, data=body, method=method)
    request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        raw = error.read()
        try:
            body = json.loads(raw)
        except ValueError:
            body = raw.decode()
        return error.code, body


def configure(server, external, scenario, agent="copy"):
    status, body = call(
        server, "PUT", f"/__test__/agents/{agent}/scenarios/{external}",
        {"scenario": scenario},
    )
    assert status == 200, body


def submit(server, external, agent="copy", snapshot=None):
    return call(server, "POST", f"/v1/{agent}/submissions", {
        "external_submission_id": external,
        "snapshot": snapshot or {"prompt": "TEST_ONLY 商品文案"},
    })


def test_mock_response_loss_preserves_intent(server):
    configure(server, "lost-1", "lost_response")
    status, first = submit(server, "lost-1")
    assert (status, first["status"]) == (504, "UNKNOWN")
    status, recovered = call(server, "GET", "/v1/copy/submissions/lost-1")
    assert (status, recovered["status"]) == (200, "FOUND")
    status, replay = submit(server, "lost-1")
    assert (status, replay["status"]) == (200, "ACCEPTED")
    assert replay["upstream_task_id"] == recovered["upstream_task_id"]
    _, counts = call(server, "GET", "/__test__/agents/copy/calls/lost-1")
    assert counts["submit"] == 2
    assert counts["generation_intents"] == 1
    assert counts["query_external"] == 1


def test_not_found_differs_proven_absent(server):
    configure(server, "missing-1", "not_found")
    submit(server, "missing-1")
    _, missing = call(server, "GET", "/v1/copy/submissions/missing-1")
    assert missing["status"] == "NOT_FOUND"
    assert missing["absence_proof"] is None
    configure(server, "absent-1", "proven_not_accepted")
    status, refused = submit(server, "absent-1")
    assert (status, refused["status"]) == (200, "PROVEN_NOT_ACCEPTED")
    _, absent = call(server, "GET", "/v1/copy/submissions/absent-1")
    assert absent["status"] == "PROVEN_NOT_ACCEPTED"
    assert absent["absence_proof"]["test_only"] is True
    assert absent["absence_proof"]["external_submission_id"] == "absent-1"
    _, counts = call(server, "GET", "/__test__/agents/copy/calls/absent-1")
    assert counts["generation_intents"] == 0


@pytest.mark.parametrize("agent", ["copy", "image", "video"])
def test_conflicting_replay_and_concurrent_duplicate_never_regenerate(server, agent):
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: submit(server, "parallel-1", agent), range(8)))
    assert {status for status, _ in responses} == {200}
    assert len({body["upstream_task_id"] for _, body in responses}) == 1
    status, body = submit(server, "parallel-1", agent, {"prompt": "changed"})
    assert (status, body["error"]) == (409, "SNAPSHOT_CONFLICT")
    _, counts = call(server, "GET", f"/__test__/agents/{agent}/calls/parallel-1")
    assert counts["submit"] == 9
    assert counts["generation_intents"] == 1


@pytest.mark.parametrize("scenario,expected", [
    ("query_unavailable", "UNAVAILABLE"), ("not_found", "NOT_FOUND"),
    ("unsupported", "UNSUPPORTED"),
])
def test_inconclusive_queries_never_prove_non_acceptance(server, scenario, expected):
    configure(server, "query-1", scenario)
    _, task = submit(server, "query-1")
    for path in ("/v1/copy/submissions/query-1", f"/v1/copy/tasks/{task['upstream_task_id']}"):
        _, outcome = call(server, "GET", path)
        assert outcome["status"] == expected
        assert outcome["absence_proof"] is None
    _, counts = call(server, "GET", "/__test__/agents/copy/calls/query-1")
    assert counts["generation_intents"] == 1


@pytest.mark.parametrize("scenario,sequences", [
    ("repeated", [1, 2, 2]), ("out_of_order", [2, 1]),
])
def test_notification_faults_are_repeatable_and_bound_to_original_task(server, scenario, sequences):
    configure(server, "events-1", scenario)
    _, task = submit(server, "events-1")
    _, events = call(server, "GET", "/__test__/agents/copy/events/events-1")
    _, replay = call(server, "GET", "/__test__/agents/copy/events/events-1")
    assert events == replay
    payloads = [json.loads(item["raw"]) for item in events["events"]]
    assert [item["sequence"] for item in payloads] == sequences
    assert all(item["upstream_task_id"] == task["upstream_task_id"] for item in payloads)
    assert all(item["external_submission_id"] == "events-1" for item in payloads)


def test_partial_result_is_not_complete_and_expired_link_cannot_regenerate(server):
    configure(server, "partial-1", "partial")
    _, partial = submit(server, "partial-1")
    _, query = call(server, "GET", "/v1/copy/submissions/partial-1")
    assert query["result"]["complete"] is False
    assert query["result"]["expected_items"] == 2
    assert len(query["result"]["items"]) == 1
    assert partial["upstream_task_id"] == query["upstream_task_id"]
    configure(server, "expired-1", "expired_link")
    _, task = submit(server, "expired-1")
    for _ in range(2):
        status, result = call(server, "GET", f"/v1/copy/results/{task['upstream_task_id']}")
        assert (status, result["status"]) == (410, "EXPIRED")
        assert result["content_base64"] is None
    _, counts = call(server, "GET", "/__test__/agents/copy/calls/expired-1")
    assert counts["generation_intents"] == 1
    assert counts["retrieve_original"] == 2


def test_scenario_cannot_rewrite_accepted_history(server):
    submit(server, "fixed-1")
    status, body = call(server, "PUT", "/__test__/agents/copy/scenarios/fixed-1", {
        "scenario": "proven_not_accepted",
    })
    assert (status, body["error"]) == (409, "SCENARIO_LOCKED")
    _, query = call(server, "GET", "/v1/copy/submissions/fixed-1")
    assert query["status"] == "FOUND"


def test_bad_requests_are_bounded_json_errors_and_leave_no_intents(server):
    for payload in ([], {"external_submission_id": "bad-1", "snapshot": []},
                    {"external_submission_id": "bad-1", "snapshot": {"x": "a" * 70000}}):
        status, body = call(server, "POST", "/v1/copy/submissions", payload)
        assert status in (400, 413)
        assert body["test_only"] is True
    _, counts = call(server, "GET", "/__test__/agents/copy/calls/bad-1")
    assert counts["generation_intents"] == 0


def test_gate_hides_protocol_even_when_handler_is_embedded(server, monkeypatch):
    monkeypatch.setenv("APP_MODE", "production")
    for path in ("/health/live", "/__test__/agents/copy/calls/a", "/v1/copy/submissions/a"):
        status, body = call(server, "GET", path)
        assert (status, body["error"]) == (404, "NOT_FOUND")


def adapter(server, agent="copy", **options):
    assert find_spec("app.agents.mock") is not None, "Typed mock adapter must be implemented"
    from app.agents import mock

    assert hasattr(mock, "MockAgentAdapter"), "Typed mock adapter must be implemented"
    return mock.MockAgentAdapter(agent_id=agent, base_url=server, mode="mock", test_only=True,
                                 **options)


def test_typed_adapter_recovers_original_and_rejects_arbitrary_locator(server):
    client = adapter(server)
    configure(server, "typed-1", "lost_response")
    outcome = client.submit({"prompt": "test"}, "typed-1")
    assert outcome.status == "UNKNOWN"
    found = client.query_by_external("typed-1")
    assert found.status == "FOUND"
    assert client.query(found.upstream_task_id).upstream_task_id == found.upstream_task_id
    source = client.retrieve_original(found.result.items[0].locator)
    assert source.status == "AVAILABLE"
    assert source.content.startswith(b"TEST_ONLY copy original")
    assert source.complete is True
    assert client.retrieve_original("http://169.254.169.254/latest").status == "UNSUPPORTED"
    assert client.retrieve_original("/v1/video/results/other").status == "UNSUPPORTED"


def test_callback_tampering_wrong_agent_and_duplicate_are_identified(server):
    client = adapter(server)
    configure(server, "signed-1", "repeated")
    client.submit({}, "signed-1")
    _, response = call(server, "GET", "/__test__/agents/copy/events/signed-1")
    event = response["events"][1]
    raw = event["raw"].encode()
    assert client.verify_callback(raw + b" ", event["headers"]).status == "INVALID"
    assert adapter(server, "image").verify_callback(raw, event["headers"]).status == "INVALID"
    verified = client.verify_callback(raw, event["headers"])
    assert verified.status == "VERIFIED"
    assert verified.external_submission_id == "signed-1"
    assert verified.result.complete is True
    assert client.verify_callback(raw, event["headers"]).status == "DUPLICATE"


@pytest.mark.parametrize("server", [Plain404Handler], indirect=True)
def test_adapter_distinguishes_plain_404_and_unknown_capabilities(server):
    client = adapter(server)
    assert client.query("missing").status == "NOT_FOUND"
    assert client.query("missing").absence_proof is None
    from app.agents.contracts import Capabilities

    capabilities = Capabilities()
    assert capabilities.idempotent_submit == "unknown"
    assert capabilities.query_external == "unknown"


def test_registry_blocks_mock_in_production_and_unknown_real_protocol(server):
    assert find_spec("app.agents.registry") is not None, "Guarded registry must be implemented"
    from app.agents import registry

    assert hasattr(registry, "AgentRegistry"), "Guarded registry must be implemented"
    client = adapter(server)
    with pytest.raises(ValueError, match="TEST_ONLY"):
        registry.AgentRegistry(mode="production", test_only=False).register(client)
    guarded = registry.AgentRegistry(mode="mock", test_only=True)
    guarded.register(client)
    assert guarded.get("copy", "mock-v1-TEST_ONLY") is client
    with pytest.raises(LookupError):
        guarded.get("copy", "v1")


def test_test_only_absence_proof_cannot_be_constructed_from_a_status_alone(server):
    client = adapter(server)
    configure(server, "proof-1", "proven_not_accepted")
    proof = client.query_by_external("proof-1").absence_proof
    assert proof.verified_by == "TEST_ONLY.atomic_simulator"
    assert proof.test_only is True
    from app.agents.contracts import QueryOutcome

    with pytest.raises(ValueError):
        QueryOutcome(status="PROVEN_NOT_ACCEPTED")


def test_invalid_numeric_callback_timestamp_is_never_verified(server):
    import hashlib
    import hmac

    from app.agents.mock_server import CALLBACK_KEY

    client = adapter(server)
    client.submit({}, "nonfinite-1")
    _, response = call(server, "GET", "/__test__/agents/copy/events/nonfinite-1")
    payload = json.loads(response["events"][0]["raw"])
    payload["timestamp"] = float("nan")
    raw = json.dumps(payload).encode()
    signature = hmac.new(CALLBACK_KEY, raw, hashlib.sha256).hexdigest()
    assert client.verify_callback(raw, {"X-Mock-Signature": signature}).status == "INVALID"


@pytest.mark.parametrize("proof", [["malformed"], "malformed", 1, True])
def test_callback_non_object_absence_proof_returns_invalid(server, proof):
    import hashlib
    import hmac

    from app.agents.mock_server import CALLBACK_KEY

    client = adapter(server)
    client.submit({}, "malformed-proof-1")
    _, response = call(server, "GET", "/__test__/agents/copy/events/malformed-proof-1")
    payload = json.loads(response["events"][0]["raw"])
    payload["absence_proof"] = proof
    raw = json.dumps(payload).encode()
    signature = hmac.new(CALLBACK_KEY, raw, hashlib.sha256).hexdigest()
    assert client.verify_callback(raw, {"X-Mock-Signature": signature}).status == "INVALID"


def test_malformed_json_and_ambiguous_length_are_rejected(server):
    from urllib.parse import urlsplit

    target = urlsplit(server)
    for raw, extra, want in [(b"{", {}, 400), (b"{}", {"Transfer-Encoding": "chunked"}, 400),
                             (b"NaN", {}, 400)]:
        connection = HTTPConnection(target.hostname, target.port, timeout=3)
        try:
            connection.request("POST", "/v1/copy/submissions", body=raw,
                               headers={"Content-Type": "application/json", **extra})
            response = connection.getresponse()
            assert response.status == want
            assert json.loads(response.read())["test_only"] is True
        finally:
            connection.close()


@pytest.mark.parametrize("mode,test_only", [("production", "true"), ("mock", "false")])
def test_standalone_server_refuses_non_test_configuration(tmp_path, mode, test_only):
    script = tmp_path / "server.py"
    shutil.copyfile(Path(__file__).resolve().parents[2] / "app/agents/mock_server.py", script)
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(script)], cwd=tmp_path, capture_output=True,
        timeout=5, env={**os.environ, "APP_MODE": mode, "APP_TEST_ONLY": test_only},
    )
    assert result.returncode != 0
    assert b"requires APP_MODE=mock and APP_TEST_ONLY=true" in result.stderr


def test_single_file_process_http_lifecycle_and_fault_control(tmp_path):
    script = tmp_path / "server.py"
    shutil.copyfile(Path(__file__).resolve().parents[2] / "app/agents/mock_server.py", script)
    process = subprocess.Popen(
        [sys.executable, "-I", "-B", str(script)], cwd=tmp_path,
        env={**os.environ, "APP_MODE": "mock", "APP_TEST_ONLY": "true",
             "MOCK_HOST": "127.0.0.1", "MOCK_PORT": "0"},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    lines = Queue()
    reader = Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
    reader.start()
    try:
        announcement = json.loads(lines.get(timeout=5))
        url = f"http://127.0.0.1:{announcement['port']}"
        assert call(url, "GET", "/health/live")[1]["test_only"] is True
        configure(url, "process-1", "lost_response", "video")
        assert submit(url, "process-1", "video")[0] == 504
        recovered = adapter(url, "video").query_by_external("process-1")
        assert recovered.status == "FOUND"
        assert call(url, "GET", "/__test__/agents/video/calls/process-1")[1][
            "generation_intents"
        ] == 1
        print(json.dumps({"single_file_process": True, "health": "live",
                          "lost_response": 504, "recovered": recovered.status,
                          "generation_intents": 1, "pid": process.pid}))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        reader.join(timeout=2)
        process.stdout.close()
        process.stderr.close()
    assert process.poll() is not None


@pytest.mark.parametrize("agent,media_type", [("image", "image/png"), ("video", "video/mp4")])
def test_complete_media_has_valid_format_and_original_content_metadata(server, agent, media_type):
    import hashlib
    import struct
    import zlib

    client = adapter(server, agent)
    client.submit({}, "media-1")
    found = client.query_by_external("media-1")
    item = found.result.items[0]
    assert item.media_type == media_type
    source = client.retrieve_original(item.locator)
    assert source.status == "AVAILABLE"
    assert source.media_type == media_type
    assert source.complete is True
    assert item.sha256 == source.sha256 == hashlib.sha256(source.content).hexdigest()
    assert item.byte_length == source.byte_length == len(source.content)
    if agent == "image":
        assert source.content.startswith(b"\x89PNG\r\n\x1a\n")
        offset, compressed = 8, b""
        while offset < len(source.content):
            length = struct.unpack(">I", source.content[offset:offset + 4])[0]
            chunk = source.content[offset + 4:offset + 8]
            data = source.content[offset + 8:offset + 8 + length]
            crc = struct.unpack(">I", source.content[offset + 8 + length:offset + 12 + length])[0]
            assert zlib.crc32(chunk + data) == crc
            if chunk == b"IDAT":
                compressed += data
            offset += length + 12
        assert zlib.decompress(compressed)
    else:
        offset, boxes = 0, set()
        while offset < len(source.content):
            length = struct.unpack(">I", source.content[offset:offset + 4])[0]
            assert length >= 8
            boxes.add(source.content[offset + 4:offset + 8])
            offset += length
        assert offset == len(source.content)
        assert {b"ftyp", b"moov", b"mdat"} <= boxes
    decoder = shutil.which("ffmpeg")
    if decoder:
        decoded = subprocess.run(
            [decoder, "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-f", "null", "-"],
            input=source.content, capture_output=True, timeout=10,
        )
        assert decoded.returncode == 0, decoded.stderr.decode(errors="replace")
    print(json.dumps({"agent": agent, "mime": source.media_type, "bytes": source.byte_length,
                      "sha256": source.sha256, "http_bytes_decoded_by_ffmpeg": bool(decoder)}))
    assert client.retrieve_original(item.locator).content == source.content
    _, counts = call(server, "GET", f"/__test__/agents/{agent}/calls/media-1")
    assert counts["generation_intents"] == 1
    assert counts["retrieve_original"] == 2


@pytest.fixture
def closing_server(monkeypatch):
    """Control actual request segmentation; observe real server reads and close."""
    monkeypatch.setenv("APP_MODE", "mock")
    monkeypatch.setenv("APP_TEST_ONLY", "true")
    written, resume, closed = Event(), Event(), Event()
    discarded = []

    class ObservedSocket:
        def __init__(self, actual):
            self.actual = actual

        def __getattr__(self, name):
            return getattr(self.actual, name)

        def recv(self, size):
            chunk = self.actual.recv(size)
            discarded.append(len(chunk))
            return chunk

    class SegmentedHandler(Handler):
        def setup(self):
            super().setup()
            self.connection = ObservedSocket(self.connection)

        def respond(self, status, payload):
            super().respond(status, payload)
            written.set()
            assert resume.wait(2), "test did not release response boundary"

    class ObservedServer(ThreadingHTTPServer):
        def shutdown_request(self, request):
            super().shutdown_request(request)
            closed.set()

    httpd = ObservedServer(("127.0.0.1", 0), SegmentedHandler)
    thread = Thread(target=lambda: httpd.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        yield httpd, written, resume, closed, discarded
    finally:
        resume.set()
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)


def rejection_headers(size):
    return ("POST /v1/copy/submissions HTTP/1.1\r\nHost: localhost\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {size}\r\n\r\n").encode()


def test_inflight_oversized_body_keeps_complete_error_response(closing_server):
    httpd, written, resume, closed, discarded = closing_server
    with socket.create_connection(httpd.server_address, timeout=2) as client:
        client.sendall(rejection_headers(70000))
        assert written.wait(1)
        client.sendall(b"x" * 8192)
        resume.set()
        # Force the same boundary as sendall's remaining in-flight segments.
        closed.wait(0.1)
        try:
            client.sendall(b"x" * (70000 - 8192))
            response = HTTPResponse(client)
            response.begin()
            body = json.loads(response.read())
        except OSError as error:
            pytest.fail(f"413 lost while request tail was in flight: {type(error).__name__}")
        assert (response.status, body["error"], body["test_only"]) == (413, "BODY_TOO_LARGE", True)
        assert sum(discarded) <= 131072
        client.shutdown(socket.SHUT_WR)
        assert closed.wait(1)
    assert not hasattr(httpd, "simulator"), "rejected body must not create a generation intent"


def test_huge_declared_body_does_not_delay_error_or_hold_worker(closing_server):
    httpd, written, resume, closed, _ = closing_server
    with socket.create_connection(httpd.server_address, timeout=2) as client:
        client.sendall(rejection_headers(10**12))
        assert written.wait(1)
        started = time.monotonic()
        resume.set()
        response = HTTPResponse(client)
        response.begin()
        assert json.loads(response.read())["error"] == "BODY_TOO_LARGE"
        # Keep client write side open: cleanup must not await Content-Length or EOF forever.
        assert closed.wait(0.8)
        assert time.monotonic() - started < 0.8


def test_error_discard_stops_at_byte_budget(closing_server):
    httpd, written, resume, closed, discarded = closing_server
    with socket.create_connection(httpd.server_address, timeout=2) as client:
        client.sendall(rejection_headers(10**12))
        assert written.wait(1)
        client.sendall(b"x" * 262144)
        resume.set()
        assert closed.wait(0.8)
        assert 0 < sum(discarded) <= 131072



def test_error_discard_deadline_cannot_be_extended_by_trickling_body(closing_server):
    httpd, written, resume, closed, _ = closing_server
    stop = Event()
    errors = []
    sent = []
    with socket.create_connection(httpd.server_address, timeout=2) as client:
        client.sendall(rejection_headers(10**12))
        assert written.wait(1)
        resume.set()
        response = HTTPResponse(client)
        response.begin()
        assert json.loads(response.read())["error"] == "BODY_TOO_LARGE"

        def trickle():
            while not stop.wait(0.02):
                try:
                    client.sendall(b"x")
                    sent.append(1)
                except OSError as error:
                    # Closing after the rejection is intentional; a prior failure is not.
                    if not closed.wait(0.1):
                        errors.append(type(error).__name__)
                    return

        sender = Thread(target=trickle, daemon=True)
        sender.start()
        try:
            assert closed.wait(0.8), "each received byte extended the cleanup deadline"
            assert len(sent) >= 2
            assert not errors
        finally:
            stop.set()
            sender.join(timeout=1)
