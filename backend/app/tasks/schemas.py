from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.common.types import DTO, InputSnapshot, Quote, TaskView
from app.policies.schemas import Text, Version


class GenerationEstimate(DTO):
    """Server-selected upper estimate for the exact generation contract.

    New submissions key estimates by agent_id with spec_version equal to the agent
    protocol version; historical spec-keyed snapshots remain readable.
    The total is bound to the reviewed D-10 estimation reference. No client amount
    or unconfirmed production fallback can select the reservation size.
    """

    spec_version: Version
    policy_version: Version
    estimation_ref: Text
    total_bytes: Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]


class RegenerationState(DTO):
    root_task_id: UUID
    free_regenerations_used: int = Field(ge=0, le=3)
    free_regenerations_remaining: int = Field(ge=0, le=3)


class RegenerationQuoteRequest(DTO):
    agent_id: UUID
    input: InputSnapshot


class RegenerationQuote(DTO):
    quote: Quote
    credits: int = Field(ge=0)
    eligible: bool
    free_regenerations_used: int = Field(ge=0, le=3)
    free_regenerations_remaining: int = Field(ge=0, le=3)


class TaskDetail(DTO):
    task: TaskView
    conversation_id: UUID
    conversation_display_number: str = Field(
        pattern=r"^H\d{8}-\d{6,19}$", json_schema_extra={"readOnly": True},
    )
    agent_id: UUID
    input: InputSnapshot
    policy_versions: dict[str, str]
    media: dict | None = None
    regeneration: RegenerationState | None = Field(
        default=None, json_schema_extra=lambda schema: schema.pop('default', None),
    )
