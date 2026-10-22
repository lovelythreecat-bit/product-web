"""Present two model roles; publish a new upstream graph only after it is complete.

Provider keys remain owned by imageAgent. Reuse unchanged services when a key is
omitted; never patch existing resources used by historical platform connections.
"""

from app.admin.media_schemas import MediaConnectionUpdate, project_resource, resource_body
from app.agents.media_connection import (
    connection_head,
    current_connection_view,
    read_media_connection,
    update_media_connection,
)
from app.agents.media_http import MediaServiceError


def _read(upstream, resource, identity, versions):
    path = f"/api/v1/{resource}/{identity}"
    _, raw = upstream.json("GET", path)
    value = project_resource("image", resource, raw)
    if value["id"] != str(identity):
        raise MediaServiceError()
    # A resource referenced by both roles must not change midway through a read.
    if path in versions and versions[path] != value["version"]:
        raise MediaServiceError(409, "模型配置已更新，请关闭后重新打开编辑。")
    versions[path] = value["version"]
    return value


def _state(session, settings, upstream):
    connection = current_connection_view(session, settings, "image")
    result = dict(revision=connection.revision, versions={}, text_model=None, image_model=None)
    graph = dict(scheme=None, roles={})
    if not connection.default_config_id:
        return result, graph
    scheme = _read(upstream, "agent-configs", connection.default_config_id, result["versions"])
    graph["scheme"] = scheme
    targets = {
        "text_model": scheme["stages"].get("vision"),
        "image_model": scheme["image_models"].get(connection.image_model),
    }
    for role, identity in targets.items():
        if not identity:
            raise MediaServiceError(422, "当前图片配置缺少文字或生图模型绑定，请检查原方案。")
        model = _read(upstream, "model-configs", identity, result["versions"])
        service = _read(upstream, "services", model["service_id"], result["versions"])
        expected = (
            {"chat_completions"} if role == "text_model" else {"openai_images", "openrouter_images"}
        )
        if service["protocol"] not in expected:
            raise MediaServiceError(422, "当前模型协议与用途不匹配，请检查原方案。")
        graph["roles"][role] = dict(model=model, service=service)
        result[role] = dict(
            base_url=service["base_url"],
            protocol=service["protocol"],
            model=model["model"],
            has_api_key=service["has_api_key"],
            enabled=scheme["enabled"] and model["enabled"] and service["enabled"],
        )
    return result, graph


def read_image_models(session, settings, upstream):
    return _state(session, settings, upstream)[0]


def _create(upstream, resource, body):
    body = resource_body("image", resource, body)
    _, raw = upstream.json("POST", "/api/v1/" + resource, body)
    return project_resource("image", resource, raw)


def save_image_models(session, settings, upstream, dto, actor_id):
    head = connection_head(session, "image", lock=True)
    if head.revision != dto.expected_revision:
        raise MediaServiceError(409, "图片配置已更新，请关闭后重新打开编辑。")
    view, graph = _state(session, settings, upstream)
    if view["versions"] != dto.expected_versions:
        raise MediaServiceError(409, "模型配置已更新，请关闭后重新打开编辑。")
    # Require a working connection before creating any upstream resources.
    read_media_connection(session, settings, "image")
    reusable = {}
    for role in ("text_model", "image_model"):
        desired = getattr(dto, role)
        previous = graph["roles"].get(role)
        service = previous["service"] if previous else None
        reusable[role] = bool(
            service
            and service["enabled"]
            and service["has_api_key"]
            and service["base_url"] == desired.base_url
            and service["protocol"] == desired.protocol
        )
        if desired.api_key is None and not reusable[role]:
            label = "文字模型" if role == "text_model" else "图片生成模型"
            raise MediaServiceError(
                422, f"{label}首次配置或更换 API 地址、协议时，请填写 API Key。"
            )

    models = {}
    for role in ("text_model", "image_model"):
        desired = getattr(dto, role)
        previous = graph["roles"].get(role)
        label = "文字模型" if role == "text_model" else "图片生成模型"
        if desired.api_key is None:
            service = previous["service"]
        else:
            # Preserve custom endpoint paths for rotations on the same protocol/origin.
            paths = (
                {
                    key: previous["service"][key]
                    for key in ("generation_path", "edit_path", "chat_path")
                }
                if reusable[role]
                else {}
            )
            service = _create(
                upstream,
                "services",
                dict(
                    name=label,
                    base_url=desired.base_url,
                    protocol=desired.protocol,
                    api_key=desired.api_key.get_secret_value(),
                    **paths,
                ),
            )
        if (
            previous
            and previous["model"]["enabled"]
            and previous["model"]["service_id"] == service["id"]
            and previous["model"]["model"] == desired.model
        ):
            models[role] = previous["model"]
        else:
            models[role] = _create(
                upstream,
                "model-configs",
                dict(service_id=service["id"], model=desired.model, description=label),
            )
    parameters = graph["scheme"]["parameters"] if graph["scheme"] else {}
    scheme = _create(
        upstream,
        "agent-configs",
        dict(
            name="图片创作",
            parameters=parameters,
            image_models={"fast": models["image_model"]["id"]},
            stages={"vision": models["text_model"]["id"]},
        ),
    )
    # Only the complete new graph is activated. A failed POST leaves the old
    # connection and every old service/model/scheme intact; no generation is run.
    update_media_connection(
        session,
        settings,
        "image",
        MediaConnectionUpdate(
            expected_revision=dto.expected_revision,
            default_config_id=scheme["id"],
            image_model="fast",
        ),
        actor_id,
    )
    return read_image_models(session, settings, upstream)
