"""Authenticated public catalog and DB-authorized administration; no credential output."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.auth.routes import DB, PrincipalDep, require_csrf
from app.catalog import schemas as s
from app.catalog.service import CatalogService
from app.common.errors import ErrorResponse
from app.common.types import Quote

router = APIRouter(
    prefix="/api/v1",
    responses={status: {"model": ErrorResponse} for status in (401, 403, 409, 422)},
)


def service(request, session):
    return CatalogService(session, mode=request.app.state.settings.mode)


@router.get("/agents", response_model=list[s.AgentVersion], operation_id="list_agents")
def agents(request: Request, session: DB, principal: PrincipalDep):
    return service(request, session).list_agents()


@router.get(
    "/agents/{agent_id}/specs", response_model=list[s.SpecVersion], operation_id="list_agent_specs"
)
def specs(agent_id: UUID, request: Request, session: DB, principal: PrincipalDep):
    return service(request, session).list_specs(agent_id)


@router.post(
    "/quotes",
    response_model=Quote,
    operation_id="quote_generation",
    dependencies=[Depends(require_csrf)],
)
def quote(dto: s.QuoteRequest, request: Request, session: DB, principal: PrincipalDep):
    return service(request, session).quote_generation(principal, dto.input, dto.spec_id)


@router.get("/admin/agents", response_model=list[s.AgentVersion], operation_id="admin_agents")
def admin_agents(request: Request, session: DB, principal: PrincipalDep):
    catalog = service(request, session)
    catalog._principal(principal, admin=True)
    return catalog.list_agents(admin=True)


@router.get("/admin/specs", response_model=list[s.SpecVersion], operation_id="admin_specs")
def admin_specs(request: Request, session: DB, principal: PrincipalDep):
    catalog = service(request, session)
    catalog._principal(principal, admin=True)
    return catalog.list_specs(admin=True)


@router.get("/admin/prices", response_model=list[s.PriceVersion], operation_id="admin_prices")
def admin_prices(request: Request, session: DB, principal: PrincipalDep):
    catalog = service(request, session)
    catalog._principal(principal, admin=True)
    return catalog.list_prices()


@router.post(
    "/admin/agents",
    response_model=s.AgentVersion,
    status_code=201,
    operation_id="publish_agent",
    dependencies=[Depends(require_csrf)],
)
def publish_agent(dto: s.AgentDraft, request: Request, session: DB, principal: PrincipalDep):
    result = service(request, session).publish_agent_version(principal, dto)
    session.commit()
    return result


@router.post(
    "/admin/specs",
    response_model=s.SpecVersion,
    status_code=201,
    operation_id="publish_spec",
    dependencies=[Depends(require_csrf)],
)
def publish_spec(dto: s.SpecDraft, request: Request, session: DB, principal: PrincipalDep):
    result = service(request, session).publish_spec_version(principal, dto)
    session.commit()
    return result


@router.post(
    "/admin/prices",
    response_model=s.PriceVersion,
    status_code=201,
    operation_id="publish_price",
    dependencies=[Depends(require_csrf)],
)
def publish_price(dto: s.PriceDraft, request: Request, session: DB, principal: PrincipalDep):
    result = service(request, session).set_price_version(principal, dto)
    session.commit()
    return result
