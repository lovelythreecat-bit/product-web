"""Typed HTTP client for the TEST_ONLY simulator. No retries or real-provider claims."""

import base64
import hashlib
import hmac
import json
import threading
import time
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from pydantic import ValidationError

from .contracts import (
    Capabilities,
    QueryOutcome,
    ResultSource,
    SubmitOutcome,
    VerifiedEvent,
)
from .mock_server import AGENTS, CALLBACK_KEY, ID, MAX_BODY, PROTOCOL


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class MockAgentAdapter:
    protocol_version = PROTOCOL
    test_only = True

    def __init__(self, *, agent_id: str, base_url: str, mode: str, test_only: bool,
                 timeout: float = 3):
        if mode != "mock" or not test_only:
            raise ValueError("TEST_ONLY adapter requires mock mode and TEST_ONLY=true")
        parts = urlsplit(base_url)
        if (agent_id not in AGENTS or parts.scheme != "http" or not parts.hostname
                or parts.username or parts.password or parts.query or parts.fragment
                or parts.path not in ("", "/") or not 0 < timeout <= 30):
            raise ValueError("Invalid TEST_ONLY simulator configuration")
        self.agent_id, self.base_url, self.timeout = agent_id, base_url.rstrip("/"), timeout
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()
        self.capabilities = Capabilities(
            sync="unsupported", async_="supported", stream="unsupported",
            final_text="supported" if agent_id == "copy" else "unsupported",
            idempotent_submit="supported", query_external="supported", query_id="supported",
            callback="supported", original_result_recovery="supported",
        )

    def _request(self, method, path, body=None):
        data = None if body is None else json.dumps(body, allow_nan=False).encode()
        if data is not None and len(data) > MAX_BODY:
            raise ValueError("TEST_ONLY request exceeds size limit")
        request = Request(self.base_url + path, data=data, method=method,
                          headers={"Content-Type": "application/json"})
        opener = build_opener(ProxyHandler({}), NoRedirects())
        try:
            response = opener.open(request, timeout=self.timeout)
        except HTTPError as error:
            response = error
        with response:
            status, raw = response.status, response.read(MAX_BODY + 1)
        if len(raw) > MAX_BODY:
            raise ValueError("TEST_ONLY response exceeds size limit")
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeError):
            payload = {}
        return status, payload

    def _validate_wire(self, payload):
        if (not isinstance(payload, dict) or payload.get("test_only") is not True
                or payload.get("protocol_version") != PROTOCOL):
            raise ValueError("Not a TEST_ONLY protocol response")
        proof = payload.get("absence_proof")
        if proof is not None and not isinstance(proof, dict):
            raise ValueError("TEST_ONLY absence proof must be an object")
        if proof and (proof.get("agent_id") != self.agent_id
                      or proof.get("verified_by") != "TEST_ONLY.atomic_simulator"
                      or proof.get("consistency") != "atomic_simulator_lifetime"):
            raise ValueError("Invalid TEST_ONLY proof provenance")

    @staticmethod
    def _id(identifier):
        if not isinstance(identifier, str) or not ID.fullmatch(identifier):
            raise ValueError("Invalid agent identifier")
        return identifier

    def retry_scope(self):
        """Instance-scoped idempotency only; unavailable probes never authorize retries."""
        try:
            status, payload = self._request("GET", "/health/live")
            self._validate_wire(payload)
            if (status != 200 or not ID.fullmatch(payload.get("instance_id", ""))
                    or any(type(payload.get(key)) is not int for key in
                           ("started", "observed_at", "sequence"))
                    or payload["sequence"] < 1 or payload["started"] > payload["observed_at"]):
                return None
            return {key: payload[key] for key in
                    ("instance_id", "started", "observed_at", "sequence")}
        except (URLError, OSError, ValueError, TypeError):
            return None

    def submit_scoped(self, snapshot, external_submission_id, scope):
        return self._submit(snapshot, external_submission_id, scope["instance_id"])

    def submit(self, snapshot: Mapping[str, Any], external_submission_id: str) -> SubmitOutcome:
        return self._submit(snapshot, external_submission_id)

    def _submit(self, snapshot, external_submission_id, instance_id=None):
        external = self._id(external_submission_id)
        fallback = dict(protocol_version=PROTOCOL, test_only=True, external_submission_id=external)
        try:
            status, payload = self._request("POST", f"/v1/{self.agent_id}/submissions", {
                "snapshot": dict(snapshot), "external_submission_id": external,
                **({"expected_instance_id": instance_id} if instance_id else {}),
            })
            self._validate_wire(payload)
            if status in (400, 409, 413, 415):
                return SubmitOutcome(status="REJECTED", **fallback)
            if payload.get("external_submission_id") != external:
                raise ValueError("Submission identity mismatch")
            return SubmitOutcome.model_validate(payload)
        except (URLError, OSError, ValueError, TypeError):
            # A lost reply cannot establish whether submission was accepted.
            return SubmitOutcome(status="UNKNOWN", **fallback)

    def _query(self, identifier, by_id):
        identifier = self._id(identifier)
        fallback = dict(protocol_version=PROTOCOL, test_only=True)
        try:
            operation = "tasks" if by_id else "submissions"
            status, payload = self._request("GET", f"/v1/{self.agent_id}/{operation}/{identifier}")
            # A plain upstream 404 is only NOT_FOUND, never an absence proof.
            if status == 404:
                return QueryOutcome(status="NOT_FOUND", **fallback)
            self._validate_wire(payload)
            outcome = QueryOutcome.model_validate(payload)
            if (
                not by_id and outcome.external_submission_id != identifier
                or by_id and outcome.status == "FOUND" and outcome.upstream_task_id != identifier
            ):
                raise ValueError("Query identity mismatch")
            return outcome
        except (URLError, OSError, ValueError, TypeError):
            return QueryOutcome(status="UNAVAILABLE", **fallback)

    def query_by_external(self, external_submission_id: str) -> QueryOutcome:
        return self._query(external_submission_id, False)

    def query(self, upstream_task_id: str) -> QueryOutcome:
        return self._query(upstream_task_id, True)

    def retrieve_original(self, locator: str) -> ResultSource:
        fallback = dict(protocol_version=PROTOCOL, test_only=True, locator=locator)
        prefix = f"/v1/{self.agent_id}/results/"
        parts = locator[len(prefix) :].split("/")
        if (
            not locator.startswith(prefix)
            or len(parts) not in {1, 2}
            or not ID.fullmatch(parts[0])
            or len(parts) == 2
            and parts[1] not in {"original-1", "original-2"}
        ):
            return ResultSource(status="UNSUPPORTED", **fallback)
        try:
            _, payload = self._request("GET", locator)
            self._validate_wire(payload)
            if payload.get("locator") != locator:
                raise ValueError("Result identity mismatch")
            body = payload.pop("content_base64")
            payload["content"] = None if body is None else base64.b64decode(body, validate=True)
            return ResultSource.model_validate(payload)
        except (URLError, OSError, ValueError, TypeError, KeyError):
            return ResultSource(status="UNAVAILABLE", **fallback)

    def verify_callback(self, raw: bytes, headers: Mapping[str, str]) -> VerifiedEvent:
        fallback = dict(protocol_version=PROTOCOL, test_only=True)
        try:
            if len(raw) > MAX_BODY:
                raise ValueError("Oversized event")
            signature = {key.lower(): value for key, value in headers.items()}.get(
                "x-mock-signature", ""
            )
            if not hmac.compare_digest(
                hmac.new(CALLBACK_KEY, raw, hashlib.sha256).hexdigest(), signature
            ):
                raise ValueError("Invalid TEST_ONLY signature")
            payload = json.loads(raw)
            self._validate_wire(payload)
            if "status" in payload:
                raise ValueError("Wire payload cannot assert verification")
            event = VerifiedEvent.model_validate(dict(payload, status="VERIFIED"))
            now = time.time()
            if (
                event.agent_id != self.agent_id
                or event.timestamp is None
                or abs(now - event.timestamp) > 300
                or not event.event_id
                or not event.upstream_task_id
                or not event.external_submission_id
                or type(event.sequence) is not int
                or event.sequence not in (1, 2)
                or len(event.event_id) > 128
                or event.event_id != f"{event.upstream_task_id}:{event.sequence}"
                or not ID.fullmatch(event.upstream_task_id)
                or not ID.fullmatch(event.external_submission_id)
                or event.state
                not in ({"RUNNING"} if event.sequence == 1 else {"RESULT_READY", "FAILED"})
                or (event.state != "RESULT_READY" and event.result is not None)
            ):
                raise ValueError("Invalid event identity or timestamp")
            with self._lock:
                self._seen = {key: value for key, value in self._seen.items() if now - value <= 300}
                if event.event_id in self._seen:
                    return event.model_copy(update={"status": "DUPLICATE"})
                if len(self._seen) >= 10000:
                    raise ValueError("Callback verification capacity exceeded")
                self._seen[event.event_id] = event.timestamp
            return event
        except (ValueError, TypeError, ValidationError):
            return VerifiedEvent(status="INVALID", **fallback)
