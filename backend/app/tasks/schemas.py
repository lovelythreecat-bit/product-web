from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.common.types import DTO, InputSnapshot, TaskView
from app.policies.schemas import Text, Version


class GenerationEstimate(DTO):
    """Server-selected upper estimate for ALL outputs across an exact spec's parameters.

    The total is bound to the reviewed D-10 estimation reference. No client amount
    or unconfirmed production fallback can select the reservation size.
    """

    spec_version: Version
    policy_version: Version
    estimation_ref: Text
    total_bytes: Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]


class TaskDetail(DTO):
    task: TaskView
    conversation_id: UUID
    agent_id: UUID
    input: InputSnapshot
    policy_versions: dict[str, str]
