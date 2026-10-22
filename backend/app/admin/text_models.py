"""Local service settings and a gateway to textAgent-owned model configurations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import ValidationError

from app.admin import text_model_schemas as s
from app.admin.permissions import authorize_admin
from app.agents.model_configs import TextModelClient, TextModelError
from app.agents.service_connection import (
    TextServiceConnectionUpdate,
    TextServiceConnectionView,
    connection_row,
    connection_view,
    read_service_connection,
    update_service_connection,
)
from app.agents.text_runtime import (
    TextDefaultModelUpdate,
    TextDefaultModelView,
    default_view,
    remote_model,
    sync_text_agent,
)
from app.audit.service import audit_admin
from app.auth.routes import DB, PrincipalDep, require_csrf
from app.common.errors import ErrorResponse

router = APIRouter(
    prefix="/api/v1/admin/text-model-configs",
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 429, 503)},
)


service_router = APIRouter(
    prefix="/api/v1/admin/text-service-connection",
    responses={status: {"model": ErrorResponse} for status in (401, 403, 409, 422, 503)},
)

default_router = APIRouter(
    prefix="/api/v1/admin/text-default-model",
    responses={status: {"model": ErrorResponse} for status in (401, 403, 409, 422, 503)},
)


@default_router.get("", response_model=TextDefaultModelView,
                    operation_id="admin_text_default_model")
def get_default_model(request: Request, session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    return default_view(connection_row(session), request.app.state.settings)


@default_router.patch("", response_model=TextDefaultModelView,
                      operation_id="admin_save_text_default_model",
                      dependencies=[Depends(require_csrf)])
def save_default_model(dto: TextDefaultModelUpdate, request: Request,
                       session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    row = connection_row(session, lock=True)
    if (row.revision != dto.expected_connection_revision
            or row.default_revision != dto.expected_revision):
        raise TextModelError(409, public_message="服务连接或默认模型已更新，请刷新后重新选择。")
    model = remote_model(read_service_connection(session, request.app.state.settings),
                         dto.model_config_id)
    sync_text_agent(session, request.app.state.settings, model)
    row.default_model_id = str(model.id)
    row.default_revision += 1
    audit_admin(session, principal.user_id, "text_default_model", model.id, "设置默认文本模型",
                {"revision": row.default_revision})
    session.commit()
    return default_view(row, request.app.state.settings)


@service_router.get("", response_model=TextServiceConnectionView,
                    operation_id="admin_text_service_connection")
def get_connection(session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    return connection_view(connection_row(session))


@service_router.patch("", response_model=TextServiceConnectionView,
                    operation_id="admin_save_text_service_connection",
                    dependencies=[Depends(require_csrf)])
def save_connection(dto: TextServiceConnectionUpdate, request: Request,
                    session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    row = update_service_connection(session, request.app.state.settings, dto, principal.user_id)
    audit_admin(session, principal.user_id, "text_service_connection", row.slot,
                "更新文本服务连接", {"revision": row.revision, "key_changed": dto.service_key is not None})
    session.commit()
    return connection_view(row)


def client(request, session):
    return TextModelClient(read_service_connection(session, request.app.state.settings))


def project(schema, value):
    try:
        return schema.model_validate(value)
    except ValidationError:
        raise TextModelError() from None


@router.get("", response_model=s.TextModelPage, operation_id="admin_text_models")
def list_models(
    request: Request,
    session: DB,
    principal: PrincipalDep,
    cursor: Annotated[str | None, Query(max_length=4096)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    authorize_admin(session, principal)
    return project(
        s.TextModelPage, client(request, session).request("GET", cursor=cursor, limit=limit)
    )


def record_change(session, principal, value):
    audit_admin(
        session,
        principal.user_id,
        "text_model_config",
        value.id,
        "保存文本模型配置",
        {"revision": value.revision},
    )
    session.commit()
    return value


@router.get("/{config_id}", response_model=s.TextModelView, operation_id="admin_text_model")
def get_model(config_id: UUID, request: Request, session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    result = project(s.TextModelView, client(request, session).request("GET", "/" + str(config_id)))
    if result.id != config_id:
        raise TextModelError()
    return result


@router.post(
    "",
    response_model=s.TextModelView,
    status_code=201,
    operation_id="admin_create_text_model",
    dependencies=[Depends(require_csrf)],
)
def create_model(dto: s.TextModelCreate, request: Request, session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    result = project(s.TextModelView, client(request, session).request("POST", config=dto.config))
    return record_change(session, principal, result)


@router.patch(
    "/{config_id}",
    response_model=s.TextModelView,
    operation_id="admin_update_text_model",
    dependencies=[Depends(require_csrf)],
)
def update_model(
    config_id: UUID, dto: s.TextModelUpdate, request: Request, session: DB, principal: PrincipalDep
):
    authorize_admin(session, principal)
    result = project(
        s.TextModelView,
        client(request, session).request(
            "PATCH", "/" + str(config_id), config=dto.config, revision=dto.expected_revision
        ),
    )
    if result.id != config_id:
        raise TextModelError()
    return record_change(session, principal, result)
