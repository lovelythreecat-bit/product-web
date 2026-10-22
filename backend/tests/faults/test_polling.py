"""Polling shares durable callback reduction without new generation."""

import pytest
from sqlalchemy import select

from app.agents.models import UpstreamEvidence
from app.tasks.models import GenerationTask
from tests.faults.test_upstream_recovery import calls, submit
from tests.faults.test_upstream_recovery import upstream as upstream_fixture
from tests.integration.test_callbacks import reducer

upstream = upstream_fixture


@pytest.mark.parametrize("scenario", ["query_unavailable", "not_found", "unsupported"])
def test_query_timeout_no_resubmit(upstream, scenario):
    task = upstream[2](scenario)
    submit(upstream, task)
    assert reducer(upstream).poll_original_task(task).state == "INVESTIGATING"
    assert calls(upstream, task)["submit"] == 1
    assert calls(upstream, task)["query_id"] == 1


def test_durable_result_before_crash_survives_later_query_failure(upstream, monkeypatch):
    factory, service, create, server, _ = upstream
    task = create()
    submit(upstream, task)
    original = service._apply_observation

    def crash(*args, **kwargs):
        raise SystemExit("TEST_ONLY before reduction")

    monkeypatch.setattr(service, "_apply_observation", crash)
    with pytest.raises(SystemExit):
        service.recover_original_task(task)
    monkeypatch.setattr(service, "_apply_observation", original)
    with factory() as s:
        row = s.get(GenerationTask, task)
        server.simulator.records["copy", row.external_submission_id]["scenario"] = (
            "query_unavailable"
        )
        assert s.scalar(
            select(UpstreamEvidence).where(
                UpstreamEvidence.task_id == task, UpstreamEvidence.kind == "observation"
            )
        )
    assert reducer(upstream).poll_original_task(task).state == "SAVING"
    assert reducer(upstream).original_result(task).manifest.complete
    assert calls(upstream, task)["query_id"] == 1


def test_actual_worker_reduces_original_result(upstream):
    task = upstream[2]()
    submit(upstream, task)
    worker = upstream[4]()
    assert worker.tick()[2].handled >= 1
    assert reducer(upstream)._view(task).state == "SAVING"
    assert calls(upstream, task)["submit"] == 1


def test_transport_timeout_only_queries_original(upstream, monkeypatch):
    from app.agents.mock import MockAgentAdapter

    task = upstream[2]()
    submit(upstream, task)
    original = MockAgentAdapter._request

    def timeout(self, method, path, body=None):
        if "/tasks/" in path:
            raise TimeoutError("TEST_ONLY query timeout")
        return original(self, method, path, body)

    monkeypatch.setattr(MockAgentAdapter, "_request", timeout)
    assert reducer(upstream).poll_original_task(task).state == "INVESTIGATING"
    assert calls(upstream, task)["submit"] == 1
