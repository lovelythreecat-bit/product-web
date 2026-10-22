"""Administrative API: live role checks, CSRF mutations, explicit content grants."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.admin import schemas as s
from app.admin.content_access import (
    grant_content_access,
    read_user_content,
    revoke_content_access,
)
from app.admin.download import download_content
from app.admin.models import ContentAccessGrant
from app.admin.permissions import authorize_admin
from app.admin.queries import search_terms
from app.admin.service import (
    admin_credit_grant,
    audit_summary,
    diagnostic,
    ledger_summary,
    list_ledger,
    list_tasks,
    list_users,
    tasks_summary,
    user_account,
    users_summary,
)
from app.admin.statistics import get_statistics
from app.audit.models import AuditEvent
from app.auth.routes import DB, PrincipalDep, require_csrf
from app.catalog.parameters import (
    ParameterConfigUpdate,
    ParameterConfigView,
    read_parameters,
    update_parameters,
)
from app.common.errors import ErrorResponse
from app.common.pagination import numbered_page_rows, page_rows
from app.common.types import CursorPage, NumberedPage, TaskState
from app.ledger.read_schemas import AccountView, LedgerEntryView
from app.ledger.service import read_registration_credit_config, set_registration_credit_config
from app.tasks.models import GenerationTask

router = APIRouter(
    prefix="/api/v1/admin",
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 503)},
)
Limit = Annotated[int, Query(ge=1, le=100)]
ReadReason = Annotated[str, Query(min_length=1, max_length=500, pattern=r"\S")]
Search = Annotated[str | None, Query(max_length=128)]


@router.get(
    "/users/summary", response_model=s.AdminUsersSummary, operation_id="admin_users_summary"
)
def summary_users(session: DB, principal: PrincipalDep):
    return users_summary(session, principal)


@router.get(
    "/ledger/summary", response_model=s.AdminLedgerSummary, operation_id="admin_ledger_summary"
)
def summary_ledger(session: DB, principal: PrincipalDep):
    return ledger_summary(session, principal)


@router.get(
    "/ledger", response_model=NumberedPage[s.AdminLedgerEntryView], operation_id="admin_list_ledger"
)
def platform_ledger(
    session: DB,
    principal: PrincipalDep,
    cursor: UUID | None = None,
    limit: Limit = 20,
    q: Search = None,
    page: Annotated[int | None, Query(ge=1)] = None,
):
    return list_ledger(session, principal, cursor, limit, q, page=page)


@router.get(
    "/tasks/summary", response_model=s.AdminTasksSummary, operation_id="admin_tasks_summary"
)
def summary_tasks(session: DB, principal: PrincipalDep):
    return tasks_summary(session, principal)


@router.get(
    "/audit/summary", response_model=s.AdminAuditSummary, operation_id="admin_audit_summary"
)
def summary_audit(session: DB, principal: PrincipalDep):
    return audit_summary(session, principal)


@router.get("/users", response_model=CursorPage[s.AdminUserView], operation_id="admin_list_users")
def users(
    session: DB,
    principal: PrincipalDep,
    cursor: UUID | None = None,
    limit: Limit = 20,
    status: Literal["active", "disabled"] | None = None,
    q: Search = None,
):
    return list_users(session, principal, cursor, limit, status, q)


@router.get("/users/{id}/account", response_model=AccountView, operation_id="admin_user_account")
def account(id: UUID, session: DB, principal: PrincipalDep):
    return user_account(session, principal, id)


@router.get(
    "/users/{id}/ledger",
    response_model=NumberedPage[LedgerEntryView],
    operation_id="admin_user_ledger",
)
def ledger(
    id: UUID,
    session: DB,
    principal: PrincipalDep,
    cursor: UUID | None = None,
    limit: Limit = 20,
    page: Annotated[int | None, Query(ge=1)] = None,
):
    return user_account(
        session,
        principal,
        id,
        ledger=True,
        cursor=str(cursor) if cursor else None,
        limit=limit,
        page=page,
    )


@router.post(
    "/credit-grants",
    response_model=s.CreditGrantView,
    operation_id="admin_grant_credits",
    dependencies=[Depends(require_csrf)],
)
def credit_grants(dto: s.CreditGrantRequest, session: DB, principal: PrincipalDep):
    session.rollback()
    result = admin_credit_grant(session, principal, dto)
    session.commit()
    return result


@router.get(
    "/registration-credit-config",
    response_model=s.RegistrationConfigView,
    operation_id="admin_get_registration_credit_config",
)
def registration_config(request: Request, session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    return read_registration_credit_config(session, request.app.state.settings.mode)


@router.patch(
    "/registration-credit-config",
    response_model=s.RegistrationConfigView,
    operation_id="admin_update_registration_credit_config",
    dependencies=[Depends(require_csrf)],
)
def update_registration_config(
    dto: s.RegistrationConfigUpdate, request: Request, session: DB, principal: PrincipalDep
):
    session.rollback()
    authorize_admin(session, principal)
    try:
        result = set_registration_credit_config(
            session,
            mode=request.app.state.settings.mode,
            expected_version=str(dto.expected_version) if dto.expected_version else None,
            amount=dto.amount,
            policy_version=dto.policy_version,
            actor=principal,
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409) from None
    return result


@router.get(
    "/tasks", response_model=NumberedPage[s.TaskDiagnosticView], operation_id="admin_list_tasks"
)
def tasks(
    session: DB,
    principal: PrincipalDep,
    cursor: UUID | None = None,
    limit: Limit = 20,
    state: TaskState | None = None,
    user_id: UUID | None = None,
    q: Search = None,
    agent_id: UUID | None = None,
    page: Annotated[int | None, Query(ge=1)] = None,
):
    return list_tasks(session, principal, cursor, limit, state, user_id, q, agent_id, page=page)


@router.get(
    "/tasks/{id}/diagnostics",
    response_model=s.TaskDiagnosticView,
    operation_id="admin_task_diagnostics",
)
def task_diagnostics(id: UUID, session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    task = session.get(GenerationTask, str(id))
    if task is None:
        raise HTTPException(404)
    return diagnostic(session, task)


@router.post(
    "/content-access-grants",
    response_model=s.ContentGrantView,
    status_code=201,
    operation_id="admin_grant_content_access",
    dependencies=[Depends(require_csrf)],
)
def content_grants(
    dto: s.ContentGrantRequest, request: Request, session: DB, principal: PrincipalDep
):
    session.rollback()
    result = grant_content_access(session, request.app.state.settings, principal, dto)
    session.commit()
    return result


@router.get(
    "/content-access-grants",
    response_model=CursorPage[s.ContentGrantView],
    operation_id="admin_list_content_grants",
)
def list_content_grants(
    request: Request,
    session: DB,
    principal: PrincipalDep,
    cursor: UUID | None = None,
    limit: Limit = 20,
):
    authorize_admin(session, principal)
    settings = request.app.state.settings
    rows, next_cursor = page_rows(
        session,
        ContentAccessGrant,
        [
            ContentAccessGrant.mode == settings.mode,
            ContentAccessGrant.test_only == settings.test_only,
            or_(
                ContentAccessGrant.actor_id == str(principal.user_id),
                ContentAccessGrant.approver_id == str(principal.user_id),
            ),
        ],
        str(cursor) if cursor else None,
        limit,
    )
    return CursorPage[s.ContentGrantView](items=rows, next_cursor=next_cursor)


@router.post(
    "/content-access-grants/{id}/revoke",
    response_model=s.ContentGrantView,
    operation_id="admin_revoke_content_grant",
    dependencies=[Depends(require_csrf)],
)
def revoke_grant(
    id: UUID, dto: s.RevokeContentGrant, request: Request, session: DB, principal: PrincipalDep
):
    session.rollback()
    result = revoke_content_access(session, request.app.state.settings, principal, id, dto.reason)
    session.commit()
    return result


@router.get(
    "/content/{resource_type}/{id}",
    response_model=s.AuditedContent,
    operation_id="admin_read_content",
)
def content(
    resource_type: s.ResourceType,
    id: UUID,
    reason: ReadReason,
    request: Request,
    response: Response,
    session: DB,
    principal: PrincipalDep,
):
    result = read_user_content(
        session, request.app.state.settings, principal, resource_type, id, reason
    )
    session.commit()
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.get(
    "/content/{resource_type}/{id}/download",
    response_class=StreamingResponse,
    operation_id="admin_download_content",
    responses={
        200: {
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            }
        },
        206: {
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            }
        },
        416: {"model": ErrorResponse},
    },
)
def download(
    resource_type: Literal["file", "material"],
    id: UUID,
    reason: ReadReason,
    request: Request,
    session: DB,
    principal: PrincipalDep,
    range_header: Annotated[str | None, Header(alias="Range")] = None,
):
    return download_content(request, session, principal, resource_type, id, reason, range_header)


@router.get("/statistics", response_model=s.StatisticsView, operation_id="admin_statistics")
def statistics(session: DB, principal: PrincipalDep):
    return get_statistics(session, principal)


# Only known metadata fields cross the generic audit endpoint. User contents,
# agent snapshots, credentials and arbitrary future fields are not projected.
AUDIT_FIELDS = {
    "text_price",
    "image_price",
    "video_price",
    "previous_version",
    "version",
    "enabled",
    "secret_configured",
    "credits",
    "amount",
    "policy_version",
    "user_id",
    "actor_id",
    "resource_type",
    "resource_id",
    "expires_at",
    "authority_source",
    "grant_id",
    "owner",
    "action",
    "outcome",
    "before_version",
    "after_version",
    "task_version",
    "status",
    "auth_version",
    "file_id",
    "work_id",
    "expected_version",
}


@router.get("/audit", response_model=NumberedPage[s.AuditView], operation_id="admin_list_audit")
def audit(
    session: DB,
    principal: PrincipalDep,
    cursor: UUID | None = None,
    limit: Limit = 20,
    action: Annotated[str | None, Query(max_length=64)] = None,
    actor_id: UUID | None = None,
    object_id: Annotated[str | None, Query(max_length=128)] = None,
    q: Search = None,
    page: Annotated[int | None, Query(ge=1)] = None,
):
    authorize_admin(session, principal)
    predicates = []
    for column, value in (
        (AuditEvent.action, action),
        (AuditEvent.actor_id, actor_id),
        (AuditEvent.object_id, object_id),
    ):
        if value is not None:
            predicates.append(column == str(value))
    predicates += search_terms(q, [AuditEvent.actor_id, AuditEvent.object_id, AuditEvent.reason])
    rows, next_cursor, metadata = numbered_page_rows(
        session, AuditEvent, predicates, str(cursor) if cursor else None, limit, page=page
    )
    return NumberedPage[s.AuditView](
        **metadata,
        items=[
            s.AuditView(
                id=row.id,
                actor_id=row.actor_id,
                action=row.action,
                object_id=row.object_id,
                reason=row.reason,
                created_at=row.created_at,
                changes={
                    key: value
                    for key, value in row.changes.items()
                    if key in AUDIT_FIELDS
                    and (value is None or type(value) in (str, int, bool, float))
                },
            )
            for row in rows
        ],
        next_cursor=next_cursor,
    )


@router.get(
    "/parameter-config",
    response_model=ParameterConfigView,
    operation_id="admin_get_parameter_config",
)
def parameter_config(request: Request, session: DB, principal: PrincipalDep):
    authorize_admin(session, principal)
    return read_parameters(session, request.app.state.settings.mode)


@router.patch(
    "/parameter-config",
    response_model=ParameterConfigView,
    operation_id="admin_update_parameter_config",
    dependencies=[Depends(require_csrf)],
)
def save_parameter_config(
    dto: ParameterConfigUpdate, request: Request, session: DB, principal: PrincipalDep
):
    session.rollback()
    authorize_admin(session, principal)
    result = update_parameters(
        session,
        request.app.state.settings.mode,
        dto,
        principal.user_id,
        settings=request.app.state.settings,
    )
    session.commit()
    return result
