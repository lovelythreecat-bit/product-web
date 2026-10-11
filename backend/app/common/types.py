"""Platform wire contracts; agent protocols and policies remain separate."""

from enum import StrEnum
from typing import Annotated, Any, Generic, TypeVar
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]
Timestamp = AwareDatetime


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


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


class SubmitTaskRequest(DTO):
    conversation_id: UUID
    agent_id: UUID
    input: InputSnapshot
    confirmed_quote: Quote


class TaskView(DTO):
    task_id: UUID
    state: TaskState
    state_version: PositiveInt
    settlement_state: SettlementState
    quote: Quote
    work_ids: list[UUID]
    investigation_reason: str | None


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
