"""Database-owned service connection and authenticated encryption of its credential."""

import json
from datetime import UTC, datetime

from cryptography.fernet import Fernet, InvalidToken
from pydantic import AwareDatetime, ConfigDict, Field, SecretStr, field_validator

from app.admin.models import TextServiceConnection
from app.agents.model_configs import TextModelError, TextModelService
from app.agents.text import TextAgentProfile
from app.common.types import ConfigurationChange, DTO


class TextServiceConnectionView(DTO):
    base_url: str | None
    has_service_key: bool
    revision: int = Field(ge=0)
    updated_at: AwareDatetime | None


class TextServiceConnectionUpdate(ConfigurationChange):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    expected_revision: int = Field(strict=True, ge=0)
    base_url: str = Field(min_length=1, max_length=2048)
    service_key: SecretStr | None = Field(default=None, min_length=1, max_length=8192, repr=False)

    @field_validator("base_url")
    @classmethod
    def valid_url(cls, value):
        return TextAgentProfile.valid_url(value)

    @field_validator("service_key")
    @classmethod
    def valid_key(cls, value):
        return TextAgentProfile.valid_key(value) if value is not None else None


def cipher(settings):
    key = settings.text_service_encryption_key
    try:
        if key is not None:
            return Fernet(key.get_secret_value().encode("ascii"))
    except (ValueError, UnicodeError):
        pass
    raise TextModelError(
        public_message="服务凭据加密未配置或配置无效，请联系运维配置后重试。"
    )


def connection_row(session, *, lock=False):
    row = session.get(
        TextServiceConnection, "text", with_for_update=lock, populate_existing=True
    )
    if row is None:
        raise TextModelError(public_message="服务连接存储尚未准备好，请先完成数据库迁移。")
    return row


def connection_view(row):
    return TextServiceConnectionView(
        base_url=row.base_url,
        has_service_key=bool(row.key_ciphertext),
        revision=row.revision,
        updated_at=row.updated_at.replace(tzinfo=UTC) if row.updated_at else None,
    )


def read_service_connection(session, settings):
    row = connection_row(session)
    if not row.key_ciphertext:
        raise TextModelError(public_message="请先配置文本服务连接，再管理模型配置。")
    try:
        data = json.loads(cipher(settings).decrypt(row.key_ciphertext))
        if data["purpose"] != "text-service-connection" or data["base_url"] != row.base_url:
            raise ValueError()
        return TextModelService(base_url=row.base_url, service_key=data["service_key"])
    except (InvalidToken, ValueError, KeyError, TypeError):
        raise TextModelError(
            public_message="服务凭据无法解密，请检查服务器加密配置或重新设置服务密钥。"
        ) from None


def update_service_connection(session, settings, dto, actor_id):
    row = connection_row(session, lock=True)
    if row.revision != dto.expected_revision:
        raise TextModelError(
            409, public_message="服务连接已更新，草稿已保留，请载入最新连接后重试。"
        )
    encrypted = cipher(settings)
    if dto.service_key is None:
        if not row.key_ciphertext or row.base_url != dto.base_url:
            raise TextModelError(
                422, public_message="首次配置或更换服务地址时，请填写服务访问 Key。"
            )
        # Verify it still decrypts before accepting a blank-key update.
        read_service_connection(session, settings)
    else:
        row.key_ciphertext = encrypted.encrypt(json.dumps({
            "purpose": "text-service-connection", "base_url": dto.base_url,
            "service_key": dto.service_key.get_secret_value(),
        }).encode())
    if row.base_url != dto.base_url and getattr(row, "default_model_id", None) is not None:
        row.default_model_id = None
        row.default_revision += 1
    row.base_url = dto.base_url
    row.revision += 1
    row.updated_at = datetime.now(UTC).replace(tzinfo=None)
    row.updated_by = str(actor_id)
    return row
