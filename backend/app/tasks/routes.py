from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.exc import OperationalError

from app.auth.routes import DB, PrincipalDep, require_csrf
from app.common.errors import ErrorResponse
from app.common.types import AdmissionResult, CursorPage, SubmitTaskRequest, TaskView
from app.tasks.admission import AdmissionService
from app.tasks.repository import TaskRepository
from app.tasks.schemas import TaskDetail

router = APIRouter(
    prefix="/api/v1/tasks",
    responses={s: {"model": ErrorResponse} for s in (401, 402, 403, 404, 409, 429)},
)


@router.post(
    "",
    response_model=AdmissionResult,
    status_code=201,
    responses={200: {"model": AdmissionResult}},
    operation_id="admit_task",
    dependencies=[Depends(require_csrf)],
)
def admit_task(
    dto: SubmitTaskRequest,
    request: Request,
    response: Response,
    session: DB,
    principal: PrincipalDep,
    key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
):
    for attempt in range(3):
        try:
            result = AdmissionService(session, request.app.state.settings).admit_task(
                principal, key, dto
            )
        except OperationalError as exc:
            session.rollback()
            if attempt == 2 or exc.orig.args[0] not in (1205, 1213):
                raise
            continue
        # Never retry an ambiguous commit. The client may safely replay its key.
        session.commit()
        response.status_code = 200 if result.replayed else 201
        return result


@router.get("", response_model=CursorPage[TaskView], operation_id="list_tasks")
def list_tasks(
    session: DB,
    principal: PrincipalDep,
    conversation_id: UUID | None = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return TaskRepository(session).list_tasks(principal, conversation_id, cursor, limit)


@router.get("/{id}", response_model=TaskDetail, operation_id="get_task")
def get_task(id: UUID, session: DB, principal: PrincipalDep):
    return TaskRepository(session).read_task(principal, id)
