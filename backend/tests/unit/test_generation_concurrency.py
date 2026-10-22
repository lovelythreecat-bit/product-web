import pytest
from pydantic import ValidationError

from app.policies.schemas import ConcurrencyPolicy


def test_explicit_null_allows_independent_generations_without_an_account_task_cap():
    policy = ConcurrencyPolicy.model_validate(
        {"max_concurrent_tasks": None, "enforcement_ref": "user-approved-parallel-generation"}
    )
    assert policy.max_concurrent_tasks is None


@pytest.mark.parametrize("limit", [0, -1])
def test_numeric_limits_still_require_positive_values(limit):
    with pytest.raises(ValidationError):
        ConcurrencyPolicy(max_concurrent_tasks=limit, enforcement_ref="test")


def test_missing_limit_does_not_silently_remove_an_existing_policy_gate():
    with pytest.raises(ValidationError):
        ConcurrencyPolicy(enforcement_ref="test")
