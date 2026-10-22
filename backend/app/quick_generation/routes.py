from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.auth.routes import DB, PrincipalDep, require_csrf
from app.quick_generation.schemas import (
    QuickAdvance,
    QuickCreate,
    QuickPrepare,
    QuickSave,
    QuickSummary,
    QuickView,
)
from app.quick_generation.service import QuickGenerationService

router = APIRouter(prefix="/api/v1/quick-generation", tags=["quick-generation"])


def service(session, request):
    return QuickGenerationService(session, request.app.state.settings)


@router.get("", response_model=list[QuickSummary], operation_id="list_quick_generation")
def list_runs(session: DB, principal: PrincipalDep, request: Request):
    return service(session, request).list(principal)


@router.post("", response_model=QuickView, dependencies=[Depends(require_csrf)],
             operation_id="create_quick_generation")
def create(dto: QuickCreate, session: DB, principal: PrincipalDep, request: Request):
    svc = service(session, request)
    row = svc.create(principal, dto.run_id)
    result = svc.view(principal, row)
    session.commit()
    return result


@router.get("/{id}", response_model=QuickView, operation_id="get_quick_generation")
def read(id: UUID, session: DB, principal: PrincipalDep, request: Request):
    svc = service(session, request)
    return svc.view(principal, svc.owned(principal, id))


@router.patch("/{id}", response_model=QuickView, dependencies=[Depends(require_csrf)],
              operation_id="save_quick_generation")
def save(id: UUID, dto: QuickSave, session: DB, principal: PrincipalDep, request: Request):
    svc = service(session, request)
    row = svc.owned(principal, id, write=True)
    svc.save(principal, row, dto)
    result = svc.view(principal, row)
    session.commit()
    return result


@router.post("/{id}/prepare", response_model=QuickView, dependencies=[Depends(require_csrf)],
             operation_id="prepare_quick_generation")
def prepare(id: UUID, dto: QuickPrepare, session: DB, principal: PrincipalDep, request: Request):
    svc = service(session, request)
    row = svc.owned(principal, id, write=True)
    svc.prepare(principal, row, dto)
    result = svc.view(principal, row)
    session.commit()
    return result


@router.post("/{id}/batches/{batch_id}/submit", response_model=QuickView,
             dependencies=[Depends(require_csrf)], operation_id="submit_quick_generation")
def submit(id: UUID, batch_id: UUID, session: DB, principal: PrincipalDep, request: Request):
    svc = service(session, request)
    row = svc.owned(principal, id, write=True)
    svc.submit(principal, row, batch_id)
    result = svc.view(principal, row)
    session.commit()
    return result


@router.post("/{id}/batches/{batch_id}/cancel", response_model=QuickView,
             dependencies=[Depends(require_csrf)], operation_id="cancel_quick_generation_batch")
def cancel_batch(id: UUID, batch_id: UUID, session: DB, principal: PrincipalDep, request: Request):
    svc = service(session, request)
    row = svc.owned(principal, id, write=True)
    svc.cancel_batch(row, batch_id)
    result = svc.view(principal, row)
    session.commit()
    return result


@router.post("/{id}/advance", response_model=QuickView, dependencies=[Depends(require_csrf)],
             operation_id="advance_quick_generation")
def advance(id: UUID, dto: QuickAdvance, session: DB, principal: PrincipalDep, request: Request):
    svc = service(session, request)
    row = svc.owned(principal, id, write=True)
    svc.advance(row, dto)
    result = svc.view(principal, row)
    session.commit()
    return result
