"""SSE data objects; only safe state references are durable notifications."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from app.common.types import DTO, PositiveInt, Timestamp
from app.events.service import TaskEventPayload


class DurableEventView(DTO):
    event_seq: PositiveInt
    payload: TaskEventPayload
    created_at: Timestamp


class ResetEvent(DTO):
    reason: Literal["cursor_unavailable"] = "cursor_unavailable"
    recovery_method: Literal["GET"] = "GET"
    recovery_resources: list[str] = Field(
        default_factory=lambda: [
            "/api/v1/tasks/{id}",
            "/api/v1/conversations/{id}",
        ]
    )
    instruction: str = "GET original persisted resources; never resubmit a task on reconnect."


class TransientFragment(DTO):
    task_id: UUID
    text: str = Field(max_length=4096)
    test_only: Literal[True] = True
    replayable: Literal[False] = False
