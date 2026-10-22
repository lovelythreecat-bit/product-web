"""Cookie authentication; every mutation uses origin and session-bound CSRF checks."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response
from redis import RedisError
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.auth.models import AuthSession
from app.auth.schemas import (
    AuthView,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdate,
    ProfileView,
    RegisterRequest,
)
from app.auth.security import digest, normalize_account
from app.auth.service import AuthService
from app.common.errors import ErrorResponse
from app.common.types import Principal
from app.db import get_session

router = APIRouter(
    prefix="/api/v1",
    responses={status: {"model": ErrorResponse} for status in (401, 403, 409, 429, 503)},
)
DB = Annotated[Session, Depends(get_session)]


def service(request, session):
    return AuthService(session, mode=request.app.state.settings.mode)


def origin_check(request):
    if request.headers.get("origin") not in request.app.state.settings.auth_origins:
        raise HTTPException(403)
    if request.headers.get("x-requested-with") != "platform":
        raise HTTPException(403)


def require_origin_headers(
    request: Request,
    origin: Annotated[
        str | None,
        Header(
            description=(
                "Required exact allowlisted Origin; browsers send this automatically. "
                "Do not set Origin in frontend JavaScript."
            )
        ),
    ] = None,
    requested_with: Annotated[
        str | None,
        Header(
            alias="X-Requested-With",
            description="Required literal platform; omission or mismatch returns 403.",
        ),
    ] = None,
):
    # Optional in Python preserves the existing 403 security semantics on omission.
    origin_check(request)


def limit_auth(request, account):
    client = request.app.state.auth_redis
    if client is None:
        raise HTTPException(503)
    prefix = request.app.state.auth_rate_prefix
    address = request.client.host if request.client else "unknown"
    # No raw account or IP is stored in Redis keys; proxy headers are deliberately ignored.
    script = (
        "local n=redis.call('INCR',KEYS[1]); "
        "if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n"
    )
    try:
        for key, limit in (("ip:" + digest(address), 20), ("account:" + digest(account), 10)):
            if client.eval(script, 1, prefix + key) > limit:
                raise HTTPException(429)
    except RedisError:
        raise HTTPException(503) from None


def set_cookies(response, result):
    response.set_cookie(
        "session",
        result.session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400,
        path="/",
    )
    response.set_cookie(
        "csrf_token",
        result.csrf_token,
        httponly=False,
        secure=True,
        samesite="lax",
        max_age=86400,
        path="/",
    )


def require_active_principal(
    request: Request,
    session: DB,
    cookie: Annotated[
        str | None,
        Cookie(
            alias="session",
            description=(
                "Required Secure HttpOnly session cookie; omission or invalid session returns 401."
            ),
        ),
    ] = None,
):
    return service(request, session).require_active_principal(cookie)


PrincipalDep = Annotated[Principal, Depends(require_active_principal)]


def require_csrf(
    request: Request,
    session: DB,
    principal: PrincipalDep,
    origin_headers: Annotated[None, Depends(require_origin_headers)] = None,
    csrf_header: Annotated[
        str | None,
        Header(
            alias="X-CSRF-Token",
            description=(
                "Required token bound to this session and csrf_token cookie; "
                "omission or mismatch returns 403."
            ),
        ),
    ] = None,
    csrf_cookie: Annotated[
        str | None,
        Cookie(
            alias="csrf_token",
            description="Required session-bound CSRF cookie; omission or mismatch returns 403.",
        ),
    ] = None,
):
    origin_check(request)
    token = request.headers.get("x-csrf-token", "")
    cookie = request.cookies.get("csrf_token", "")
    credential = session.get(AuthSession, str(principal.session_id))
    if (
        credential is None
        or not token
        or len(token) > 128
        or not secrets.compare_digest(token, cookie)
        or not secrets.compare_digest(digest(token), credential.csrf_hash)
    ):
        raise HTTPException(403)


@router.post(
    "/auth/register",
    response_model=AuthView,
    status_code=201,
    responses={200: {"model": AuthView}},
    operation_id="auth_register",
    dependencies=[Depends(require_origin_headers)],
)
def register(dto: RegisterRequest, request: Request, response: Response, session: DB):
    origin_check(request)
    limit_auth(request, normalize_account(dto.account))
    for attempt in range(3):
        try:
            result = service(request, session).register_account(
                dto.account, dto.password.get_secret_value(), dto.request_key
            )
            session.commit()
            break
        except OperationalError as exc:
            session.rollback()
            if attempt == 2 or exc.orig.args[0] not in (1205, 1213):
                raise

    response.status_code = 200 if result.replayed else 201
    set_cookies(response, result)
    return AuthView(profile=result.profile, replayed=result.replayed)


@router.post(
    "/auth/login",
    response_model=AuthView,
    operation_id="auth_login",
    dependencies=[Depends(require_origin_headers)],
)
def login(dto: LoginRequest, request: Request, response: Response, session: DB):
    origin_check(request)
    limit_auth(request, normalize_account(dto.account))
    result = service(request, session).authenticate(dto.account, dto.password.get_secret_value())
    session.commit()
    set_cookies(response, result)
    return AuthView(profile=result.profile, replayed=False)


@router.post(
    "/auth/logout",
    status_code=204,
    operation_id="auth_logout",
    dependencies=[Depends(require_csrf)],
)
def logout(request: Request, session: DB, principal: PrincipalDep):
    service(request, session).revoke_session(principal.session_id)
    session.commit()
    response = Response(status_code=204)
    for name in ("session", "csrf_token"):
        response.delete_cookie(
            name, secure=True, httponly=name == "session", samesite="lax", path="/"
        )
    return response


@router.get("/me", response_model=ProfileView, operation_id="get_profile")
def get_profile(request: Request, session: DB, principal: PrincipalDep):
    return service(request, session).get_profile(principal)


@router.post(
    "/auth/password",
    status_code=204,
    operation_id="auth_change_password",
    responses={400: {"model": ErrorResponse}},
    dependencies=[Depends(require_csrf)],
)
def change_password(
    dto: PasswordChangeRequest, request: Request, session: DB, principal: PrincipalDep
):
    limit_auth(request, str(principal.user_id))
    service(request, session).change_password(
        principal, dto.current_password.get_secret_value(), dto.new_password.get_secret_value()
    )
    session.commit()
    response = Response(status_code=204)
    for name in ("session", "csrf_token"):
        response.delete_cookie(
            name, secure=True, httponly=name == "session", samesite="lax", path="/"
        )
    return response


@router.patch(
    "/me",
    response_model=ProfileView,
    operation_id="update_profile",
    dependencies=[Depends(require_csrf)],
)
def update_profile(dto: ProfileUpdate, request: Request, session: DB, principal: PrincipalDep):
    result = service(request, session).update_profile(principal, dto)
    session.commit()
    return result
