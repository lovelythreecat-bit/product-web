from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(
    "state,upstream,action",
    [
        ("SUBMITTED", None, "prepare_submission"),
        ("QUEUED", None, "prepare_submission"),
        ("SUBMITTING", None, "reconcile_submission"),
        ("RUNNING", "original", "query_original"),
        ("INVESTIGATING", None, "investigate"),
        ("QUEUED", "original", "query_original"),
        ("SUBMITTING", "original", "query_original"),
        ("SAVING", "original", "save_original"),
        ("SAVE_RECOVERY", "original", "save_original"),
        ("SUCCEEDED", "original", None),
        ("FAILED", None, None),
        ("MANUALLY_CLOSED", None, None),
    ],
)
def test_recovery_uses_persisted_stage(state, upstream, action):
    from app.dispatch.recovery import recovery_action

    assert recovery_action(SimpleNamespace(state=state, upstream_id=upstream)) == action
