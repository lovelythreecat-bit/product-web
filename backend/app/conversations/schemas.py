from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field

from app.common.types import DTO, CursorPage, TaskView, Timestamp


class ConversationCreate(DTO):
    title: Annotated[str, Field(min_length=1, max_length=200, pattern=r"\S")]


class ConversationSummary(DTO):
    conversation_id: UUID
    title: str
    created_at: Timestamp


class ProductVersionCreate(DTO):
    product_id: UUID | None = None
    product: dict[str, Any]


class ProductVersionView(DTO):
    product_id: UUID
    version: UUID
    product: dict[str, Any]
    created_at: Timestamp


class MessageView(DTO):
    message_id: UUID
    task_id: UUID | None
    kind: Literal["authored", "final"]
    role: Literal["user", "assistant"]
    content: dict[str, Any]
    created_at: Timestamp


class ConversationView(DTO):
    conversation: ConversationSummary
    tasks: CursorPage[TaskView]
    messages: CursorPage[MessageView]
