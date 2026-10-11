"""Private published results and immutable source facts; no internal storage locations."""

from typing import Literal
from uuid import UUID

from app.common.types import DTO, FileVersionRef, PositiveInt, Timestamp
from app.tasks.schemas import TaskDetail

WorkKind = Literal["copy", "image", "video"]


class WorkItemView(DTO):
    item_key: str
    file_id: UUID
    file_version: str
    media_type: str
    actual_bytes: PositiveInt
    content_url: str
    text: str | None


class SourceMaterial(DTO):
    file: FileVersionRef
    available: bool
    action: Literal["upload_again"] | None


class WorkSource(TaskDetail):
    """Read-only original input. Reuse requires a new quote and a new intent key."""

    materials: list[SourceMaterial]
    requires_new_quote: Literal[True] = True
    credit_reservation_id: UUID
    ledger_ids: list[UUID]


class WorkView(DTO):
    work_id: UUID
    kind: WorkKind
    task_id: UUID
    conversation_id: UUID
    message_id: UUID
    created_at: Timestamp
    items: list[WorkItemView]


class WorkDetail(WorkView):
    source: WorkSource
