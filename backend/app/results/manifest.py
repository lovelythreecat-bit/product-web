"""Task-bound, exact-version completion rules for explicitly configured protocols."""

from app.agents.contracts import ResultManifest
from app.agents.mock_server import PROTOCOL
from app.agents.text import PROTOCOL as TEXT_PROTOCOL
from app.agents.text import TextAgentAdapter
from app.agents.text_parameters import validate_text_parameters
from app.catalog.schemas import AgentVersion, content_digest, single_spec
from app.policies.service import PolicyService
from app.tasks.models import TaskSnapshot
from app.tasks.state_machine import TransitionError


def exact_policy(session, snapshot, decision):
    version = snapshot.policy_versions.get(decision)
    record = PolicyService(session)._read(decision, version) if version else None
    mode = snapshot.agent_snapshot.get("mode", "mock")
    if (
        record is None
        or record.mode != mode
        or (mode == "mock" and not record.test_only)
        or (mode != "mock" and (record.test_only or record.status != "confirmed"))
    ):
        raise TransitionError("RESULT_POLICY_UNAVAILABLE")
    return record.payload


def result_rule(session, task, binding):
    snapshot = session.get(TaskSnapshot, task.id)
    spec = snapshot.spec_snapshot
    try:
        if binding.protocol_version in {"image-agent-v1", "video-agent-v1"}:
            return media_result_rule(session, task, snapshot, binding)
        if "platform-pricing" in snapshot.quote.get("policy_versions", {}):
            agent = AgentVersion.model_validate(snapshot.agent_snapshot)
            text_protocol = (
                binding.protocol_version == TEXT_PROTOCOL
                and isinstance(binding.adapter, TextAgentAdapter)
                and binding.wire_agent_id == "copy"
                and agent.kind == "copy"
            )
            mock_protocol = (
                binding.protocol_version == PROTOCOL
                and binding.adapter.test_only
                and agent.mode == "mock"
                and agent.test_only
            )
            protocol = exact_policy(session, snapshot, "D-01")["agents"][str(agent.agent_id)]
            parameters = snapshot.input_snapshot.get("parameters")
            if text_protocol:
                validate_text_parameters(parameters)
            elif parameters != {}:
                raise ValueError()
            if (
                not (text_protocol or mock_protocol)
                or str(agent.agent_id) != task.agent_id
                or agent.version != task.agent_version
                or agent.kind != binding.wire_agent_id
                or agent.protocol_version != binding.protocol_version
                or protocol["protocol_version"] != binding.protocol_version
                or spec != single_spec(agent).model_dump(mode="json")
            ):
                raise ValueError()
            return dict(
                protocol_version=binding.protocol_version,
                spec_version=agent.version,
                spec_digest=content_digest(spec),
                expected_item_keys=["original-1"],
                media_type={"copy": "text/plain", "image": "image/png", "video": "video/mp4"}[
                    agent.kind
                ],
            )
        rule = exact_policy(session, snapshot, "D-01")["result_specs"][spec["spec_id"]]
        text_protocol = (
            binding.protocol_version == TEXT_PROTOCOL
            and isinstance(binding.adapter, TextAgentAdapter)
            and binding.wire_agent_id == "copy"
            and spec.get("delivery_kind", "single") == "single"
        )
        mock_protocol = binding.protocol_version == PROTOCOL and binding.adapter.test_only
        if (
            not (text_protocol or mock_protocol)
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
    if rule.get("media_kind"):
        if manifest.model_dump(mode="json") != rule["expected_manifest"]:
            raise TransitionError("RESULT_MANIFEST_MISMATCH")
        return manifest
    for index, item in enumerate(manifest.items):
        suffix = "" if len(keys) == 1 else f"/original-{index + 1}"
        if (
            item.locator != f"/v1/{binding.wire_agent_id}/results/{upstream_id}{suffix}"
            or item.media_type != rule["media_type"]
        ):
            raise TransitionError("RESULT_MANIFEST_MISMATCH")
    return manifest


def media_result_rule(session, task, snapshot, binding):
    from app.agents.media_execution import MediaExecution, validate_media_input
    from app.common.types import InputSnapshot
    from app.policies.schemas import DeliveryPolicy

    agent = AgentVersion.model_validate(snapshot.agent_snapshot)
    protocol = exact_policy(session, snapshot, "D-01")["agents"][str(agent.agent_id)]
    kind = agent.kind
    route = snapshot.routing_snapshot or {}
    execution = session.get(MediaExecution, task.id)
    if (kind not in {"image", "video"} or binding.wire_agent_id != kind
            or binding.protocol_version != {"image": "image-agent-v1",
                                            "video": "video-agent-v1"}[kind]
            or agent.protocol_version != binding.protocol_version
            or str(agent.agent_id) != task.agent_id or agent.version != task.agent_version
            or protocol["protocol_version"] != binding.protocol_version
            or route.get("protocol_version") != binding.protocol_version
            or snapshot.spec_snapshot != single_spec(agent).model_dump(mode="json")
            or execution is None or execution.kind != kind
            or execution.state.get("upstream_task_id") != task.upstream_id):
        raise ValueError("Media result identity mismatch")
    validate_media_input(kind, InputSnapshot.model_validate(snapshot.input_snapshot))
    state = execution.state
    if kind == "image":
        from app.agents.image import ImageAgentAdapter, expected_image_targets, image_item_key

        if not isinstance(binding.adapter, ImageAgentAdapter):
            raise ValueError()
        targets = expected_image_targets({"input_snapshot": snapshot.input_snapshot})
        keys = [image_item_key(target) for target in targets]
        if len(keys) > 1:
            DeliveryPolicy.model_validate(
                exact_policy(session, snapshot, "D-04")["specs"][task.agent_id])
        manifest = ResultManifest.model_validate(state["manifest"])
        if any(not item.locator.startswith(f"/api/v1/tasks/{task.upstream_id}/blobs/")
               or item.media_type not in {"image/png", "image/jpeg", "image/webp"}
               for item in manifest.items):
            raise ValueError()
    else:
        from app.agents.contracts import ResultItem
        from app.agents.video import VideoAgentAdapter

        if (not isinstance(binding.adapter, VideoAgentAdapter)
                or not state.get("generation_id") or not state.get("confirmed_plan_version")):
            raise ValueError()
        keys = ["original-1"]
        manifest = ResultManifest(complete=True, expected_items=1, items=(ResultItem(
            item_key="original-1", locator=f"/api/v1/artifacts/{state['artifact_id']}/content",
            media_type="video/mp4", sha256=state["artifact_sha256"],
            byte_length=state["artifact_byte_length"]),))
    if [item.item_key for item in manifest.items] != keys:
        raise ValueError()
    return dict(media_kind=kind, expected_item_keys=keys,
                expected_manifest=manifest.model_dump(mode="json"),
                protocol_version=binding.protocol_version,
                spec_version=agent.version, spec_digest=content_digest(snapshot.spec_snapshot))
