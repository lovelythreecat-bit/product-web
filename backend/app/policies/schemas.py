"""Versioned policy snapshots and feature-specific confirmed content requirements.

References identify reviewed attachments, not secrets. Null/unresolved sections may
remain in a draft or partially confirmed decision, but never satisfy their feature.
"""

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.common.types import NonNegativeInt, PositiveInt

Mode = Literal["mock", "staging", "production"]
Text = Annotated[str, Field(strict=True, min_length=1, max_length=1024, pattern=r"\S")]
Version = Annotated[str, Field(strict=True, min_length=1, max_length=128, pattern=r"^[\w.-]+$")]
DecisionId = Annotated[str, Field(pattern=r"^D-(0[1-9]|1[0-2])$")]


class PolicyData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class DecisionVersion(PolicyData):
    decision_id: DecisionId
    version: Version
    mode: Mode
    test_only: bool = Field(strict=True)
    status: Literal["draft", "confirmed"] = "draft"
    payload: dict[str, Any]
    confirmed_by: UUID | None = None
    confirmed_at: AwareDatetime | None = None
    evidence_refs: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def validate_provenance(self):
        if self.test_only != (self.mode == "mock"):
            raise ValueError("TEST_ONLY is required in mock and forbidden in real environments")
        has_confirmation = self.confirmed_by is not None and self.confirmed_at is not None
        if self.status == "confirmed" and (not has_confirmation or not self.evidence_refs):
            raise ValueError("Confirmation requires a verified person, timestamp and evidence")
        if self.status == "draft" and (
            self.confirmed_by is not None or self.confirmed_at is not None or self.evidence_refs
        ):
            raise ValueError("Drafts cannot claim confirmation")
        return self


class GateReceipt(PolicyData):
    feature: str
    mode: Mode
    test_only: bool
    decision_versions: dict[str, str]


class Credits(PolicyData):
    credits: NonNegativeInt


class AssistQuota(PolicyData):
    count: PositiveInt
    decrement_ref: Text
    reset_ref: Text


class AssistPolicy(PolicyData):
    scheme: Literal["INDEPENDENT_FREE_QUOTA", "OTHER_CONFIRMED_SCHEME"]
    policy_ref: Text
    implementation_ref: Text
    quota: AssistQuota | None = None

    @model_validator(mode="after")
    def quota_for_selected_scheme(self):
        if self.scheme == "INDEPENDENT_FREE_QUOTA" and self.quota is None:
            raise ValueError("Independent quota requires count, decrement and reset rules")
        if self.scheme == "OTHER_CONFIRMED_SCHEME" and self.quota is not None:
            raise ValueError("Another scheme cannot implicitly adopt the independent quota")
        return self


class SpecPolicy(PolicyData):
    agent_id: Text
    agent_version: Version
    parameter_schema_ref: Text
    validation_evidence_ref: Text
    delivery_kind: Literal["single", "multiple", "detail_images"]


class DeliveryPolicy(PolicyData):
    delivery_ref: Text
    partial_failure_ref: Text
    billing_ref: Text
    missing_results_evidence_ref: Text


class AgentPolicy(PolicyData):
    protocol_version: Version
    input_schema_ref: Text
    authentication_ref: Text
    execution_ref: Text
    completion_ref: Text
    recovery_ref: Text
    callback_ref: Text
    error_ref: Text
    usage_ref: Text
    capabilities_ref: Text


class InputPolicy(PolicyData):
    protocol_version: Version
    validation_ref: Text
    supported_inputs_ref: Text


class ConcurrencyPolicy(PolicyData):
    max_concurrent_tasks: PositiveInt
    enforcement_ref: Text


class ExceptionPolicy(PolicyData):
    investigation_deadline_seconds: PositiveInt
    responsible_party_ref: Text
    settlement_evidence_ref: Text
    late_delivery_ref: Text
    save_failure_ref: Text
    deadline_is_failure: Literal[False]
    requires_complete_delivery: Literal[True]


class LifecycleHandoff(PolicyData):
    inflight_protection_ref: Text
    exception_handoff_ref: Text
    disabled_account_tasks_ref: Text


class UploadPolicy(PolicyData):
    max_file_bytes: PositiveInt
    account_quota_bytes: PositiveInt
    allowed_types: Annotated[list[Text], Field(min_length=1)]
    reservation_seconds: PositiveInt
    reclamation_ref: Text
    alert_ref: Text


class StoragePolicy(PolicyData):
    account_quota_bytes: PositiveInt
    server_budget_bytes: PositiveInt
    estimation_ref: Text
    reservation_seconds: PositiveInt
    reclamation_ref: Text
    alert_ref: Text
    allowed_download_sources: Annotated[list[Text], Field(min_length=1)]
    max_download_bytes: PositiveInt
    download_timeout_seconds: PositiveInt
    max_redirects: NonNegativeInt
    link_validity_ref: Text
    recovery_ref: Text


class DeletePolicy(PolicyData):
    execution: "DeleteExecution | None" = None
    list_history_ref: Text
    old_links_ref: Text
    restoration_ref: Text
    retention_reclamation_ref: Text
    capacity_ref: Text
    inflight_protection_ref: Text


class DisablePolicy(PolicyData):
    execution: "DisableExecution | None" = None
    tasks_ref: Text
    frozen_credits_ref: Text
    works_access_ref: Text
    restoration_ref: Text
    exception_handoff_ref: Text


class CostPolicy(PolicyData):
    source_ref: Text
    unit: Text
    accounting_ref: Text


class RecoveryPolicy(PolicyData):
    identity_verification_ref: Text
    permissions_ref: Text
    audit_ref: Text


class LoginHelpPolicy(PolicyData):
    instructions_ref: Text


class SitePolicy(PolicyData):
    name_brand_ref: Text
    content_ref: Text
    visual_ref: Text


class CasePolicy(PolicyData):
    source_work_ref: Text
    owner_ref: Text
    authorization_ref: Text
    withdrawal_ref: Text
    public_copy_cleanup_ref: Text
    is_mock: Literal[False]


class DeploymentPolicy(PolicyData):
    environment_ref: Text
    persistent_root_ref: Text
    consistent_backup_ref: Text
    restore_drill_evidence_ref: Text
    rpo_seconds: NonNegativeInt
    rto_seconds: PositiveInt
    monitoring_ref: Text
    public_terms_ref: Text


class InvestigationPolicy(PolicyData):
    schema_version: Literal["investigations-v1"]
    deadline_seconds: PositiveInt
    responsible_user_id: UUID
    escalation_ref: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:/-]{1,128}$")]
    authorized_actor_ids: Annotated[list[UUID], Field(min_length=1)]
    actions: Annotated[
        list[Literal["resume_original", "confirm_failure", "manual_close", "settle"]],
        Field(min_length=1),
    ]
    manual_release_basis: Literal["operator_review"]
    capacity_on_close: Literal["retain_all"]
    late_delivery: Literal["quarantine"]
    evidence_types: Annotated[
        list[Literal["review", "upstream_failure", "durable_delivery"]], Field(min_length=1)
    ]
    deadline_is_failure: Literal[False]
    requires_complete_delivery: Literal[True]


class DeleteExecution(PolicyData):
    schema_version: Literal["lifecycle-delete-v1"]
    list: Literal["hide"]
    history: Literal["tombstone"]
    old_links: Literal["deny"]
    restoration: Literal["disabled"]
    references: Literal["retain_all"]
    capacity: Literal["until_physical_removal"]
    retention_seconds: NonNegativeInt
    unreferenced_cleanup: bool = Field(strict=True)


class DisableExecution(PolicyData):
    schema_version: Literal["lifecycle-disable-v1"]
    inflight: Literal["continue_original"]
    frozen_credits: Literal["retain"]
    works_access: Literal["deny"]
    restoration: Literal["disabled", "new_login"]
    exception_policy_version: Version


DeletePolicy.model_rebuild()
DisablePolicy.model_rebuild()
