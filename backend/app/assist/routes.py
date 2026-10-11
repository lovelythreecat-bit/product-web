"""Authenticated draft preparation. Rate limiting is abuse control, not an allowance."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from redis import RedisError

from app.assist.schemas import AssistProposal, AssistRequest
from app.assist.service import AssistService
from app.auth.routes import DB, PrincipalDep, require_csrf
from app.auth.security import digest
from app.common.errors import ErrorResponse

router = APIRouter(
    prefix="/api/v1",
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 429, 503, 504)},
)


def limit_assist(request, principal):
    client = request.app.state.auth_redis
    if client is None:
        raise HTTPException(503)
    key = request.app.state.auth_rate_prefix + "assist:" + digest(str(principal.user_id))
    script = (
        "local n=redis.call('INCR',KEYS[1]); "
        "if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n"
    )
    try:
        if client.eval(script, 1, key) > request.app.state.settings.assist_rate_limit:
            raise HTTPException(429)
    except RedisError:
        raise HTTPException(503) from None


@router.post(
    "/assist/prompts",
    response_model=AssistProposal,
    operation_id="prepare_prompt",
    dependencies=[Depends(require_csrf)],
)
def prepare_prompt(
    dto: AssistRequest,
    request: Request,
    session: DB,
    principal: PrincipalDep,
    key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=128,
            pattern=r"^[!-~]+$",
            description=(
                "request_key is carried only in this required Idempotency-Key header. "
                "Reuse the key for the same draft request to replay its completed result; "
                "reusing it with different input returns 409."
            ),
        ),
    ],
):
    """Prepare a draft; request_key is the required Idempotency-Key header, not a body field."""
    settings = request.app.state.settings
    result = AssistService(session, settings).prepare_prompt(
        principal,
        dto,
        settings.assist_policy_version,
        key=key,
        before_provider=lambda: limit_assist(request, principal),
    )

    session.commit()
    return result
