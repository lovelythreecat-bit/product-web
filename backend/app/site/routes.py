"""Site routes: CSRF writes, live admin checks, no-store public copies."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError

from app.auth.routes import DB, PrincipalDep, require_csrf
from app.common.errors import ErrorResponse
from app.site import schemas as s
from app.site import service
from app.storage.local_store import LocalStore

router = APIRouter(
    prefix="/api/v1", responses={n: {"model": ErrorResponse} for n in (401, 403, 404, 409, 422)}
)


@router.get("/site/content", response_model=s.PublicSiteView, operation_id="public_site_content")
def content(request: Request, response: Response, session: DB):
    response.headers["Cache-Control"] = "no-store"
    return s.PublicSiteView(
        content=service.get_public_site_content(session, request.app.state.settings.mode)
    )


@router.get(
    "/admin/site/content", response_model=s.SiteContentView, operation_id="admin_site_content"
)
def admin_content(request: Request, session: DB, principal: PrincipalDep):
    return service.get_admin_site_content(session, principal, request.app.state.settings.mode)


@router.patch(
    "/admin/site/content",
    response_model=s.SiteContentView,
    dependencies=[Depends(require_csrf)],
    operation_id="update_site_content",
)
def update_content(
    dto: s.SiteContentUpdate, request: Request, session: DB, principal: PrincipalDep
):
    session.rollback()
    result = service.update_site_content(session, principal, request.app.state.settings.mode, dto)
    session.commit()
    return result


@router.get("/site/cases", response_model=list[s.PublicCaseView], operation_id="public_site_cases")
def cases(request: Request, response: Response, session: DB):
    response.headers["Cache-Control"] = "no-store"
    return service.public_cases(session, request.app.state.settings.mode)


@router.get(
    "/site/cases/{case_id}/copies/{copy_id}",
    response_class=Response,
    operation_id="public_site_copy",
)
def case_copy(case_id: UUID, copy_id: UUID, request: Request, session: DB):
    data, media = service.read_public_copy(session, request.app.state.settings, case_id, copy_id)
    return Response(
        data,
        media_type=media,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )


@router.get(
    "/admin/site/cases", response_model=list[s.AdminCaseView], operation_id="admin_site_cases"
)
def admin_cases(request: Request, session: DB, principal: PrincipalDep):
    return service.list_admin_cases(session, principal, request.app.state.settings.mode)


@router.post(
    "/admin/site/cases",
    response_model=s.AdminCaseView,
    dependencies=[Depends(require_csrf)],
    operation_id="publish_site_case",
)
async def publish_case(dto: s.CasePublish, request: Request, session: DB, principal: PrincipalDep):
    session.rollback()
    staged = []
    settings = request.app.state.settings
    try:
        result = await service.publish_case(session, principal, settings, dto, staged)
    except Exception as exc:
        session.rollback()
        if staged:
            store = LocalStore(settings.storage_root)
            for item in staged:
                store.discard(item)
        if isinstance(exc, IntegrityError):
            raise HTTPException(409) from None
        raise
    # Ambiguous commit failures retain journals/copies, inaccessible without a published row.
    session.commit()
    if staged:
        store = LocalStore(settings.storage_root)
        for item in staged:
            store.acknowledge(item)
    return result


@router.post(
    "/admin/site/cases/{case_id}/withdraw",
    response_model=s.AdminCaseView,
    dependencies=[Depends(require_csrf)],
    operation_id="withdraw_site_case",
)
def withdraw_case(
    case_id: UUID, dto: s.CaseWithdraw, request: Request, session: DB, principal: PrincipalDep
):
    session.rollback()
    settings = request.app.state.settings
    service.withdraw_case(session, principal, settings.mode, case_id, dto.policy_version)
    session.commit()  # Denial is durable before physical copy cleanup. Repeat to retry cleanup.
    result = service.cleanup_case(session, principal, settings, case_id)
    session.commit()
    return result
