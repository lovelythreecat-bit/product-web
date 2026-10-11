from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from app.common.types import Timestamp


def database_utc(value):
    """MySQL DATETIME fields store UTC without a timezone."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return value


DatabaseTimestamp = Annotated[Timestamp, BeforeValidator(database_utc)]

Reference = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:/-]{1,128}$")]
Action = Literal["resume_original", "confirm_failure", "manual_close", "settle"]


class Data(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class OpenInvestigation(Data):
    owner: UUID
    policy_version: Reference
    evidence: Reference


class Evidence(Data):
    kind: Literal["review", "upstream_failure", "durable_delivery"]
    reference: Reference


class ResolveInvestigation(Data):
    action: Action
    policy_version: Reference
    evidence: Evidence
    reason: Annotated[str, Field(min_length=1, max_length=500, pattern=r"\S")]
    expected_version: Annotated[int, Field(strict=True, ge=1)]


class InvestigationView(Data):
    task_id: UUID
    owner: UUID | None
    policy_version: str
    status: str
    version: int
    deadline_at: DatabaseTimestamp
    user_reason: str | None


class ResolutionReceipt(Data):
    id: UUID
    task_id: UUID
    action: Action
    outcome: str
    after_version: int
    task_version: int


class OwnerView(Data):
    task_id: UUID
    status: str
    deadline_at: DatabaseTimestamp
    user_reason: str | None


class AlertView(Data):
    key: str
    task_id: UUID
    kind: str
    escalation_ref: str
    evidence_ref: str | None
    disposition: str
    created_at: DatabaseTimestamp


class AssignInvestigation(OpenInvestigation):
    expected_version: Annotated[int, Field(strict=True, ge=1)]
    reason: Annotated[str, Field(min_length=1, max_length=500, pattern=r"\S")]
