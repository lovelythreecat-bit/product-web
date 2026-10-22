"""Explicit administrative projections; never serialize arbitrary ORM records."""

from datetime import date as CalendarDate
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field

from app.common.types import DTO, ConfigurationChange, SettlementState, TaskState, Timestamp
from app.investigations.schemas import Data, DatabaseTimestamp
from app.ledger.read_schemas import LedgerEntryView

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
    shop_name: str | None = None
    category: str | None = None
    email: str | None = None
    phone: str | None = None
    last_login_at: DatabaseTimestamp | None = None
    task_count: int = 0
    available: int = 0
    frozen: int = 0
    consumed: int = 0


class AdminUsersSummary(DTO):
    total: int
    active: int
    disabled: int
    admin_count: int
    available: int
    frozen: int
    consumed: int
    credited_total: int


class AdminLedgerEntryView(LedgerEntryView):
    user_id: UUID
    account: str
    operator: UUID | None = None


class AdminLedgerSummary(DTO):
    available: int
    frozen: int
    consumed: int
    credited_total: int
    ledger_count: int


class AdminTasksSummary(DTO):
    total: int
    investigating: int
    save_recovery: int
    frozen_credits: int


class AdminAuditSummary(DTO):
    total: int
    action_counts: dict[str, int]


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


class RegistrationConfigUpdate(ConfigurationChange):
    expected_version: UUID | None
    amount: Amount
    policy_version: Annotated[str, Field(min_length=1, max_length=128)]


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


class TaskTimelineEvent(Data):
    state_version: int
    from_state: TaskState | None
    to_state: TaskState
    created_at: DatabaseTimestamp


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
    conversation_id: UUID | None = None
    account: str | None = None
    fixed_credits: int | None = None
    spec_version: str | None = None
    price_version: str | None = None
    external_submission_id: str | None = None
    upstream_id: str | None = None
    updated_at: DatabaseTimestamp | None = None
    work_ids: list[UUID] = Field(default_factory=list)
    timeline: list[TaskTimelineEvent] = Field(default_factory=list)


class AgentUsageView(DTO):
    agent_id: UUID
    task_count: int
    succeeded_count: int
    failed_count: int
    unsettled_count: int
    credits_consumed: int
    terminal_count: int
    manually_closed_count: int
    success_rate: float | None
    credits_frozen: int
    credits_released: int


class DailyUsageView(DTO):
    date: CalendarDate
    task_count: int
    credits_consumed: int
    registered_count: int = 0
    active_user_count: int = 0


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
    by_agent: list[AgentUsageView] = Field(default_factory=list)
    state_counts: dict[str, int] = Field(default_factory=dict)
    unsettled_count: int = 0
    credits_frozen: int
    credits_released: int
    daily_trend: list[DailyUsageView]
    trend_days: int
    trend_timezone: Literal["UTC"]
    total_users: int = 0
    registered_today: int = 0
    registered_in_trend: int = 0
    active_today: int = 0
    active_in_trend: int = 0
    active_user_basis: Literal["generation_task_created"] = "generation_task_created"


class AuditView(Data):
    id: UUID
    actor_id: UUID | None
    action: str
    object_id: str
    reason: str
    changes: dict[str, Any]
    created_at: DatabaseTimestamp
