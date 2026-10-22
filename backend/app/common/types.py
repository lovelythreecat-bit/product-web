"""Platform wire contracts; agent protocols and policies remain separate."""

from enum import StrEnum
from typing import Annotated, Any, Generic, TypeVar
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]
Timestamp = AwareDatetime
MAX_REFERENCE_IMAGES = 4


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConfigurationChange(DTO):
    """Change reasons were removed; tolerate and discard the legacy input only."""

    @model_validator(mode="before")
    @classmethod
    def discard_legacy_reason(cls, value):
        if isinstance(value, dict) and "reason" in value:
            return {key: item for key, item in value.items() if key != "reason"}
        return value


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class TaskState(StrEnum):
    SUBMITTED = "SUBMITTED"
    QUEUED = "QUEUED"
    SUBMITTING = "SUBMITTING"
    RUNNING = "RUNNING"
    INVESTIGATING = "INVESTIGATING"
    SAVING = "SAVING"
    SAVE_RECOVERY = "SAVE_RECOVERY"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    MANUALLY_CLOSED = "MANUALLY_CLOSED"


class SettlementState(StrEnum):
    FROZEN = "FROZEN"
    CONSUMED = "CONSUMED"
    RELEASED = "RELEASED"


class Principal(DTO):
    user_id: UUID
    role: UserRole
    session_id: UUID
    auth_version: NonNegativeInt


class FileVersionRef(DTO):
    file_id: UUID
    version: str


class InputSnapshot(DTO):
    product_version: str
    product: dict[str, Any]
    instruction: str
    material_versions: list[FileVersionRef]
    parameters: dict[str, Any]


class Quote(DTO):
    spec_id: UUID
    spec_version: str
    price_version: str
    agent_version: str
    policy_versions: dict[str, str]
    credits: NonNegativeInt
    input_digest: str


class RegenerationConfirmation(DTO):
    source_task_id: UUID
    expected_credits: NonNegativeInt
    expected_used: Annotated[int, Field(strict=True, ge=0, le=3)]


class SubmitTaskRequest(DTO):
    conversation_id: UUID
    agent_id: UUID
    input: InputSnapshot
    confirmed_quote: Quote
    regeneration: RegenerationConfirmation | None = Field(
        default=None, json_schema_extra=lambda schema: schema.pop('default', None),
    )


class TaskView(DTO):
    task_id: UUID
    display_number: str = Field(pattern=r"^T\d{8}-\d{6,19}$", json_schema_extra={"readOnly": True})
    state: TaskState
    state_version: PositiveInt
    settlement_state: SettlementState
    quote: Quote
    work_ids: list[UUID]
    investigation_reason: str | None
    created_at: Timestamp
    updated_at: Timestamp


class AdmissionResult(DTO):
    task: TaskView
    replayed: bool


class PageQuery(DTO):
    cursor: str | None = None
    limit: Annotated[int, Field(strict=True, ge=1, le=100)] = 20


T = TypeVar("T")


class CursorPage(DTO, Generic[T]):
    items: list[T]
    next_cursor: str | None


class NumberedPage(CursorPage[T], Generic[T]):
    total: NonNegativeInt
    page: PositiveInt | None = None
    page_size: PositiveInt
