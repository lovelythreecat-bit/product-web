from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.auth.routes import DB, PrincipalDep, require_csrf
from app.auth.service import AuthService
from app.common.errors import ErrorResponse
from app.works.lifecycle import LifecycleService
from app.works.lifecycle_schemas import (
    AccountStatusReceipt,
    AccountStatusRequest,
    DeleteReceipt,
    DeleteRequest,
)

router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_csrf)],
    responses={s: {"model": ErrorResponse} for s in (401, 403, 404, 409, 422)},
)


@router.delete("/works/{id}", response_model=DeleteReceipt, operation_id="delete_work")
def delete_work(
    id: UUID, dto: DeleteRequest, request: Request, session: DB, principal: PrincipalDep
):
    result = LifecycleService(session, mode=request.app.state.settings.mode).delete_work(
        principal, id, dto.policy_version
    )
    session.commit()
    return result


@router.delete("/files/{id}", response_model=DeleteReceipt, operation_id="delete_material")
def delete_material(
    id: UUID, dto: DeleteRequest, request: Request, session: DB, principal: PrincipalDep
):
    result = LifecycleService(session, mode=request.app.state.settings.mode).delete_material(
        principal, id, dto.policy_version
    )
    session.commit()
    return result


@router.patch(
    "/admin/users/{id}/status",
    response_model=AccountStatusReceipt,
    operation_id="set_account_status",
)
def set_account_status(
    id: UUID, dto: AccountStatusRequest, request: Request, session: DB, principal: PrincipalDep
):
    result = AuthService(session, mode=request.app.state.settings.mode).set_account_status(
        principal,
        id,
        dto.status,
        dto.policy_version,
        expected_auth_version=dto.expected_auth_version,
    )
    session.commit()
    return result
