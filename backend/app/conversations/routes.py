from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.routes import DB, PrincipalDep, require_csrf
from app.common.errors import ErrorResponse
from app.common.types import CursorPage
from app.conversations.schemas import (
    ConversationCreate,
    ConversationSummary,
    ConversationView,
    ProductVersionCreate,
    ProductVersionView,
)
from app.conversations.service import ConversationService

router = APIRouter(
    prefix="/api/v1", responses={s: {"model": ErrorResponse} for s in (401, 403, 404, 409)}
)


@router.post(
    "/conversations",
    response_model=ConversationSummary,
    status_code=201,
    operation_id="create_conversation",
    dependencies=[Depends(require_csrf)],
)
def create_conversation(dto: ConversationCreate, session: DB, principal: PrincipalDep):
    result = ConversationService(session).create_conversation(principal, dto.title)
    session.commit()
    return result


@router.get(
    "/conversations",
    response_model=CursorPage[ConversationSummary],
    operation_id="list_conversations",
)
def list_conversations(
    session: DB,
    principal: PrincipalDep,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return ConversationService(session).list_conversations(principal, cursor, limit)


@router.get("/conversations/{id}", response_model=ConversationView, operation_id="get_conversation")
def get_conversation(
    id: UUID,
    session: DB,
    principal: PrincipalDep,
    task_cursor: str | None = None,
    message_cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return ConversationService(session).read_conversation(
        principal, id, task_cursor=task_cursor, message_cursor=message_cursor, limit=limit
    )


@router.post(
    "/products/versions",
    response_model=ProductVersionView,
    status_code=201,
    operation_id="create_product_version",
    dependencies=[Depends(require_csrf)],
)
def create_product_version(dto: ProductVersionCreate, session: DB, principal: PrincipalDep):
    result = ConversationService(session).create_product_version(principal, dto)
    session.commit()
    return result


@router.get(
    "/products/versions/{version}",
    response_model=ProductVersionView,
    operation_id="get_product_version",
)
def get_product_version(version: UUID, session: DB, principal: PrincipalDep):
    return ConversationService(session).read_product_version(principal, version)
