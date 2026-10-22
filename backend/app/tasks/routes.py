from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy.exc import OperationalError

from app.auth.routes import DB, PrincipalDep, require_csrf
from app.common.errors import ErrorResponse
from app.common.types import AdmissionResult, CursorPage, SubmitTaskRequest, TaskView
from app.tasks.admission import AdmissionService
from app.tasks.repository import TaskRepository
from app.tasks.schemas import RegenerationQuote, RegenerationQuoteRequest, TaskDetail

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
    # Retry successor identities are server-owned; clients cannot preempt one.
    if key.startswith("failed-retry:"):
        raise HTTPException(422)
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
    task_type: Literal["ordinary"] | None = None,
):
    return TaskRepository(session).list_tasks(
        principal, conversation_id, cursor, limit, task_type=task_type,
    )


@router.get("/{id}", response_model=TaskDetail, operation_id="get_task")
def get_task(id: UUID, session: DB, principal: PrincipalDep):
    return TaskRepository(session).read_task(principal, id)


@router.post("/{id}/regeneration-quote", response_model=RegenerationQuote,
             operation_id="quote_task_regeneration", dependencies=[Depends(require_csrf)])
def quote_task_regeneration(
    id: UUID, dto: RegenerationQuoteRequest, request: Request, session: DB,
    principal: PrincipalDep,
):
    from app.tasks.regeneration import RegenerationService

    return RegenerationService(session, request.app.state.settings).quote(principal, id, dto)


@router.get("/{id}/history", response_model=list[TaskDetail], operation_id="task_history")
def task_history(id: UUID, session: DB, principal: PrincipalDep):
    from app.tasks.regeneration import RegenerationService

    return RegenerationService(session).history(principal, id)


@router.delete("/{id}", status_code=204, operation_id="delete_task_history",
               dependencies=[Depends(require_csrf)])
def delete_task_history(id: UUID, session: DB, principal: PrincipalDep):
    TaskRepository(session).delete_history(principal, id)
    session.commit()
    return Response(status_code=204)


def failed_task_action(operation, id, request, session, principal, key):
    from app.agents.media_execution import validate_command_key
    from app.tasks.failed_actions import FailedTaskActions

    try:
        validate_command_key(key)
    except ValueError:
        raise HTTPException(422) from None
    if operation == "retry":
        from app.tasks.stopped_image_retry import prepare_stopped_image_retry

        prepare_stopped_image_retry(session, principal, id, request.app.state.settings)
    for attempt in range(3):
        try:
            service = FailedTaskActions(session, request.app.state.settings)
            result = getattr(service, operation)(principal, id)
        except OperationalError as exc:
            session.rollback()
            if attempt == 2 or exc.orig.args[0] not in (1205, 1213):
                raise
            continue
        session.commit()
        return result


@router.post("/{id}/retry", response_model=AdmissionResult, operation_id="retry_failed_task",
             dependencies=[Depends(require_csrf)])
def retry_failed_task(
    id: UUID, request: Request, session: DB, principal: PrincipalDep,
    key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
):
    return failed_task_action("retry", id, request, session, principal, key)


@router.post("/{id}/release", response_model=TaskView, operation_id="release_failed_task",
             dependencies=[Depends(require_csrf)])
def release_failed_task(
    id: UUID, request: Request, session: DB, principal: PrincipalDep,
    key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
):
    return failed_task_action("release", id, request, session, principal, key)
