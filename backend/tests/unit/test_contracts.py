from uuid import UUID

import pytest
from pydantic import ValidationError

from app.common.types import PageQuery, Quote, TaskView


def quote_payload():
    return {
        "spec_id": "9f0bb21f-f1f9-4b54-9fe2-cf2463626e09",
        "spec_version": "TEST_ONLY-v1",
        "price_version": "TEST_ONLY-v1",
        "agent_version": "TEST_ONLY-v1",
        "policy_versions": {},
        "credits": 1,
        "input_digest": "test-input-digest",
    }


@pytest.mark.parametrize("credits", [-1, True, 1.5, "2"])
def test_quote_credits_reject_invalid_integer_amounts(credits):
    with pytest.raises(ValidationError):
        Quote(**(quote_payload() | {"credits": credits}))


def test_task_view_cannot_serialize_private_diagnostics():
    with pytest.raises(ValidationError):
        TaskView(
            task_id=UUID("abd3b968-9170-46d7-befa-1a084f7d36e1"),
            state="SAVING",
            state_version=1,
            settlement_state="FROZEN",
            quote=Quote(**quote_payload()),
            work_ids=[],
            investigation_reason=None,
            input={"secret": "private user input"},
            internal_path="/private/source",
        )


@pytest.mark.parametrize("limit", [0, -1, 101])
def test_cursor_page_limits_are_bounded(limit):
    with pytest.raises(ValidationError):
        PageQuery(limit=limit)
