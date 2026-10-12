"""Explicit administrative projections; never serialize arbitrary ORM records."""

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field

from app.common.types import DTO, SettlementState, TaskState, Timestamp
from app.investigations.schemas import Data, DatabaseTimestamp

Reason = Annotated[str, Field(min_length=1, max_length=500, pattern=r"\S")]
Amount = Annotated[int, Field(strict=True, ge=0, le=2**63 - 1)]
ResourceType = Literal[
    "message", "work", "file", "material", "conversation", "task", "product_version"
]


class AdminUserView(Data):
    id: UUID
    account_normalized: str
    nickname: str | None
    role: Literal["user", "admin"]
    status: Literal["active", "disabled"]
    auth_version: Annotated[int, Field(ge=0)]
    created_at: DatabaseTimestamp


class CreditGrantRequest(DTO):
    user_id: UUID
    business_key: Annotated[str, Field(min_length=1, max_length=128, pattern=r"\S")]
    amount: Amount
    reason: Reason


class CreditGrantView(Data):
    id: UUID
    user_id: UUID
    actor_id: UUID
    business_key: str
    amount: Amount
    reason: str
    created_at: DatabaseTimestamp


class RegistrationConfigUpdate(DTO):
    expected_version: UUID | None
    amount: Amount
    policy_version: Annotated[str, Field(min_length=1, max_length=128)]
    reason: Reason


class RegistrationConfigView(Data):
    version: UUID
    amount: Amount
    mode: Literal["mock", "staging", "production"]
    test_only: bool
    policy_version: str
    reason: str
    created_at: DatabaseTimestamp


class ContentScope(DTO):
    user_id: UUID
    resource_type: ResourceType
    resource_id: UUID


class ContentGrantRequest(DTO):
    actor_id: UUID
    scope: ContentScope
    reason: Reason
    expires_at: Timestamp


class ContentGrantView(Data):
    id: UUID
    actor_id: UUID
    approver_id: UUID
    user_id: UUID
    resource_type: ResourceType
    resource_id: UUID
    reason: str
    expires_at: DatabaseTimestamp
    created_at: DatabaseTimestamp
    revoked_at: DatabaseTimestamp | None
    revoked_by: UUID | None
    revoke_reason: str | None
    mode: Literal["mock", "staging", "production"]
    test_only: bool
    authority_source: str


class RevokeContentGrant(DTO):
    reason: Reason


class AuditedContent(DTO):
    resource_type: ResourceType
    resource_id: UUID
    user_id: UUID
    grant_id: UUID
    audit_id: UUID
    content: dict[str, Any]


class TaskDiagnosticView(Data):
    id: UUID
    user_id: UUID
    agent_id: UUID
    agent_version: str
    state: TaskState
    state_version: int
    settlement_state: SettlementState
    created_at: DatabaseTimestamp
    elapsed_seconds: float
    diagnostic_code: str | None
    investigation_status: str | None
    investigation_owner: UUID | None
    investigation_deadline: DatabaseTimestamp | None


class StatisticsView(DTO):
    generated_count: int
    succeeded_count: int
    terminal_count: int
    success_rate: float | None
    success_rate_basis: Literal["succeeded / (succeeded + failed + manually_closed)"]
    credits_consumed: int
    signup_credits: int
    admin_granted_credits: int
    payment_revenue_status: Literal["not_supported"]
    supplier_cost_status: Literal["unavailable"]
    supplier_cost: None
    supplier_usage_status: Literal["unavailable"]


class AuditView(Data):
    id: UUID
    actor_id: UUID | None
    action: str
    object_id: str
    reason: str
    changes: dict[str, Any]
    created_at: DatabaseTimestamp
