from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import sessionmaker

from app.agents.registry import AgentRegistry
from app.agents.upstream import UpstreamService
from app.auth.routes import DB, PrincipalDep, require_csrf
from app.catalog.service import CatalogService
from app.common.errors import ErrorResponse
from app.common.types import CursorPage
from app.investigations.models import Investigation, InvestigationAlert
from app.investigations.schemas import (
    AlertView,
    AssignInvestigation,
    InvestigationView,
    OpenInvestigation,
    OwnerView,
    ResolutionReceipt,
    ResolveInvestigation,
)
from app.investigations.service import InvestigationService
from app.tasks.models import GenerationTask

router = APIRouter(
    prefix="/api/v1", responses={s: {"model": ErrorResponse} for s in (401, 403, 404, 409)}
)


def service(request):
    settings = request.app.state.settings
    factory = sessionmaker(request.app.state.engine, expire_on_commit=False)
    upstream = UpstreamService(
        factory, AgentRegistry(mode=settings.mode, test_only=settings.test_only)
    )
    return InvestigationService(factory, upstream=upstream, mode=settings.mode)


@router.post(
    "/admin/tasks/{id}/investigations",
    response_model=InvestigationView,
    status_code=201,
    operation_id="open_investigation",
    dependencies=[Depends(require_csrf)],
)
def open_investigation(
    id: UUID, dto: OpenInvestigation, request: Request, session: DB, principal: PrincipalDep
):
    session.rollback()  # Release dependency authentication locks; recheck in sorted lock order.
    result = service(request).open_investigation(
        session, principal, id, dto.owner, dto.policy_version, dto.evidence
    )
    session.commit()
    return result


@router.post(
    "/admin/tasks/{id}/resolutions",
    response_model=ResolutionReceipt,
    operation_id="resolve_investigation",
    dependencies=[Depends(require_csrf)],
)
def resolve_investigation(
    id: UUID, dto: ResolveInvestigation, request: Request, session: DB, principal: PrincipalDep
):
    task_id = id
    session.rollback()  # Mutation reauthenticates the same live session under sorted user locks.
    svc = service(request)
    if dto.action != "settle":
        result = svc.resolve_investigation(session, principal, task_id, dto)
        session.commit()
        return result
    from app.results.persistence import ResultPersistence
    from app.results.publisher import ResultPublisher
    from app.storage.local_store import LocalStore
    from app.tasks.state_machine import TransitionError

    svc.preflight_settlement(session, principal, task_id, dto)
    session.rollback()
    settings = request.app.state.settings
    if not settings.storage_persistent or settings.storage_root is None:
        raise TransitionError("PUBLICATION_REQUIRED")
    publisher = ResultPublisher(
        ResultPersistence(svc.factory, svc.upstream, LocalStore(settings.storage_root))
    )
    lease = publisher.leases.claim_task(str(task_id), "investigation:publication")
    if lease is None:
        raise HTTPException(409)
    try:
        prepared = publisher.prepare(str(task_id), lease=lease)
        if prepared is None:
            raise TransitionError("PUBLICATION_REQUIRED")
        result = svc.resolve_investigation(
            session, principal, task_id, dto, publisher=publisher, prepared=prepared
        )
        session.commit()
        return result
    finally:
        session.rollback()
        publisher.leases.release(lease)


@router.post(
    "/admin/investigations/{task_id}/assign",
    response_model=InvestigationView,
    operation_id="assign_investigation",
    dependencies=[Depends(require_csrf)],
)
def assign(
    task_id: UUID, dto: AssignInvestigation, request: Request, session: DB, principal: PrincipalDep
):
    session.rollback()
    result = service(request).assign(session, principal, task_id, dto)
    session.commit()
    return result


@router.get(
    "/admin/investigations",
    response_model=CursorPage[InvestigationView],
    operation_id="list_investigations",
)
def list_investigations(
    session: DB,
    principal: PrincipalDep,
    cursor: UUID | None = None,
    owner: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    CatalogService(session)._principal(principal, admin=True)
    query = select(Investigation).where(Investigation.status != "resolved")
    if owner:
        query = query.where(Investigation.owner == str(owner))
    if cursor:
        anchor = session.scalar(query.where(Investigation.task_id == str(cursor)))
        if anchor is None:
            raise HTTPException(422)
        query = query.where(
            or_(
                Investigation.created_at < anchor.created_at,
                and_(
                    Investigation.created_at == anchor.created_at,
                    Investigation.task_id < anchor.task_id,
                ),
            )
        )
    rows = session.scalars(
        query.order_by(Investigation.created_at.desc(), Investigation.task_id.desc()).limit(
            limit + 1
        )
    ).all()
    return dict(
        items=rows[:limit], next_cursor=rows[limit - 1].task_id if len(rows) > limit else None
    )


@router.get(
    "/admin/investigations/{task_id}",
    response_model=InvestigationView,
    operation_id="get_investigation",
)
def get_investigation(task_id: UUID, session: DB, principal: PrincipalDep):
    CatalogService(session)._principal(principal, admin=True)
    result = session.get(Investigation, str(task_id))
    if result is None:
        raise HTTPException(404)
    return result


@router.get(
    "/admin/investigation-alerts",
    response_model=CursorPage[AlertView],
    operation_id="list_investigation_alerts",
)
def list_alerts(
    session: DB,
    principal: PrincipalDep,
    cursor: Annotated[str | None, Query(max_length=180)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    CatalogService(session)._principal(principal, admin=True)
    query = select(InvestigationAlert)
    if cursor:
        anchor = session.get(InvestigationAlert, cursor)
        if anchor is None:
            raise HTTPException(422)
        query = query.where(
            or_(
                InvestigationAlert.created_at < anchor.created_at,
                and_(
                    InvestigationAlert.created_at == anchor.created_at,
                    InvestigationAlert.key < anchor.key,
                ),
            )
        )
    rows = session.scalars(
        query.order_by(InvestigationAlert.created_at.desc(), InvestigationAlert.key.desc()).limit(
            limit + 1
        )
    ).all()
    return dict(items=rows[:limit], next_cursor=rows[limit - 1].key if len(rows) > limit else None)


@router.get(
    "/tasks/{task_id}/investigation", response_model=OwnerView, operation_id="get_own_investigation"
)
def get_own_investigation(task_id: UUID, session: DB, principal: PrincipalDep):
    CatalogService(session)._principal(principal)
    task = session.get(GenerationTask, str(task_id))
    if task is None or task.user_id != str(principal.user_id):
        raise HTTPException(404)
    result = session.get(Investigation, task.id)
    if result is None:
        raise HTTPException(404)
    return result
