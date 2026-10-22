"""Admin-only resource gateway; provider configurations remain owned by media services."""

from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.admin.image_model_settings import read_image_models, save_image_models
from app.admin.media_schemas import (
    ImageModelsUpdate,
    ImageModelsView,
    MediaConnectionUpdate,
    MediaConnectionView,
    MediaKind,
    MediaResourceWrite,
    VideoAudioUpdate,
    VideoModelRole,
    VideoModelUpdate,
    project_resource,
    resource_body,
)
from app.admin.permissions import authorize_admin
from app.admin.video_model_settings import read_video_models, save_video_model
from app.agents.media_connection import (
    connection_head,
    connection_view,
    current_connection_view,
    read_media_connection,
    update_media_connection,
)
from app.agents.media_http import MediaClient, MediaServiceError
from app.agents.media_runtime import sync_media_agent
from app.audit.service import audit_admin
from app.auth.routes import DB, PrincipalDep, require_csrf
from app.common.errors import ErrorResponse

router = APIRouter(
    prefix="/api/v1/admin/media-agents",
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 429, 503)},
)
SINGLETONS = {"adapter-bindings", "settings"}
RESOURCES = {
    "image": {"services", "model-configs", "agent-configs"},
    "video": {"adapter-types", "model-profiles", *SINGLETONS},
}


def resource_path(kind, resource, config_id=None):
    if resource not in RESOURCES.get(kind, set()):
        raise MediaServiceError(404)
    if config_id is not None and (resource in SINGLETONS or resource == "adapter-types"):
        raise MediaServiceError(404)
    prefix = "/api/v1/" if kind == "image" else "/api/v1/admin/"
    return prefix + resource + ("/" + str(config_id) if config_id else "")


def client(request, session, kind):
    connection = read_media_connection(session, request.app.state.settings, kind)
    key = connection.management_key or connection.service_key
    return MediaClient(connection.base_url, key)


@router.get("/video/models", operation_id="admin_video_models")
def get_video_models(request: Request, session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    connection_head(session, "video", lock=True)
    return read_video_models(session, request.app.state.settings, client(request, session, "video"))


@router.get("/video/audio", operation_id="admin_video_audio")
def get_video_audio(request: Request, session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    settings = request.app.state.settings
    head = connection_head(session, "video", lock=True)
    value = read_media_connection(session, settings, "video")
    return dict(revision=head.revision, enabled=value.video_audio_enabled)


@router.patch(
    "/video/audio", operation_id="admin_save_video_audio", dependencies=[Depends(require_csrf)]
)
def update_video_audio(
    dto: VideoAudioUpdate, request: Request, session: DB, principal: PrincipalDep
):
    authorize_admin(session, principal)
    head = connection_head(session, "video", lock=True)
    if head.revision != dto.expected_revision:
        raise MediaServiceError(409)
    # Ensure a valid connection before touching the upstream fallback bindings.
    read_media_connection(session, request.app.state.settings, "video")
    upstream = client(request, session, "video")
    body = dict(expected_version=dto.expected_configuration_revision,
                voice={"adapter": "fake"}, music={"adapter": "fake"})
    # Silence is controlled by frozen task flags. Keep fallbacks available for
    # older audio-enabled tasks that have not taken their generation snapshot.
    upstream.json("PATCH", resource_path("video", "adapter-bindings"), body)
    change = MediaConnectionUpdate(
        expected_revision=dto.expected_revision, video_audio_enabled=dto.enabled
    )
    row = update_media_connection(
        session, request.app.state.settings, "video", change, principal.user_id
    )
    audit_admin(session, principal.user_id, "media_model_config", "video", "更新视频声音设置",
                {"kind": "video", "audio_enabled": dto.enabled, "revision": row.revision})
    session.commit()
    return dict(revision=row.revision, enabled=dto.enabled)


@router.patch("/video/models/{role}", operation_id="admin_save_video_model",
              dependencies=[Depends(require_csrf)])
def update_video_model(role: VideoModelRole, dto: VideoModelUpdate, request: Request,
                       session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    result = save_video_model(
        session, request.app.state.settings, client(request, session, "video"), role, dto
    )
    sync_media_agent(session, request.app.state.settings, "video")
    audit_admin(session, principal.user_id, "media_model_config", "video", "更新视频模型配置",
                {"kind": "video", "role": role, "revision": result["configuration_revision"]})
    session.commit()
    return result


@router.get("/image/models", response_model=ImageModelsView, operation_id="admin_image_models")
def get_image_models(request: Request, session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    settings = request.app.state.settings
    connection = current_connection_view(session, settings, "image")
    upstream = client(request, session, "image") if connection.has_service_key else None
    return read_image_models(session, settings, upstream)


@router.patch(
    "/image/models", response_model=ImageModelsView, operation_id="admin_save_image_models",
    dependencies=[Depends(require_csrf)],
)
def update_image_models(
    dto: ImageModelsUpdate, request: Request, session: DB, principal: PrincipalDep,
):
    authorize_admin(session, principal)
    result = save_image_models(
        session, request.app.state.settings, client(request, session, "image"), dto,
        principal.user_id,
    )
    sync_media_agent(session, request.app.state.settings, "image")
    audit_admin(session, principal.user_id, "media_model_config", "image", "更新图片模型配置",
                {"kind": "image", "revision": result["revision"]})
    session.commit()
    return result


@router.get(
    "/{kind}/connection", response_model=MediaConnectionView, operation_id="admin_media_connection"
)
def get_connection(kind: MediaKind, request: Request, session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    return current_connection_view(session, request.app.state.settings, kind)


@router.patch(
    "/{kind}/connection",
    response_model=MediaConnectionView,
    operation_id="admin_save_media_connection",
    dependencies=[Depends(require_csrf)],
)
def save_connection(
    kind: MediaKind,
    dto: MediaConnectionUpdate,
    request: Request,
    session: DB,
    principal: PrincipalDep,
):
    authorize_admin(session, principal)
    settings = request.app.state.settings
    row = update_media_connection(session, settings, kind, dto, principal.user_id)
    if kind == "image" and row.default_config_id:
        _, raw = client(request, session, kind).json(
            "GET", resource_path(kind, "agent-configs", UUID(row.default_config_id))
        )
        config = project_resource(kind, "agent-configs", raw)
        if (
            config["id"] != row.default_config_id
            or not config["enabled"]
            or not row.image_model
            or row.image_model not in config["image_models"]
        ):
            raise MediaServiceError(422, "请选择已启用的 Agent 方案及其已配置的生图别名。")
    sync_media_agent(session, settings, kind)
    audit_admin(
        session,
        principal.user_id,
        "media_service_connection",
        row.id,
        "更新媒体服务连接",
        {
            "kind": kind,
            "revision": row.revision,
            "key_changed": dto.service_key is not None,
            "management_key_changed": dto.management_key is not None,
        },
    )
    session.commit()
    return connection_view(row)


@router.get("/{kind}/resources/{resource}", operation_id="admin_media_resources")
def list_resources(
    kind: MediaKind,
    resource: str,
    request: Request,
    session: DB,
    principal: PrincipalDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    authorize_admin(session, principal)
    path = resource_path(kind, resource)
    if resource not in SINGLETONS and resource != "adapter-types":
        path += "?" + urlencode({"limit": limit, "offset": offset})
    _, payload = client(request, session, kind).json("GET", path)
    return project_resource(kind, resource, payload, listing=True)


@router.get("/{kind}/resources/{resource}/{config_id}", operation_id="admin_media_resource")
def get_resource(
    kind: MediaKind,
    resource: str,
    config_id: UUID,
    request: Request,
    session: DB,
    principal: PrincipalDep,
):
    authorize_admin(session, principal)
    path = resource_path(kind, resource, config_id)
    _, payload = client(request, session, kind).json("GET", path)
    result = project_resource(kind, resource, payload)
    if str(config_id) != result.get("id", result.get("profile_id")):
        raise MediaServiceError()
    return result


def record_change(session, principal, kind, resource, value):
    audit_admin(
        session,
        principal.user_id,
        "media_model_config",
        value.get("id", value.get("profile_id", resource)),
        "保存媒体配置",
        {
            "kind": kind,
            "resource": resource,
            "version": value.get("version", value.get("configuration_revision")),
        },
    )
    session.commit()
    return value


@router.post(
    "/{kind}/resources/{resource}",
    status_code=201,
    operation_id="admin_create_media_resource",
    dependencies=[Depends(require_csrf)],
)
def create_resource(
    kind: MediaKind,
    resource: str,
    dto: MediaResourceWrite,
    request: Request,
    session: DB,
    principal: PrincipalDep,
):
    authorize_admin(session, principal)
    path = resource_path(kind, resource)
    body = resource_body(kind, resource, dto.config)
    _, payload = client(request, session, kind).json(
        "POST",
        path,
        body,
        idempotency_key=request.headers.get("Idempotency-Key") if kind == "video" else None,
    )
    result = project_resource(kind, resource, payload)
    sync_media_agent(session, request.app.state.settings, kind)
    return record_change(session, principal, kind, resource, result)


@router.patch(
    "/{kind}/resources/{resource}",
    operation_id="admin_update_media_singleton",
    dependencies=[Depends(require_csrf)],
)
def update_singleton(
    kind: MediaKind,
    resource: str,
    dto: MediaResourceWrite,
    request: Request,
    session: DB,
    principal: PrincipalDep,
):
    authorize_admin(session, principal)
    if kind != "video" or resource not in SINGLETONS:
        raise MediaServiceError(404)
    if dto.expected_connection_revision is not None:
        head = connection_head(session, kind, lock=True)
        if head.revision != dto.expected_connection_revision:
            raise MediaServiceError(409, "服务连接已更新，请关闭后重新打开编辑。")
    body = resource_body(kind, resource, dto.config, patch=True)
    _, payload = client(request, session, kind).json("PATCH", resource_path(kind, resource), body)
    result = project_resource(kind, resource, payload)
    sync_media_agent(session, request.app.state.settings, kind)
    return record_change(session, principal, kind, resource, result)


@router.patch(
    "/{kind}/resources/{resource}/{config_id}",
    operation_id="admin_update_media_resource",
    dependencies=[Depends(require_csrf)],
)
def update_resource(
    kind: MediaKind,
    resource: str,
    config_id: UUID,
    dto: MediaResourceWrite,
    request: Request,
    session: DB,
    principal: PrincipalDep,
):
    authorize_admin(session, principal)
    path = resource_path(kind, resource, config_id)
    body = resource_body(kind, resource, dto.config, patch=True)
    _, payload = client(request, session, kind).json("PATCH", path, body)
    result = project_resource(kind, resource, payload)
    if str(config_id) != result.get("id", result.get("profile_id")):
        raise MediaServiceError()
    sync_media_agent(session, request.app.state.settings, kind)
    return record_change(session, principal, kind, resource, result)
