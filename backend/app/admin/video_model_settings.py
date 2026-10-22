"""Expose actual videoAgent model roles; keep credentials and atomic writes upstream."""

from urllib.parse import quote

from app.admin.media_schemas import project_resource, resource_body
from app.agents.media_connection import connection_head, current_connection_view
from app.agents.media_http import MediaServiceError

ROOT = "/api/v1/admin/"
ADAPTERS = {"planner": {"openai_chat"}, "video": {"seedance", "wan"}, "visual": {"openai_vision"}}
LABELS = {"planner": "分镜文本模型", "video": "视频生成模型", "visual": "视觉检查模型"}


def _read(upstream, resource, identity=None):
    path = ROOT + resource + ("/" + quote(identity, safe="") if identity else "")
    _, raw = upstream.json("GET", path)
    value = project_resource("video", resource, raw)
    if identity is not None and value.get("profile_id") != identity:
        raise MediaServiceError()
    return value


def _state(upstream):
    bindings = _read(upstream, "adapter-bindings")
    models = {}
    for role in ADAPTERS:
        target = bindings[role]
        identity = target["profile_id"]
        model = _read(upstream, "model-profiles", identity) if identity else None
        if model and (model["role"] != role or model["adapter"] != target["adapter"]):
            raise MediaServiceError()
        models[role] = model
    if _read(upstream, "adapter-bindings") != bindings:
        raise MediaServiceError(409, "视频配置已更新，请关闭后重新打开编辑。")
    return bindings, models


def _view(revision, bindings, models):
    public = {}
    for role, model in models.items():
        public[role] = (
            None
            if model is None
            else {
                key: model[key]
                for key in (
                    "profile_id",
                    "version",
                    "adapter",
                    "base_url",
                    "model",
                    "enabled",
                    "has_api_key",
                )
            }
        )
        if public[role] is not None:
            public[role]["max_segment_seconds"] = model["parameters"].get("max_segment_seconds")
    return dict(
        revision=revision,
        configuration_revision=bindings["configuration_revision"],
        models=public,
        bindings=bindings,
    )


def read_video_models(session, settings, upstream):
    bindings, models = _state(upstream)
    return _view(current_connection_view(session, settings, "video").revision, bindings, models)


def save_video_model(session, settings, upstream, role, dto):
    if role not in ADAPTERS:
        raise MediaServiceError(404)
    head = connection_head(session, "video", lock=True)
    bindings, models = _state(upstream)
    previous = models[role]
    if (
        head.revision != dto.expected_revision
        or bindings["configuration_revision"] != dto.expected_configuration_revision
        or (previous["profile_id"] if previous else None) != dto.expected_profile_id
        or (previous["version"] if previous else None) != dto.expected_profile_version
    ):
        raise MediaServiceError(409, "视频配置已更新，请关闭后重新打开编辑。")
    if not dto.enabled:
        if role != "visual":
            raise MediaServiceError(422, "真实出片需要分镜文本模型和视频生成模型。")
        body = dict(expected_version=bindings["configuration_revision"], visual={"adapter": "none"})
        upstream.json("PATCH", ROOT + "adapter-bindings", body)
        return read_video_models(session, settings, upstream)
    if dto.adapter not in ADAPTERS[role]:
        raise MediaServiceError(422, "模型类型与用途不匹配。")
    if not dto.base_url or not dto.model or not dto.model.strip():
        raise MediaServiceError(422, f"{LABELS[role]}请填写 API 地址和模型名称。")
    if dto.adapter == "wan" and dto.max_segment_seconds is None:
        raise MediaServiceError(422, "万相模型请填写单段最长秒数（1–15）。")
    same = bool(
        previous
        and previous["enabled"]
        and previous["has_api_key"]
        and previous["adapter"] == dto.adapter
        and previous["base_url"] == dto.base_url
    )
    if dto.api_key is None and not same:
        raise MediaServiceError(422, "首次配置或更换 API 地址、供应商时，请填写 API Key。")
    parameters = (
        dict(previous["parameters"]) if previous and previous["adapter"] == dto.adapter else {}
    )
    if dto.adapter == "wan":
        parameters["max_segment_seconds"] = dto.max_segment_seconds
    if dto.api_key is None:
        # Updating the already bound profile is one upstream transaction. Empty
        # secrets are never copied back to web or to another provider address.
        changed = previous["model"] != dto.model.strip() or previous["parameters"] != parameters
        if changed:
            body = resource_body(
                "video",
                "model-profiles",
                dict(
                    expected_version=previous["version"],
                    model=dto.model.strip(),
                    parameters=parameters,
                ),
                patch=True,
            )
            upstream.json(
                "PATCH", ROOT + "model-profiles/" + quote(previous["profile_id"], safe=""), body
            )
        result = read_video_models(session, settings, upstream)
        active = result["models"][role]
        if (
            result["configuration_revision"] != bindings["configuration_revision"] + int(changed)
            or active is None
            or active["profile_id"] != previous["profile_id"]
            or active["version"] != previous["version"] + int(changed)
        ):
            # The HTTP profile PATCH cannot guard the global configuration
            # revision. Detect concurrent rebindings instead of claiming the
            # administrator's edit was applied to the currently active model.
            raise MediaServiceError(409, "视频配置已更新，请关闭后重新打开编辑。")
        return result
    body = resource_body(
        "video",
        "model-profiles",
        dict(
            name=LABELS[role],
            role=role,
            adapter=dto.adapter,
            base_url=dto.base_url,
            model=dto.model.strip(),
            parameters=parameters,
            enabled=True,
            secrets={"api_key": dto.api_key.get_secret_value()},
        ),
    )
    _, raw = upstream.json("POST", ROOT + "model-profiles", body)
    profile = project_resource("video", "model-profiles", raw)
    if profile["role"] != role or profile["adapter"] != dto.adapter or not profile["enabled"]:
        raise MediaServiceError()
    current = _read(upstream, "adapter-bindings")
    # Creating a profile increments the global revision once. Any other write
    # between the read and activation must cause a conflict, never overwrite it.
    if current["configuration_revision"] != bindings["configuration_revision"] + 1 or any(
        current[key] != bindings[key] for key in (*ADAPTERS, "voice", "music")
    ):
        raise MediaServiceError(409, "视频配置已更新，请关闭后重新打开编辑。")
    upstream.json(
        "PATCH",
        ROOT + "adapter-bindings",
        dict(
            expected_version=current["configuration_revision"],
            **{role: {"profile_id": profile["profile_id"]}},
        ),
    )
    return read_video_models(session, settings, upstream)
