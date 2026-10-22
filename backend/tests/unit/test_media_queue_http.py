"""Only the image service's documented pre-admission queue refusal is replayable."""

import json
from io import BytesIO
from types import SimpleNamespace

import pytest

from app.agents.media_http import MediaClient, MediaServiceError


@pytest.mark.parametrize("payload,expected", [
    ({"code": "queue_full", "request_id": "trace"}, True),
    ({"code": "queue_full", "task_id": "accepted"}, False),
    ({"code": "model_rate_limited"}, False),
    ({"error": {"code": "concurrency_limit"}}, False),
    ({}, False),
])
def test_queue_rejection_requires_exact_bounded_unaccepted_reply(monkeypatch, payload, expected):
    response = BytesIO(json.dumps(payload).encode())
    response.status = 429
    response.headers = {"Retry-After": "7"}
    monkeypatch.setattr("app.agents.media_http.build_opener", lambda *a: SimpleNamespace(
        open=lambda *a, **kw: response,
    ))
    client = MediaClient("http://localhost:8123", "TEST_ONLY_key")
    with pytest.raises(MediaServiceError) as caught:
        client.json("POST", "/api/v1/tasks", {}, idempotency_key="original-key")
    assert caught.value.status_code == 429
    assert caught.value.retryable_rejection is expected
    assert caught.value.retry_after_seconds == 7
    assert "TEST_ONLY_key" not in str(caught.value)
