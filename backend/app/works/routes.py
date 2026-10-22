from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.auth.routes import DB, PrincipalDep
from app.common.errors import ErrorResponse
from app.works.schemas import WorkDetail, WorkKind, WorkPage
from app.works.service import WorkService

router = APIRouter(
    prefix="/api/v1/works",
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 422)},
)


@router.get("", response_model=WorkPage, operation_id="list_works")
def list_works(
    session: DB,
    principal: PrincipalDep,
    kind: WorkKind | None = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(max_length=120)] = None,
    page: Annotated[int | None, Query(ge=1)] = None,
):
    return WorkService(session).list_works(principal, kind, cursor, limit, q=q, page=page)


@router.get("/{id}", response_model=WorkDetail, operation_id="get_work")
def get_work(id: UUID, session: DB, principal: PrincipalDep):
    return WorkService(session).read_work(principal, id)
