from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.common.types import DTO, CursorPage, TaskView, Timestamp


class ConversationCreate(DTO):
    title: Annotated[str, Field(min_length=1, max_length=200, pattern=r"\S")]


class ConversationSummary(DTO):
    conversation_id: UUID
    display_number: str = Field(pattern=r"^H\d{8}-\d{6,19}$", json_schema_extra={"readOnly": True})
    title: str
    created_at: Timestamp


class ProductVersionCreate(DTO):
    product_id: UUID | None = None
    product: dict[str, Any] = Field(json_schema_extra={
        "properties": {"product_type": {"type": "string", "enum": [
            "clothing", "shoes_bags", "beauty", "food", "digital", "home",
            "appliances", "sports", "baby", "other",
        ]}},
    })

    @field_validator("product")
    @classmethod
    def valid_product_type(cls, value):
        if "product_type" in value and value["product_type"] not in (
            "clothing", "shoes_bags", "beauty", "food", "digital", "home",
            "appliances", "sports", "baby", "other",
        ):
            raise ValueError("Choose a supported product type")
        return value


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
