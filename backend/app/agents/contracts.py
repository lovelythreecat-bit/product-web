"""Agent boundary only; normalization is not task completion or safe-retry authorization."""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, populate_by_name=True, allow_inf_nan=False,
    )


class Support(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class Capabilities(Contract):
    sync: Support = Support.UNKNOWN
    async_: Support = Field(default=Support.UNKNOWN, alias="async")
    stream: Support = Support.UNKNOWN
    final_text: Support = Support.UNKNOWN
    idempotent_submit: Support = Support.UNKNOWN
    query_external: Support = Support.UNKNOWN
    query_id: Support = Support.UNKNOWN
    callback: Support = Support.UNKNOWN
    original_result_recovery: Support = Support.UNKNOWN


class AbsenceProof(Contract):
    """Protocol-scoped evidence, never permission to retry on its own.

    A real adapter must validate D-01 consistency and coverage before constructing
    this value. TEST_ONLY proofs must never be promoted to production evidence.
    """

    protocol_version: str
    agent_id: str
    external_submission_id: str
    reference: str
    verified_by: str
    verified_at: float
    coverage_start: float
    coverage_end: float
    consistency: str
    test_only: bool = False
    # Optional for other protocols; mandatory in the trusted TEST_ONLY sequence extension.
    scope_instance_id: str | None = None
    coverage_start_sequence: int | None = Field(default=None, strict=True, ge=0)
    coverage_end_sequence: int | None = Field(default=None, strict=True, ge=0)
    verified_sequence: int | None = Field(default=None, strict=True, ge=0)

    @model_validator(mode="after")
    def covered(self):
        if self.coverage_start > self.coverage_end or not self.consistency:
            raise ValueError("Absence proof requires a consistency rule and coverage interval")
        if not all((self.reference, self.verified_by, self.protocol_version)):
            raise ValueError("Absence proof requires provenance")
        return self


class ResultItem(Contract):
    item_key: str
    locator: str
    media_type: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    byte_length: int = Field(ge=1)


class ResultManifest(Contract):
    complete: bool
    expected_items: int = Field(ge=1)
    items: tuple[ResultItem, ...]

    @model_validator(mode="after")
    def complete_delivery(self):
        keys = [item.item_key for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate result items")
        if self.complete and len(keys) != self.expected_items:
            raise ValueError("Complete result must contain every expected item")
        return self


class Outcome(Contract):
    protocol_version: str = "unknown"
    test_only: bool = False
    external_submission_id: str | None = None
    upstream_task_id: str | None = None
    absence_proof: AbsenceProof | None = None

    @model_validator(mode="after")
    def proof_consistency(self):
        proven = self.status == "PROVEN_NOT_ACCEPTED"
        if proven != (self.absence_proof is not None):
            raise ValueError("Only PROVEN_NOT_ACCEPTED requires an absence proof")
        if self.absence_proof is not None:
            proof = self.absence_proof
            if (proof.external_submission_id != self.external_submission_id
                    or proof.protocol_version != self.protocol_version
                    or proof.test_only != self.test_only):
                raise ValueError("Absence proof does not match the outcome")
        return self


class SubmitOutcome(Outcome):
    status: Literal["ACCEPTED", "COMPLETED", "UNKNOWN", "REJECTED", "UNSUPPORTED",
                    "PROVEN_NOT_ACCEPTED"]
    result: ResultManifest | None = None

    @model_validator(mode="after")
    def accepted_identity(self):
        if self.status == "ACCEPTED" and not self.upstream_task_id:
            raise ValueError("Accepted asynchronous submission requires a task id")
        if self.status == "COMPLETED" and (self.result is None or not self.result.complete):
            raise ValueError("Completed submission requires a complete result")
        return self


class QueryOutcome(Outcome):
    status: Literal["FOUND", "UNSUPPORTED", "NOT_FOUND", "UNAVAILABLE", "PROVEN_NOT_ACCEPTED"]
    state: Literal["RUNNING", "RESULT_READY", "FAILED"] | None = None
    result: ResultManifest | None = None

    @model_validator(mode="after")
    def found_identity(self):
        if self.status == "FOUND" and (not self.upstream_task_id or self.state is None):
            raise ValueError("Found task requires identity and state")
        return self


class VerifiedEvent(Contract):
    """Verified origin/shape only. The task reducer must bind identities and reject regressions.

    DUPLICATE is advisory in-memory detection; durable deduplication belongs to T10.
    """

    status: Literal["VERIFIED", "DUPLICATE", "INVALID", "UNSUPPORTED"]
    protocol_version: str = "unknown"
    test_only: bool = False
    agent_id: str | None = None
    event_id: str | None = None
    external_submission_id: str | None = None
    upstream_task_id: str | None = None
    sequence: int | None = None
    state: Literal["RUNNING", "RESULT_READY", "FAILED"] | None = None
    timestamp: float | None = None
    result: ResultManifest | None = None


class ResultSource(Contract):
    status: Literal["AVAILABLE", "EXPIRED", "NOT_FOUND", "UNSUPPORTED", "UNAVAILABLE"]
    protocol_version: str = "unknown"
    test_only: bool = False
    locator: str
    content: bytes | None = None
    media_type: str | None = None
    complete: bool = False
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    byte_length: int | None = Field(default=None, ge=1)


@runtime_checkable
class AgentAdapter(Protocol):
    agent_id: str
    protocol_version: str
    test_only: bool
    capabilities: Capabilities

    def submit(self, snapshot: Mapping[str, Any], external_submission_id: str) -> SubmitOutcome: ...
    def query_by_external(self, external_submission_id: str) -> QueryOutcome: ...
    def query(self, upstream_task_id: str) -> QueryOutcome: ...
    def verify_callback(self, raw: bytes, headers: Mapping[str, str]) -> VerifiedEvent: ...
    def retrieve_original(self, locator: str) -> ResultSource: ...
