"""Environment configuration. No production policy or credential defaults."""

from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.tasks.schemas import GenerationEstimate


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", extra="forbid", hide_input_in_errors=True)

    mode: Literal["mock", "staging", "production"] = "mock"
    test_only: bool = True
    # Production approval authority is unresolved. Only an explicitly isolated
    # mock approver list is supported; there is no production default authority.
    test_only_content_approver_ids: list[UUID] = []
    assist_policy_version: str | None = None
    assist_provider: Literal["deterministic_mock"] | None = None
    assist_timeout_seconds: float = Field(default=10, gt=0, le=60)
    assist_rate_limit: int = Field(default=10, ge=1, le=100)
    auth_origins: list[str] = []
    storage_root: Path | None = None
    storage_persistent: bool = False
    storage_policy_version: str | None = None
    generation_policy_versions: dict[str, str] = {}
    generation_capacity_estimates: dict[str, GenerationEstimate] = {}
    database_url: SecretStr | None = None
    redis_url: SecretStr | None = None
    event_retention_seconds: int = Field(default=7 * 86400, ge=1, le=365 * 86400)

    @model_validator(mode="after")
    def reject_test_configuration(self) -> "Settings":
        if self.test_only_content_approver_ids and (self.mode != "mock" or not self.test_only):
            raise ValueError("Content approvers are TEST_ONLY and require mock mode")
        if self.mode != "mock":
            values = [self.database_url, self.redis_url]
            contains_test_value = any(
                value and "TEST_ONLY" in value.get_secret_value().upper() for value in values
            )
            contains_test_value = contains_test_value or (
                self.storage_root is not None and "TEST_ONLY" in str(self.storage_root).upper()
            )
            if self.test_only or contains_test_value:
                raise ValueError("TEST_ONLY configuration is only permitted in mock mode")
        return self
