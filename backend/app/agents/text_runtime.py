"""A single database-owned connection and default model for new text tasks."""

from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import Field, ValidationError

from app.admin.text_model_schemas import TextModelView
from app.agents.model_configs import TextModelClient, TextModelError
from app.agents.service_connection import connection_row, read_service_connection
from app.agents.text import PROTOCOL, TextAgentProfile, TextAgentRouting
from app.catalog.models import AgentHead, AgentRecord
from app.catalog.schemas import AgentVersion
from app.common.types import ConfigurationChange, DTO

DATABASE_PROFILE = "database:text"


class TextDefaultModelView(DTO):
    model_config_id: UUID | None
    revision: int = Field(ge=0)
    connection_revision: int = Field(ge=0)
    generation_policy_configured: bool = False


class TextDefaultModelUpdate(ConfigurationChange):
    model_config_id: UUID
    expected_revision: int = Field(strict=True, ge=0)
    expected_connection_revision: int = Field(strict=True, ge=0)


def default_view(row, settings=None):
    return TextDefaultModelView(
        model_config_id=getattr(row, "default_model_id", None),
        revision=getattr(row, "default_revision", 0), connection_revision=row.revision,
        generation_policy_configured=settings is not None and {
            "D-01", "D-03", "D-05", "D-08", "D-09", "D-10",
        }.issubset(settings.generation_policy_versions),
    )


def remote_model(connection, config_id):
    raw = TextModelClient(connection).request("GET", "/" + str(config_id))
    try:
        model = TextModelView.model_validate(raw)
    except ValidationError:
        raise TextModelError() from None
    if model.id != config_id:
        raise TextModelError()
    if not model.enabled or not model.has_api_key or model.provider != "openai_chat":
        raise TextModelError(
            422, public_message="默认文本模型不可用，请选择已启用且已配置密钥的模型。",
        )
    return model


def managed_agent_id(mode):
    return uuid5(NAMESPACE_URL, "ecommerce-ai-platform:text:" + mode)


def managed_input_support():
    # The service contract is stable across model switches. A model's actual image
    # support is checked against the submitted materials before freezing credits.
    return dict(product_required_fields=["name"], instruction_required=False,
                min_materials=0, max_materials=4)


def sync_text_agent(session, settings, model):
    """Publish an internal technical identity; no endpoint, key or model replica."""
    identity = str(managed_agent_id(settings.mode))
    support = managed_input_support()
    # A code-owned protocol identity is not a second administrator-authored config.
    # Model changes do not invalidate pricing specs bound to this service contract.
    policies = {}
    version = PROTOCOL
    head = session.get(AgentHead, identity, with_for_update=True)
    if session.get(AgentRecord, (identity, version)) is None:
        value = AgentVersion(
            agent_id=identity, version=version, name="文本创作", kind="copy",
            mode=settings.mode, test_only=settings.test_only, enabled=True,
            protocol_version=PROTOCOL, input_support=support, policy_versions=policies,
            secret_configured=True,
        )
        session.add(AgentRecord(agent_id=identity, version=version,
            snapshot=value.model_dump(mode="json"), endpoint=DATABASE_PROFILE,
            secret_ref=DATABASE_PROFILE))
        session.flush()
    if head is None:
        session.add(AgentHead(agent_id=identity, version=version))
    else:
        head.version = version
    session.flush()


def resolve_text_profile(session, settings, *, routing=None):
    connection = read_service_connection(session, settings)
    if routing is None:
        row = connection_row(session)
        config_id = getattr(row, "default_model_id", None)
        if not config_id:
            raise TextModelError(422, public_message="请先在后台指定默认文本模型。")
        model = remote_model(connection, UUID(config_id))
        supports_images, model_id = model.supports_images, model.id
    else:
        fixed = TextAgentRouting.model_validate(routing)
        if (fixed.profile != DATABASE_PROFILE or fixed.protocol_version != PROTOCOL
                or fixed.base_url != connection.base_url):
            raise LookupError("Original text service connection is unavailable")
        # Never resolve the current default while executing/recovering an existing task.
        supports_images, model_id = fixed.supports_images, fixed.model_config_id
    return TextAgentProfile(base_url=connection.base_url, service_key=connection.service_key,
                            model_config_id=model_id, supports_images=supports_images)
