"""Explicit supported input/parameter contracts; no speculative production defaults."""

import hashlib
import json
from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, SecretStr, model_validator

from app.common.types import DTO, InputSnapshot, NonNegativeInt, Quote
from app.policies.schemas import Mode, Version

Name = Annotated[str, Field(min_length=1, max_length=128, pattern=r"\S")]
Scalar = str | Annotated[int, Field(strict=True)] | Annotated[bool, Field(strict=True)]


def content_digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


class CatalogDTO(DTO):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class InputSupport(CatalogDTO):
    product_required_fields: list[Name]
    instruction_required: bool = Field(strict=True)
    min_materials: NonNegativeInt
    max_materials: NonNegativeInt

    @model_validator(mode="after")
    def valid_range(self):
        if self.min_materials > self.max_materials:
            raise ValueError("Invalid material range")
        return self


class ParameterRule(CatalogDTO):
    kind: Literal["string", "integer", "boolean"]
    required: bool = Field(strict=True)
    choices: list[Scalar] | None = None
    minimum: Annotated[int, Field(strict=True)] | None = None
    maximum: Annotated[int, Field(strict=True)] | None = None
    max_length: NonNegativeInt | None = None
    default: Scalar | None = None

    def accepts(self, value):
        expected = {"string": str, "integer": int, "boolean": bool}[self.kind]
        return (
            type(value) is expected
            and (
                self.choices is None
                or any(type(v) is type(value) and v == value for v in self.choices)
            )
            and (self.minimum is None or value >= self.minimum)
            and (self.maximum is None or value <= self.maximum)
            and (self.max_length is None or len(value) <= self.max_length)
        )

    @model_validator(mode="after")
    def valid_rule(self):
        if self.kind != "integer" and (self.minimum is not None or self.maximum is not None):
            raise ValueError("Numeric bounds require integer parameters")
        if self.kind != "string" and self.max_length is not None:
            raise ValueError("Length bound requires string parameter")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("Invalid numeric range")
        if self.choices is not None and (
            not self.choices or any(not self.accepts(v) for v in self.choices)
        ):
            raise ValueError("Invalid choices")
        if self.default is not None and not self.accepts(self.default):
            raise ValueError("Invalid default")
        return self


class ParameterSchema(CatalogDTO):
    fields: dict[Name, ParameterRule]
    # When supplied, each object is a supported complete parameter combination.
    combinations: list[dict[str, Scalar]]

    def accepts(self, values):
        return (
            not values.keys() - self.fields.keys()
            and all(
                (name in values and rule.accepts(values[name]))
                or (name not in values and not rule.required)
                for name, rule in self.fields.items()
            )
            and (
                not self.combinations
                or any(content_digest(values) == content_digest(c) for c in self.combinations)
            )
        )

    @model_validator(mode="after")
    def valid_combinations(self):
        if any(not self.accepts(value) for value in self.combinations):
            raise ValueError("Unsupported combination")
        return self


class Publication(CatalogDTO):
    version: Version
    expected_version: Version | None = None
    enabled: bool = Field(strict=True)
    reason: Annotated[str, Field(min_length=1, max_length=500, pattern=r"\S")]


class AgentDraft(Publication):
    agent_id: UUID
    mode: Mode
    test_only: bool = Field(strict=True)
    kind: Literal["copy", "image", "video"]
    name: Name
    protocol_version: Version
    input_support: InputSupport
    endpoint: SecretStr
    secret_ref: SecretStr | None = None
    policy_versions: dict[str, Version]

    @model_validator(mode="after")
    def provenance(self):
        if self.test_only != (self.mode == "mock"):
            raise ValueError("Mock values must be TEST_ONLY")
        return self


class SpecDraft(Publication):
    spec_id: UUID
    agent_id: UUID
    agent_version: Version
    name: Name
    parameter_schema: ParameterSchema
    delivery_kind: Literal["single", "multiple", "detail_images"]
    policy_versions: dict[str, Version]


class PriceDraft(Publication):
    spec_id: UUID
    credits: NonNegativeInt
    policy_version: Version


class AgentVersion(CatalogDTO):
    agent_id: UUID
    version: Version
    kind: Literal["copy", "image", "video"]
    name: Name
    mode: Mode
    test_only: bool
    enabled: bool
    protocol_version: Version
    input_support: InputSupport
    policy_versions: dict[str, Version]
    secret_configured: bool


class SpecVersion(CatalogDTO):
    spec_id: UUID
    version: Version
    agent_id: UUID
    agent_version: Version
    name: Name
    parameter_schema: ParameterSchema
    delivery_kind: Literal["single", "multiple", "detail_images"]
    enabled: bool
    policy_versions: dict[str, Version]


class PriceVersion(CatalogDTO):
    spec_id: UUID
    version: Version
    credits: NonNegativeInt
    policy_version: Version
    enabled: bool


class QuoteRequest(CatalogDTO):
    spec_id: UUID
    input: InputSnapshot


class ValidatedQuote(CatalogDTO):
    """Transaction-local result; caller must not cache it across admission transactions."""

    quote: Quote
    agent: AgentVersion
    spec: SpecVersion
    price: PriceVersion


def support_ref(value) -> str:
    # Exclude absent optional rule fields so clients can hash the compact declared schema.
    return "sha256:" + content_digest(value.model_dump(mode="json", exclude_none=True))
