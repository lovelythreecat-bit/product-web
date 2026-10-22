"""Code-owned media protocol identities; pricing and policy gates remain independent."""

from uuid import NAMESPACE_URL, uuid5

from app.catalog.models import AgentHead, AgentRecord
from app.catalog.schemas import AgentVersion


def managed_media_agent_id(mode, kind):
    if kind not in {"image", "video"}:
        raise ValueError("Unsupported media kind")
    return uuid5(NAMESPACE_URL, f"ecommerce-ai-platform:{kind}:{mode}")


def managed_media_input_support(kind):
    if kind not in {"image", "video"}:
        raise ValueError("Unsupported media kind")
    return dict(
        product_required_fields=["name", "category"] if kind == "image" else ["name"],
        instruction_required=False,
        min_materials=1,
        max_materials=8,
    )


def sync_media_agent(session, settings, kind):
    identity = str(managed_media_agent_id(settings.mode, kind))
    version = kind + "-agent-v1"
    head = session.get(AgentHead, identity, with_for_update=True)
    if session.get(AgentRecord, (identity, version)) is None:
        value = AgentVersion(
            agent_id=identity,
            version=version,
            name="图片创作" if kind == "image" else "视频创作",
            kind=kind,
            mode=settings.mode,
            test_only=settings.test_only,
            enabled=True,
            protocol_version=version,
            input_support=managed_media_input_support(kind),
            policy_versions={},
            secret_configured=True,
        )
        session.add(
            AgentRecord(
                agent_id=identity,
                version=version,
                snapshot=value.model_dump(mode="json"),
                endpoint="database:" + kind,
                secret_ref="database:" + kind,
            )
        )
        session.flush()
    if head is None:
        session.add(AgentHead(agent_id=identity, version=version))
    else:
        head.version = version
    session.flush()
