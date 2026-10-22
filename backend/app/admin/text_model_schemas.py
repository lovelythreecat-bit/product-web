"""Local admin DTOs matching ecommerce_copy_api 1.0 model configurations."""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, SecretStr, model_validator

from app.common.types import DTO, ConfigurationChange

ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"]


class TextModelFields(DTO):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=100)
    provider: Literal["openai_chat"] = "openai_chat"
    base_url: str = Field(min_length=1, max_length=2048)
    model: str = Field(min_length=1, max_length=200)
    supports_images: bool = False
    timeout_seconds: float = Field(default=60, ge=1, le=120)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, strict=True, gt=0)
    reasoning_effort: ReasoningEffort | None = None


class TextModelCreateFields(TextModelFields):
    api_key: SecretStr = Field(min_length=1, max_length=8192, repr=False)


class TextModelPatch(DTO):
    # PATCH permits partial updates; explicit null resets only nullable model settings.
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, allow_inf_nan=False)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    provider: Literal["openai_chat"] | None = None
    base_url: str | None = Field(default=None, min_length=1, max_length=2048)
    model: str | None = Field(default=None, min_length=1, max_length=200)
    api_key: SecretStr | None = Field(default=None, min_length=1, max_length=8192, repr=False)
    supports_images: bool | None = None
    timeout_seconds: float | None = Field(default=None, ge=1, le=120)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, strict=True, gt=0)
    reasoning_effort: ReasoningEffort | None = None
    enabled: bool | None = None

    @model_validator(mode="after")
    def valid_patch(self):
        if not self.model_fields_set or any(
            getattr(self, key) is None
            for key in self.model_fields_set - {"temperature", "max_tokens", "reasoning_effort"}
        ):
            raise ValueError("Supply changed fields; only optional model settings accept null")
        return self


class TextModelCreate(ConfigurationChange):
    config: TextModelCreateFields


class TextModelUpdate(ConfigurationChange):
    expected_revision: int = Field(strict=True, ge=1)
    config: TextModelPatch


class TextModelView(BaseModel):
    # Explicit projection also drops any accidental upstream credential fields.
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)
    id: UUID
    name: str
    provider: str
    base_url: str
    model: str
    supports_images: bool
    timeout_seconds: float
    temperature: float | None
    max_tokens: int | None
    reasoning_effort: ReasoningEffort | None = None
    has_api_key: bool
    enabled: bool
    revision: int = Field(ge=1)
    created_at: AwareDatetime
    updated_at: AwareDatetime


class TextModelPage(DTO):
    items: list[TextModelView]
    next_cursor: str | None = None
