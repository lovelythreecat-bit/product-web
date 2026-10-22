import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, SecretStr, field_validator

from app.common.types import DTO, FileVersionRef, Timestamp, UserRole


class LoginRequest(DTO):
    account: Annotated[str, Field(min_length=3, max_length=64)]
    password: SecretStr = Field(min_length=10, max_length=128)


class RegisterRequest(LoginRequest):
    request_key: Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_:-]+$")]


class PasswordChangeRequest(DTO):
    current_password: SecretStr = Field(min_length=10, max_length=128)
    new_password: SecretStr = Field(min_length=10, max_length=128)


class ProfileUpdate(DTO):
    nickname: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    bio: Annotated[str, Field(max_length=500)] | None = None
    shop_name: Annotated[str, Field(max_length=80)] | None = None
    category: Annotated[str, Field(max_length=80)] | None = None
    email: Annotated[str, Field(max_length=120)] | None = None
    phone: Annotated[str, Field(max_length=40)] | None = None
    avatar: FileVersionRef | None = None

    @field_validator("shop_name", "category", "email", "phone", mode="before")
    @classmethod
    def optional_text(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        if value is not None and re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value) is None:
            raise ValueError("Invalid contact email")
        return value

    @field_validator("avatar")
    @classmethod
    def valid_avatar_version(cls, value):
        if value is not None:
            try:
                version = str(UUID(value.version))
            except (ValueError, TypeError, AttributeError):
                raise ValueError("Invalid avatar file version") from None
            return value.model_copy(update={"version": version})
        return value

    @field_validator("nickname")
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Nickname must not be blank")
        return value


class ProfileView(DTO):
    user_id: UUID
    account: str
    role: UserRole
    nickname: str | None
    bio: str | None
    shop_name: str | None
    category: str | None
    email: str | None
    phone: str | None
    avatar: FileVersionRef | None
    status: Literal["active", "disabled"]
    created_at: Timestamp
    last_login_at: Timestamp | None


class AuthView(DTO):
    profile: ProfileView
    replayed: bool
