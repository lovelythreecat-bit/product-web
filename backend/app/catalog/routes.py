"""Authenticated public catalog and DB-authorized administration; no credential output."""

from fastapi import APIRouter, Depends, Request

from app.agents.video_options import VideoOptionsView, read_video_options
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


@router.get("/video-options", response_model=VideoOptionsView, operation_id="video_options")
def video_options(request: Request, session: DB, principal: PrincipalDep):
    service(request, session)._principal(principal)
    return read_video_options(session, request.app.state.settings)


@router.post(
    "/quotes",
    response_model=Quote,
    operation_id="quote_generation",
    dependencies=[Depends(require_csrf)],
)
def quote(dto: s.QuoteRequest, request: Request, session: DB, principal: PrincipalDep):
    return service(request, session).quote_agent(principal, dto.input, dto.agent_id)


@router.get("/admin/agents", response_model=list[s.AgentVersion], operation_id="admin_agents")
def admin_agents(request: Request, session: DB, principal: PrincipalDep):
    catalog = service(request, session)
    catalog._principal(principal, admin=True)
    return catalog.list_agents(admin=True)


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
