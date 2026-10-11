from typing import Annotated

from fastapi import APIRouter, Query

from app.auth.routes import DB, PrincipalDep
from app.common.errors import ErrorResponse
from app.common.types import CursorPage
from app.ledger.read_schemas import AccountView, LedgerEntryView
from app.ledger.reads import AccountReads

router = APIRouter(
    prefix="/api/v1/account",
    responses={status: {"model": ErrorResponse} for status in (401, 404, 422)},
)


@router.get("", response_model=AccountView, operation_id="get_account")
def get_account(session: DB, principal: PrincipalDep):
    return AccountReads(session).account(principal)


@router.get("/ledger", response_model=CursorPage[LedgerEntryView], operation_id="list_ledger")
def list_ledger(
    session: DB,
    principal: PrincipalDep,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return AccountReads(session).ledger(principal, cursor, limit)
