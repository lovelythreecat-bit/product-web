"""Real HTTP receipt, SQL evidence reduction and frozen-credit preservation."""
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.ledger.models import CreditLedger
from app.tasks.failed_actions import FailedTaskActions
from app.tasks.models import GenerationTask
from app.tasks.stopped_image_retry import verify_stopped_image
from tests.integration.test_media_queue import image_queue, image_http_runtime, upstream


@pytest.mark.parametrize("image_calls", [0, 1])
def test_owner_retry_uses_fresh_receipt_and_keeps_frozen_credits(image_queue, monkeypatch, image_calls):
    factory, service, task_id, submit, _, remote, _, _ = image_queue
    remote["scenario"] = "accepted"
    remote["image_calls"] = image_calls
    assert submit().state == "RUNNING"
    assert service.recover_original_task(task_id).investigation_reason == "UPSTREAM_NEEDS_INPUT"
    # Fixture task has no browser login. Keep real SQL/leases/proof/HTTP; bypass only auth.
    monkeypatch.setattr(FailedTaskActions, "_owned", lambda self, actor, key: self.session.get(GenerationTask, key))
    if image_calls:
        with pytest.raises(HTTPException) as refused:
            verify_stopped_image(service, None, task_id, None)
        assert refused.value.status_code == 409
    else:
        verify_stopped_image(service, None, task_id, None)
    with factory() as session:
        task = session.get(GenerationTask, task_id)
        assert task.state == ("INVESTIGATING" if image_calls else "FAILED")
        assert task.settlement_state == "FROZEN"
        assert task.lease_owner is None
        assert not session.scalars(select(CreditLedger).where(
            CreditLedger.task_id == task_id, CreditLedger.kind.in_(["release", "consume"]),
        )).all()
    assert len(remote["posts"]) == 1
