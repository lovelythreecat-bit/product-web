"""Media administration DTOs: native resource versions, strict writes, safe reads."""

from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)

from app.agents.media_http import MediaServiceError
from app.agents.text import TextAgentProfile
from app.common.types import DTO, ConfigurationChange

MediaKind = Literal["image", "video"]
Role = Literal["planner", "video", "voice", "music", "visual"]
Protocol = Literal["openrouter_images", "openai_images", "chat_completions"]
Name = Annotated[str, Field(min_length=1, max_length=200)]
Version = Annotated[int, Field(strict=True, ge=1)]


class Strict(DTO):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, allow_inf_nan=False)


class MediaConnectionUpdate(ConfigurationChange):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    expected_revision: int = Field(strict=True, ge=0)
    base_url: str | None = Field(default=None, min_length=1, max_length=2048)
    service_key: SecretStr | None = Field(default=None, min_length=1, max_length=8192, repr=False)
    management_key: SecretStr | None = Field(
        default=None, min_length=1, max_length=8192, repr=False
    )
    default_config_id: UUID | None = None
    image_model: Literal["pro", "fast", "base"] | None = None
    video_audio_enabled: bool | None = Field(default=None, strict=True)

    @field_validator("base_url")
    @classmethod
    def valid_url(cls, value):
        return TextAgentProfile.valid_url(value) if value is not None else value

    @field_validator("service_key", "management_key")
    @classmethod
    def valid_key(cls, value):
        return TextAgentProfile.valid_key(value) if value is not None else value


class MediaConnectionView(DTO):
    id: UUID | None
    kind: MediaKind
    base_url: str | None
    revision: int = Field(ge=0)
    has_service_key: bool
    has_management_key: bool
    default_config_id: UUID | None
    image_model: str | None


class ImageModelSetting(Strict):
    base_url: str = Field(min_length=1, max_length=2048)
    model: str = Field(min_length=1, max_length=300)
    protocol: Protocol
    api_key: SecretStr | None = Field(default=None, min_length=1, max_length=8192, repr=False)

    @field_validator("base_url")
    @classmethod
    def valid_url(cls, value):
        parts = urlsplit(value)
        if (parts.scheme not in {"http", "https"} or not parts.hostname
                or parts.username or parts.password or parts.query or parts.fragment
                or "\\" in value or any(ord(char) <= 32 for char in value)):
            raise ValueError("Invalid provider API URL")
        return value.rstrip("/")

    @field_validator("model")
    @classmethod
    def nonblank_model(cls, value):
        if not value.strip():
            raise ValueError("Model must not be blank")
        return value.strip()

    @field_validator("api_key")
    @classmethod
    def valid_key(cls, value):
        return TextAgentProfile.valid_key(value) if value is not None else value


class ImageModelsUpdate(ConfigurationChange):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    expected_revision: int = Field(strict=True, ge=0)
    expected_versions: dict[str, Version] = Field(max_length=100)
    text_model: ImageModelSetting
    image_model: ImageModelSetting

    @model_validator(mode="after")
    def role_protocols(self):
        if self.text_model.protocol != "chat_completions":
            raise ValueError("Text model requires chat_completions with image input support")
        if self.image_model.protocol not in {"openai_images", "openrouter_images"}:
            raise ValueError("Image model requires an image generation protocol")
        return self


class ImageModelSettingView(DTO):
    base_url: str
    model: str
    protocol: Protocol
    has_api_key: bool
    enabled: bool


class ImageModelsView(DTO):
    revision: int = Field(ge=0)
    versions: dict[str, Version]
    text_model: ImageModelSettingView | None
    image_model: ImageModelSettingView | None


class MediaResourceWrite(ConfigurationChange):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    config: dict[str, JsonValue] = Field(repr=False)
    expected_connection_revision: int | None = Field(default=None, strict=True, ge=0)


class ImageServiceCreate(Strict):
    name: Name
    base_url: str = Field(max_length=2048)
    protocol: Protocol
    api_key: SecretStr = Field(min_length=1, max_length=8192, repr=False)
    generation_path: str | None = Field(default=None, max_length=512)
    edit_path: str | None = Field(default=None, max_length=512)
    chat_path: str = Field(default="/chat/completions", max_length=512)
    enabled: bool = True

    @field_validator("api_key")
    @classmethod
    def nonblank_key(cls, value):
        if not value.get_secret_value().strip():
            raise ValueError("Blank key")
        return value


class ImageServicePatch(Strict):
    version: Version
    name: Name | None = None
    base_url: str | None = Field(default=None, max_length=2048)
    protocol: Protocol | None = None
    api_key: SecretStr = Field(default=None, min_length=1, max_length=8192, repr=False)
    generation_path: str | None = Field(default=None, max_length=512)
    edit_path: str | None = Field(default=None, max_length=512)
    chat_path: str | None = Field(default=None, max_length=512)
    enabled: bool | None = None

    @field_validator("api_key")
    @classmethod
    def nonblank_key(cls, value):
        return ImageServiceCreate.nonblank_key(value)


class ImageModelCreate(Strict):
    service_id: UUID
    model: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    enabled: bool = True


class ImageModelPatch(Strict):
    version: Version
    service_id: UUID | None = None
    model: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    enabled: bool | None = None


class ImageParameters(Strict):
    http_proxy: str | None = None
    request_timeout_seconds: float = Field(default=180, gt=0)
    model_concurrency: int = Field(default=2, strict=True, gt=0)
    generation_reference_limit: int = Field(default=4, strict=True, gt=0)
    vision_image_limit: int = Field(default=12, strict=True, gt=0)
    model_completion_attempts: int = Field(default=4, strict=True, ge=1, le=8)


class ImageAgentCreate(Strict):
    name: Name
    parameters: ImageParameters = Field(default_factory=ImageParameters)
    image_models: dict[Literal["pro", "fast", "base"], UUID] = Field(min_length=1)
    stages: dict[str, UUID] = Field(min_length=1)
    enabled: bool = True


class ImageAgentPatch(Strict):
    version: Version
    name: Name | None = None
    parameters: ImageParameters | None = None
    image_models: dict[Literal["pro", "fast", "base"], UUID] | None = Field(
        default=None, min_length=1
    )
    stages: dict[str, UUID] | None = Field(default=None, min_length=1)
    enabled: bool | None = None


class VideoProfileCreate(Strict):
    name: Name
    role: Role
    adapter: str = Field(min_length=1, max_length=80)
    base_url: str | None = Field(default=None, max_length=2000)
    model: str | None = Field(default=None, max_length=200)
    parameters: dict[str, JsonValue] = Field(default_factory=dict, repr=False)
    secrets: dict[str, str] = Field(default_factory=dict, repr=False)
    enabled: bool = True


class VideoProfilePatch(Strict):
    expected_version: Version
    name: Name | None = None
    role: Role | None = None
    adapter: str | None = Field(default=None, min_length=1, max_length=80)
    base_url: str | None = Field(default=None, max_length=2000)
    model: str | None = Field(default=None, max_length=200)
    parameters: dict[str, JsonValue] | None = Field(default=None, repr=False)
    secrets: dict[str, str] = Field(default_factory=dict, repr=False)
    clear_secrets: list[str] = Field(default_factory=list)
    enabled: bool | None = None

    @model_validator(mode="after")
    def separate_clear(self):
        if set(self.clear_secrets) & set(self.secrets):
            raise ValueError("Cannot clear and replace the same secret")
        return self


class BindingTarget(Strict):
    adapter: str | None = None
    profile_id: str | None = None


class VideoBindingsPatch(Strict):
    expected_version: Version
    planner: BindingTarget | None = None
    video: BindingTarget | None = None
    voice: BindingTarget | None = None
    music: BindingTarget | None = None
    visual: BindingTarget | None = None


class VideoSettingsPatch(Strict):
    expected_version: Version
    mode: Literal["fake", "real"] | None = None
    duration_tiers: list[Annotated[int, Field(strict=True, ge=1, le=30)]] | None = None
    default_duration: int | None = Field(default=None, strict=True, ge=1, le=30)
    max_images: int | None = Field(default=None, strict=True, ge=1, le=12)
    max_file_bytes: int | None = Field(default=None, strict=True, ge=1, le=20971520)
    video_bitrate: int | None = Field(default=None, strict=True, ge=1)
    audio_bitrate: int | None = Field(default=None, strict=True, ge=1)
    lease_seconds: int | None = Field(default=None, strict=True, ge=15)
    resolutions: dict[str, tuple[int, int]] | None = None


VideoModelRole = Literal["planner", "video", "visual"]


class VideoAudioUpdate(Strict):
    expected_revision: int = Field(strict=True, ge=0)
    expected_configuration_revision: Version
    enabled: bool = Field(strict=True)


class VideoModelUpdate(Strict):
    expected_revision: int = Field(strict=True, ge=0)
    expected_configuration_revision: Version
    expected_profile_id: str | None
    expected_profile_version: Version | None
    enabled: bool = True
    adapter: Literal["openai_chat", "seedance", "wan", "openai_vision"]
    base_url: str | None = Field(default=None, max_length=2000)
    model: str | None = Field(default=None, max_length=200)
    api_key: SecretStr | None = Field(default=None, min_length=1, max_length=8192, repr=False)
    max_segment_seconds: int | None = Field(default=None, strict=True, ge=1, le=15)

    @field_validator("base_url")
    @classmethod
    def valid_url(cls, value):
        return ImageModelSetting.valid_url(value) if value else value

    @field_validator("api_key")
    @classmethod
    def valid_key(cls, value):
        return TextAgentProfile.valid_key(value) if value is not None else value


WRITES = {
    ("image", "services"): (ImageServiceCreate, ImageServicePatch),
    ("image", "model-configs"): (ImageModelCreate, ImageModelPatch),
    ("image", "agent-configs"): (ImageAgentCreate, ImageAgentPatch),
    ("video", "model-profiles"): (VideoProfileCreate, VideoProfilePatch),
    ("video", "adapter-bindings"): (None, VideoBindingsPatch),
    ("video", "settings"): (None, VideoSettingsPatch),
    ("video", "adapter-types"): (None, None),
}


def _secret_field(key):
    return any(
        word in key.lower()
        for word in (
            "key",
            "token",
            "secret",
            "password",
            "credential",
            "authorization",
            "ciphertext",
        )
    )


def _safe_url(value):
    if isinstance(value, str) and "://" in value:
        parts = urlsplit(value)
        if parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("Credential-bearing URL")
    return value


def scrub_parameters(value):
    if isinstance(value, dict):
        return {
            key: scrub_parameters(item) for key, item in value.items() if not _secret_field(key)
        }
    if isinstance(value, list):
        return [scrub_parameters(item) for item in value]
    return _safe_url(value)


def _plain(value):
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def resource_body(kind, resource, config, *, patch=False):
    schema = WRITES.get((kind, resource), (None, None))[int(patch)]
    if schema is None:
        raise MediaServiceError(404)
    try:
        value = schema.model_validate(config)
        result = _plain(value.model_dump(mode="python", exclude_unset=True))
        if "base_url" in result:
            _safe_url(result["base_url"])
        if "parameters" in result and result["parameters"] is not None:
            if scrub_parameters(result["parameters"]) != result["parameters"]:
                raise ValueError("Secrets must use secrets field")
        return result
    except (ValidationError, TypeError, ValueError):
        raise MediaServiceError(422, "配置字段或资源版本不符合媒体服务接口要求。") from None


class Read(BaseModel):
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)


class ImageRead(Read):
    id: UUID
    version: Version
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ImageServiceRead(ImageRead):
    name: str
    base_url: str
    protocol: Protocol
    generation_path: str | None
    edit_path: str | None
    chat_path: str
    has_api_key: bool


class ImageModelRead(ImageRead):
    service_id: UUID
    model: str
    description: str | None


class ImageAgentRead(ImageRead):
    name: str
    parameters: ImageParameters
    image_models: dict[str, UUID]
    stages: dict[str, UUID]


class VideoProfileRead(Read):
    profile_id: str
    name: str
    role: Role
    adapter: str
    base_url: str | None
    model: str | None
    parameters: dict[str, JsonValue]
    enabled: bool
    version: Version
    has_api_key: bool
    secret_presence: dict[str, bool]
    created_at: str
    updated_at: str


class AdapterTypeRead(Read):
    adapter: str
    roles: list[Role]
    required_fields: list[str] = Field(default_factory=list)
    secret_fields: list[str] = Field(default_factory=list)
    parameters: dict[str, JsonValue] | list[JsonValue] = Field(default_factory=dict)
    capabilities: dict[str, JsonValue] = Field(default_factory=dict)


class VideoBindingsRead(Read):
    configuration_revision: Version
    planner: BindingTarget
    video: BindingTarget
    voice: BindingTarget
    music: BindingTarget
    visual: BindingTarget


class VideoSettingsRead(Read):
    configuration_revision: Version
    mode: Literal["fake", "real"]
    duration_tiers: list[int]
    default_duration: int
    max_images: int
    max_file_bytes: int
    video_bitrate: int
    audio_bitrate: int
    lease_seconds: int
    resolutions: dict[str, tuple[int, int]]


READS = {
    ("image", "services"): ImageServiceRead,
    ("image", "model-configs"): ImageModelRead,
    ("image", "agent-configs"): ImageAgentRead,
    ("video", "model-profiles"): VideoProfileRead,
    ("video", "adapter-types"): AdapterTypeRead,
    ("video", "adapter-bindings"): VideoBindingsRead,
    ("video", "settings"): VideoSettingsRead,
}


def project_resource(kind, resource, payload, *, listing=False):
    schema = READS.get((kind, resource))
    if schema is None:
        raise MediaServiceError(404)

    def one(raw):
        # Unknown nested fields are removed before validating strict nested objects.
        raw = dict(raw)
        for field in ("parameters", "capabilities"):
            if field in raw:
                raw[field] = scrub_parameters(raw[field])
        if (
            kind == "image"
            and resource == "agent-configs"
            and isinstance(raw.get("parameters"), dict)
        ):
            raw["parameters"] = {
                k: v for k, v in raw["parameters"].items() if k in ImageParameters.model_fields
            }
        if "base_url" in raw:
            _safe_url(raw["base_url"])
        return schema.model_validate(raw).model_dump(mode="json")

    try:
        if listing and kind == "video" and resource == "model-profiles":
            if (
                not isinstance(payload, dict)
                or not isinstance(payload.get("items"), list)
                or any(type(payload.get(key)) is not int for key in ("limit", "offset", "total"))
                or not 1 <= payload["limit"] <= 100
                or payload["offset"] < 0
                or payload["total"] < 0
                or len(payload["items"]) > payload["limit"]
            ):
                raise ValueError()
            return {
                "items": [one(item) for item in payload["items"]],
                **{key: payload[key] for key in ("limit", "offset", "total")},
            }
        if listing and resource not in {"adapter-bindings", "settings"}:
            if not isinstance(payload, list) or len(payload) > 100:
                raise ValueError()
            return [one(item) for item in payload]
        return one(payload)
    except (ValidationError, ValueError, KeyError, TypeError):
        raise MediaServiceError() from None
