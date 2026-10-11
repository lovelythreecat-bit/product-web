"""Task-bound, exact-version TEST_ONLY completion rules; production remains disabled."""

from app.agents.contracts import ResultManifest
from app.agents.mock_server import PROTOCOL
from app.catalog.schemas import content_digest
from app.policies.service import PolicyService
from app.tasks.models import TaskSnapshot
from app.tasks.state_machine import TransitionError


def exact_policy(session, snapshot, decision):
    version = snapshot.policy_versions.get(decision)
    record = PolicyService(session)._read(decision, version) if version else None
    if record is None or record.mode != "mock" or not record.test_only:
        raise TransitionError("RESULT_POLICY_UNAVAILABLE")
    return record.payload


def result_rule(session, task, binding):
    snapshot = session.get(TaskSnapshot, task.id)
    spec = snapshot.spec_snapshot
    try:
        rule = exact_policy(session, snapshot, "D-01")["result_specs"][spec["spec_id"]]
        if (
            binding.protocol_version != PROTOCOL
            or not binding.adapter.test_only
            or rule["protocol_version"] != binding.protocol_version
            or rule["spec_version"] != spec["version"]
            or rule["spec_digest"] != content_digest(spec)
        ):
            raise ValueError()
        keys = rule["expected_item_keys"]
        expected = (
            ["original-1"]
            if spec.get("delivery_kind", "single") == "single"
            else ["original-1", "original-2"]
        )
        if keys != expected:
            raise ValueError()
        if len(keys) == 2:
            from app.catalog.schemas import ParameterSchema

            parameters = snapshot.input_snapshot["parameters"]
            if parameters != {"test_only_result_count": 2} or not ParameterSchema.model_validate(
                spec["parameter_schema"]
            ).accepts(parameters):
                raise ValueError()
            delivery = exact_policy(session, snapshot, "D-04")["result_specs"][spec["spec_id"]]
            if delivery != dict(rule, delivery="complete_only"):
                raise ValueError()
        mime = {"copy": "text/plain", "image": "image/png", "video": "video/mp4"}[
            binding.wire_agent_id
        ]
        if rule["media_type"] != mime:
            raise ValueError()
        return rule
    except (KeyError, TypeError, ValueError):
        raise TransitionError("RESULT_POLICY_UNAVAILABLE") from None


def validate_manifest(manifest, rule, binding, upstream_id):
    manifest = ResultManifest.model_validate(manifest)
    keys = rule["expected_item_keys"]
    if (
        not manifest.complete
        or manifest.expected_items != len(keys)
        or [item.item_key for item in manifest.items] != keys
    ):
        raise TransitionError("RESULT_MANIFEST_MISMATCH")
    for index, item in enumerate(manifest.items):
        suffix = "" if len(keys) == 1 else f"/original-{index + 1}"
        if (
            item.locator != f"/v1/{binding.wire_agent_id}/results/{upstream_id}{suffix}"
            or item.media_type != rule["media_type"]
        ):
            raise TransitionError("RESULT_MANIFEST_MISMATCH")
    return manifest
