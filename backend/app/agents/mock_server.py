"""Standalone, standard-library-only TEST_ONLY protocol and deterministic fault service.

Compose deliberately mounts this file alone. State is bounded and process-local: never
use simulator proofs or idempotency guarantees as a production/restart safety policy.
"""

import base64
import hashlib
import hmac
import json
import os
import re
import signal
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import NAMESPACE_URL, uuid4, uuid5

PROTOCOL = "mock-v1-TEST_ONLY"
CALLBACK_KEY = b"TEST_ONLY-not-a-production-secret"
MAX_BODY = 65536
MAX_RECORDS = 1000
AGENTS = {"copy", "image", "video"}
SCENARIOS = {
    "normal", "lost_response", "repeated", "out_of_order", "query_unavailable",
    "not_found", "partial", "expired_link", "unsupported", "proven_not_accepted",
}
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
INIT_LOCK = threading.Lock()

# Fixed synthetic TEST_ONLY files are embedded to keep the single-file Compose mount.
MEDIA_FIXTURES = {
    "image": ("image/png", base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAACXBIWXMAAAABAAAAAQBPJcTWAAAAPElE"
        "QVR4nO3RQQ0AMAgEwSOpu2qpPuxVwvLhtyPgSJbqd7PprK7HAwP+AJkImQiZCJkImQiZCJkImSjkA2ia"
        "Ae2JlpYoAAAAAElFTkSuQmCC"
    )),
    "video": ("video/mp4", base64.b64decode(
        "AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAMGbW9vdgAAAGxtdmhkAAAAAAAAAAAAAAAA"
        "AAAD6AAAA+gAAQAAAQAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAABAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAlV0cmFrAAAAXHRraGQAAAADAAAAAAAAAAAAAAAB"
        "AAAAAAAAA+gAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAABAAAAA"
        "ACAAAAAgAAAAAAAkZWR0cwAAABxlbHN0AAAAAAAAAAEAAAPoAAAAAAABAAAAAAHNbWRpYQAAACBtZGhk"
        "AAAAAAAAAAAAAAAAAABAAAAAQABVxAAAAAAALWhkbHIAAAAAAAAAAHZpZGUAAAAAAAAAAAAAAABWaWRl"
        "b0hhbmRsZXIAAAABeG1pbmYAAAAUdm1oZAAAAAEAAAAAAAAAAAAAACRkaW5mAAAAHGRyZWYAAAAAAAAA"
        "AQAAAAx1cmwgAAAAAQAAAThzdGJsAAAAuHN0c2QAAAAAAAAAAQAAAKhhdmMxAAAAAAAAAAEAAAAAAAAA"
        "AAAAAAAAAAAAACAAIABIAAAASAAAAAAAAAABDExhdmMgbGlieDI2NAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "GP//AAAALmF2Y0MBQsAe/+EAFmdCwB7ZCWwEQAAAAwBAAAADAQPFi5IBAAVoy4PLIAAAABBwYXNwAAAA"
        "AQAAAAEAAAAUYnRydAAAAAAAABTAAAAAAAAAABhzdHRzAAAAAAAAAAEAAAACAAAgAAAAABRzdHNzAAAA"
        "AAAAAAEAAAABAAAAHHN0c2MAAAAAAAAAAQAAAAEAAAACAAAAAQAAABxzdHN6AAAAAAAAAAAAAAACAAAC"
        "jgAAAAoAAAAUc3RjbwAAAAAAAAABAAADNgAAAD11ZHRhAAAANW1ldGEAAAAAAAAAIWhkbHIAAAAAAAAA"
        "AG1kaXJhcHBsAAAAAAAAAAAAAAAACGlsc3QAAAAIZnJlZQAAAqBtZGF0AAACcAYF//9s3EXpvebZSLeW"
        "LNgg2SPu73gyNjQgLSBjb3JlIDE2NSByMzIyMyAwNDgwY2IwIC0gSC4yNjQvTVBFRy00IEFWQyBjb2Rl"
        "YyAtIENvcHlsZWZ0IDIwMDMtMjAyNSAtIGh0dHA6Ly93d3cudmlkZW9sYW4ub3JnL3gyNjQuaHRtbCAt"
        "IG9wdGlvbnM6IGNhYmFjPTAgcmVmPTMgZGVibG9jaz0xOjA6MCBhbmFseXNlPTB4MToweDExMSBtZT1o"
        "ZXggc3VibWU9NyBwc3k9MSBwc3lfcmQ9MS4wMDowLjAwIG1peGVkX3JlZj0xIG1lX3JhbmdlPTE2IGNo"
        "cm9tYV9tZT0xIHRyZWxsaXM9MSA4eDhkY3Q9MCBjcW09MCBkZWFkem9uZT0yMSwxMSBmYXN0X3Bza2lw"
        "PTEgY2hyb21hX3FwX29mZnNldD0tMiB0aHJlYWRzPTEgbG9va2FoZWFkX3RocmVhZHM9MSBzbGljZWRf"
        "dGhyZWFkcz0wIG5yPTAgZGVjaW1hdGU9MSBpbnRlcmxhY2VkPTAgYmx1cmF5X2NvbXBhdD0wIGNvbnN0"
        "cmFpbmVkX2ludHJhPTAgYmZyYW1lcz0wIHdlaWdodHA9MCBrZXlpbnQ9MjUwIGtleWludF9taW49MiBz"
        "Y2VuZWN1dD00MCBpbnRyYV9yZWZyZXNoPTAgcmNfbG9va2FoZWFkPTQwIHJjPWNyZiBtYnRyZWU9MSBj"
        "cmY9MjMuMCBxY29tcD0wLjYwIHFwbWluPTAgcXBtYXg9NjkgcXBzdGVwPTQgaXBfcmF0aW89MS40MCBh"
        "cT0xOjEuMDAAgAAAABZliIQFPEYoAAgUxwABIxjgACYFJ114AAAABkGaOAl5YA=="
    )),
}


def enabled():
    return os.getenv("APP_MODE") == "mock" and os.getenv("APP_TEST_ONLY") == "true"


def wire(**values):
    return {"protocol_version": PROTOCOL, "test_only": True, **values}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def counters():
    return dict(submit=0, query_external=0, query_id=0, retrieve_original=0, generation_intents=0)


class ProtocolError(Exception):
    def __init__(self, code, status=400):
        self.code, self.status = code, status


class Simulator:
    def __init__(self):
        self.lock = threading.RLock()
        self.records = {}
        self.tasks = {}
        self.instance_id = str(uuid4())
        self.started = time.time()

    def record(self, agent, external):
        key = agent, external
        if key not in self.records:
            if len(self.records) >= MAX_RECORDS:
                raise ProtocolError("SIMULATOR_CAPACITY", 503)
            self.records[key] = {
                "scenario": "normal", "calls": counters(), "digest": None, "task_id": None,
            }
        return self.records[key]

    def proof(self, agent, external):
        return wire(agent_id=agent, external_submission_id=external,
                    reference=f"{self.instance_id}:{agent}:{external}",
                    verified_by="TEST_ONLY.atomic_simulator", verified_at=time.time(),
                    coverage_start=self.started, coverage_end=time.time(),
                    consistency="atomic_simulator_lifetime")

    def configure(self, agent, external, body):
        if set(body) != {"scenario"} or body["scenario"] not in SCENARIOS:
            raise ProtocolError("INVALID_SCENARIO")
        record = self.record(agent, external)
        if record["calls"]["submit"]:
            raise ProtocolError("SCENARIO_LOCKED", 409)
        record["scenario"] = body["scenario"]
        return 200, wire(scenario=body["scenario"], external_submission_id=external)

    def result(self, agent, record):
        complete = record["scenario"] != "partial"
        media_type, content = self.content(agent, record["task_id"])
        return dict(complete=complete, expected_items=1 if complete else 2, items=[{
            "item_key": "original-1", "locator": f"/v1/{agent}/results/{record['task_id']}",
            "media_type": media_type, "byte_length": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }])

    @staticmethod
    def content(agent, task_id):
        if agent == "copy":
            return "text/plain", f"TEST_ONLY copy original fixture {task_id}".encode()
        return MEDIA_FIXTURES[agent]

    def submit(self, agent, body):
        external, snapshot = body.get("external_submission_id"), body.get("snapshot")
        if (set(body) != {"external_submission_id", "snapshot"}
                or not isinstance(external, str) or not ID.fullmatch(external)
                or not isinstance(snapshot, dict)):
            raise ProtocolError("INVALID_SUBMISSION")
        digest = hashlib.sha256(encoded(snapshot)).hexdigest()
        record = self.record(agent, external)
        record["calls"]["submit"] += 1
        if record["digest"] is not None and record["digest"] != digest:
            raise ProtocolError("SNAPSHOT_CONFLICT", 409)
        record["digest"] = digest
        base = wire(external_submission_id=external, upstream_task_id=None, absence_proof=None)
        if record["scenario"] == "proven_not_accepted":
            return 200, dict(base, status="PROVEN_NOT_ACCEPTED",
                             absence_proof=self.proof(agent, external))
        if record["task_id"] is None:
            task_id = "mock-" + uuid5(NAMESPACE_URL, f"{agent}/{external}").hex
            record.update(task_id=task_id, created=time.time())
            record["calls"]["generation_intents"] = 1
            self.tasks[agent, task_id] = external
        if record["scenario"] == "lost_response" and record["calls"]["submit"] == 1:
            # Accepted first; intentionally suppress the identifier in the response.
            return 504, dict(base, status="UNKNOWN")
        return 200, dict(base, status="ACCEPTED", upstream_task_id=record["task_id"])

    def query(self, agent, identifier, by_id=False):
        external = self.tasks.get((agent, identifier)) if by_id else identifier
        record = self.record(agent, external) if external is not None else None
        base = wire(status="NOT_FOUND", external_submission_id=external,
                    upstream_task_id=None, absence_proof=None, state=None, result=None)
        if record is None:
            return 200, base
        record["calls"]["query_id" if by_id else "query_external"] += 1
        scenario = record["scenario"]
        if scenario == "proven_not_accepted":
            return 200, dict(base, status="PROVEN_NOT_ACCEPTED",
                             absence_proof=self.proof(agent, external))
        if scenario in {"query_unavailable", "not_found", "unsupported"}:
            status = {"query_unavailable": "UNAVAILABLE", "not_found": "NOT_FOUND",
                      "unsupported": "UNSUPPORTED"}[scenario]
            return (503 if status == "UNAVAILABLE" else 200), dict(base, status=status)
        if record["task_id"] is None:
            return 200, base
        return 200, dict(base, status="FOUND", state="RESULT_READY",
                         upstream_task_id=record["task_id"], result=self.result(agent, record))

    def retrieve(self, agent, task_id):
        external = self.tasks.get((agent, task_id))
        base = wire(status="NOT_FOUND", locator=f"/v1/{agent}/results/{task_id}",
                    content_base64=None, media_type=None, complete=False,
                    sha256=None, byte_length=None)
        if external is None:
            return 404, base
        record = self.records[agent, external]
        record["calls"]["retrieve_original"] += 1
        if record["scenario"] == "expired_link":
            return 410, dict(base, status="EXPIRED")
        media_type, body = self.content(agent, task_id)
        return 200, dict(base, status="AVAILABLE", complete=record["scenario"] != "partial",
                         media_type=media_type, content_base64=base64.b64encode(body).decode(),
                         sha256=hashlib.sha256(body).hexdigest(), byte_length=len(body))

    def events(self, agent, external):
        record = self.records.get((agent, external))
        if record is None or record["task_id"] is None:
            return 200, wire(events=[])
        seqs = {"repeated": [1, 2, 2], "out_of_order": [2, 1]}.get(record["scenario"], [1, 2])
        events = []
        for seq in seqs:
            raw = encoded(wire(
                agent_id=agent, event_id=f"{record['task_id']}:{seq}", sequence=seq,
                external_submission_id=external, upstream_task_id=record["task_id"],
                state="RUNNING" if seq == 1 else "RESULT_READY", timestamp=record["created"],
                result=None if seq == 1 else self.result(agent, record),
            ))
            signature = hmac.new(CALLBACK_KEY, raw, hashlib.sha256).hexdigest()
            events.append({"raw": raw.decode(), "headers": {"X-Mock-Signature": signature}})
        return 200, wire(events=events)

    def route(self, method, path, body):
        parts = path.strip("/").split("/")
        if method == "GET" and path == "/health/live":
            return 200, wire(live=True, mode="mock", instance_id=self.instance_id)
        with self.lock:
            if len(parts) == 5 and parts[:2] == ["__test__", "agents"]:
                _, _, agent, operation, external = parts
                self.validate_ids(agent, external)
                if method == "PUT" and operation == "scenarios":
                    return self.configure(agent, external, body)
                if method == "GET" and operation == "calls":
                    record = self.records.get((agent, external))
                    return 200, wire(**(record["calls"] if record else counters()))
                if method == "GET" and operation == "events":
                    return self.events(agent, external)
            if len(parts) in (3, 4) and parts[0] == "v1":
                agent, operation = parts[1:3]
                self.validate_ids(agent, parts[3] if len(parts) == 4 else "submit")
                if method == "POST" and parts[2:] == ["submissions"]:
                    return self.submit(agent, body)
                if method == "GET" and len(parts) == 4:
                    if operation in {"tasks", "submissions"}:
                        return self.query(agent, parts[3], operation == "tasks")
                    if operation == "results":
                        return self.retrieve(agent, parts[3])
            raise ProtocolError("NOT_FOUND", 404)

    @staticmethod
    def validate_ids(agent, identifier):
        if agent not in AGENTS or not ID.fullmatch(identifier):
            raise ProtocolError("NOT_FOUND", 404)


class Handler(BaseHTTPRequestHandler):
    # All responses close the connection; bound read time and JSON size.
    def setup(self):
        super().setup()
        self.connection.settimeout(3)

    def log_message(self, *_):
        pass  # No snapshots, identifiers, query strings or credentials in access logs.

    def send_error(self, code, message=None, explain=None):
        self.respond(code, wire(error="HTTP_ERROR"))

    def respond(self, status, payload):
        body = encoded(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.close_connection = True
        self.wfile.write(body)

    def handle_protocol(self):
        try:
            if not enabled():
                raise ProtocolError("NOT_FOUND", 404)
            body = {}
            if self.command in {"POST", "PUT"}:
                if self.headers.get("Transfer-Encoding"):
                    raise ProtocolError("TRANSFER_ENCODING_UNSUPPORTED")
                lengths = self.headers.get_all("Content-Length", [])
                if len(lengths) != 1 or not lengths[0].isdigit():
                    raise ProtocolError("CONTENT_LENGTH_REQUIRED", 411)
                size = int(lengths[0])
                if size > MAX_BODY:
                    raise ProtocolError("BODY_TOO_LARGE", 413)
                if self.headers.get_content_type() != "application/json":
                    raise ProtocolError("JSON_REQUIRED", 415)
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise ProtocolError("INCOMPLETE_BODY")
                body = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                if not isinstance(body, dict):
                    raise ProtocolError("OBJECT_REQUIRED")
            # Supports embedded stdlib servers too, without module-global task state.
            with INIT_LOCK:
                if not hasattr(self.server, "simulator"):
                    self.server.simulator = Simulator()
            status, payload = self.server.simulator.route(self.command, self.path, body)
            self.respond(status, payload)
        except ProtocolError as error:
            self.respond(error.status, wire(error=error.code))
        except (ValueError, TypeError, RecursionError):
            self.respond(400, wire(error="INVALID_JSON"))
        except (socket.timeout, TimeoutError):
            self.respond(408, wire(error="REQUEST_TIMEOUT"))
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True

    do_GET = handle_protocol
    do_POST = handle_protocol
    do_PUT = handle_protocol


class BoundedServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, address):
        self.slots = threading.BoundedSemaphore(16)
        self.simulator = Simulator()
        super().__init__(address, Handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


def main():
    if not enabled():
        raise SystemExit("Mock service requires APP_MODE=mock and APP_TEST_ONLY=true")
    server = BoundedServer((os.getenv("MOCK_HOST", "0.0.0.0"), int(os.getenv("MOCK_PORT", "8081"))))

    def stop(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    print(json.dumps(wire(host=server.server_address[0], port=server.server_port)), flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
