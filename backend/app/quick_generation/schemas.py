from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints, field_validator

from app.common.types import DTO, FileVersionRef, SubmitTaskRequest
from app.tasks.schemas import TaskDetail

ImageOutput = Literal["main_image", "detail_page", "long_image"]
Kind = Literal["copy", "image", "video"]
CopyType = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
CopyText = Annotated[str, StringConstraints(max_length=100000)]


class QuickDraft(DTO):
    product_version: str | None = Field(default=None, max_length=36)
    material_versions: list[FileVersionRef] = Field(default_factory=list, max_length=20)
    copy_parameters: dict[str, str | int | bool] = Field(default_factory=dict, max_length=6)
    copy_types: list[CopyType] = Field(default_factory=list, max_length=7)
    copy_instruction: str = Field(default="", max_length=10000)
    copy_text: str = Field(default="", max_length=100000)
    copy_texts: dict[CopyType, CopyText] = Field(default_factory=dict, max_length=7)
    image_platform: str = Field(default="", max_length=32)
    image_outputs: list[ImageOutput] = Field(default_factory=list, max_length=3)
    image_instruction: str = Field(default="", max_length=10000)
    video_first_frame_file_id: str = Field(default="", max_length=36)
    video_instruction: str = Field(default="", max_length=10000)

    @field_validator("copy_types")
    @classmethod
    def distinct_copy_types(cls, values):
        return list(dict.fromkeys(values))


class QuickCreate(DTO):
    run_id: UUID


class QuickSave(DTO):
    version: int = Field(ge=1)
    draft: QuickDraft


class QuickPrepare(DTO):
    version: int = Field(ge=1)
    kind: Kind
    outputs: list[ImageOutput] | None = Field(default=None, max_length=3)
    item_index: int | None = Field(default=None, ge=0, strict=True)


class QuickAdvance(DTO):
    version: int = Field(ge=1)
    action: Literal["confirm_copy", "confirm_images", "finish", "back"]


class QuickBatchItem(DTO):
    label: str
    request: SubmitTaskRequest
    task_id: str | None = None
    free_regenerations_used: int = Field(default=0, ge=0, le=3)
    regeneration_of: str | None = None
    free_regeneration: bool = False


class QuickBatch(DTO):
    id: str
    kind: Kind
    draft_digest: str
    submitted: bool = False
    items: list[QuickBatchItem]


class QuickState(DTO):
    step: int = Field(ge=1, le=5)
    draft: QuickDraft
    confirmed_copy: str | None = None
    confirmed_images: str | None = None
    current: dict[str, str | None]
    pending_batch: str | None = None
    batches: list[QuickBatch] = Field(default_factory=list)


class QuickSummary(DTO):
    run_id: UUID
    conversation_id: UUID
    title: str
    step: int
    version: int


class QuickView(QuickSummary):
    state: QuickState
    tasks: dict[str, TaskDetail]
