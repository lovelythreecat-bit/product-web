from typing import Annotated
from uuid import UUID

from pydantic import Field, SecretStr, field_validator

from app.common.types import DTO, UserRole


class LoginRequest(DTO):
    account: Annotated[str, Field(min_length=3, max_length=64)]
    password: SecretStr = Field(min_length=10, max_length=128)


class RegisterRequest(LoginRequest):
    request_key: Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_:-]+$")]


class ProfileUpdate(DTO):
    nickname: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    bio: Annotated[str, Field(max_length=500)] | None = None

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


class AuthView(DTO):
    profile: ProfileView
    replayed: bool
