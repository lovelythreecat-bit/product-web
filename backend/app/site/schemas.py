"""Public DTOs never expose private work/file paths or authorization evidence."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from app.common.types import DTO, NonNegativeInt
from app.policies.schemas import Version

Text = Annotated[str, Field(min_length=1, max_length=5000, pattern=r"\S")]


class AgentDescriptions(DTO):
    text: Text
    image: Text
    video: Text


class SiteContent(DTO):
    product_intro: Text
    agent_descriptions: AgentDescriptions
    process_steps: Annotated[list[Text], Field(min_length=1, max_length=12)]


class SiteContentUpdate(DTO):
    expected_version: NonNegativeInt
    content: SiteContent
    policy_version: Version
    policy_versions: dict[str, Version] = Field(default_factory=dict)


class SiteContentView(DTO):
    version: NonNegativeInt
    content: SiteContent | None
    status: Literal["draft", "approved"]
    policy_version: str
    policy_versions: dict[str, str]
    content_ref: str | None


class CasePublish(DTO):
    work_id: UUID
    authorization_ref: Annotated[str, Field(min_length=1, max_length=1024)]
    policy_version: Version
    policy_versions: dict[str, Version]


class CaseWithdraw(DTO):
    policy_version: Version


class PublicCopyView(DTO):
    id: UUID
    media_type: str
    url: str


class PublicCaseView(DTO):
    id: UUID
    items: list[PublicCopyView]


class AdminCaseView(DTO):
    id: UUID
    work_id: UUID
    owner_id: UUID
    authorization_ref: str
    policy_version: str
    withdrawal_policy_version: str | None
    state: Literal["published", "cleanup_pending", "withdrawn"]


class PublicSiteView(DTO):
    content: SiteContentView | None
