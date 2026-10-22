"""Draft-only public contract, independent of generation admission and billing."""

from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.catalog.schemas import Scalar, content_digest
from app.common.types import DTO, FileVersionRef
from app.policies.schemas import Version


class AssistRequest(DTO):
    agent_id: UUID
    agent_version: Version
    original: str = Field(max_length=20000)
    product: dict[str, Any]
    parameters: dict[str, Scalar]
    material_versions: list[FileVersionRef] = Field(max_length=100)

    @model_validator(mode="after")
    def bounded_input(self):
        import json

        content_digest(self.product)
        if len(json.dumps(self.product, ensure_ascii=False)) > 50000:
            raise ValueError("Product draft too large")
        return self


class AssistProposal(DTO):
    original: str
    proposed: str
    missing_facts: list[str]
    policy_version: Version
    parameters: dict[str, Scalar]
    agent_version: Version
    spec_version: Version
    test_only: bool = True
