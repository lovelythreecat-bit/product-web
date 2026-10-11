"""Environment configuration. No production policy or credential defaults."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", extra="forbid", hide_input_in_errors=True)

    mode: Literal["mock", "staging", "production"] = "mock"
    test_only: bool = True
    auth_origins: list[str] = []
    storage_root: Path | None = None
    storage_persistent: bool = False
    database_url: SecretStr | None = None
    redis_url: SecretStr | None = None

    @model_validator(mode="after")
    def reject_test_configuration(self) -> "Settings":
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
