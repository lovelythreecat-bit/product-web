"""Immutable encrypted platform-to-media connections, including historical routing."""

import json
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from cryptography.fernet import Fernet, InvalidToken
from pydantic import ConfigDict, Field, SecretStr
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.agents.media_http import MediaServiceError
from app.common.types import DTO
from app.db import Base


class MediaConnectionRecord(Base):
    __tablename__ = "media_service_connections"
    __table_args__ = (
        CheckConstraint("kind IN ('image','video')", name="ck_media_connection_kind"),
        CheckConstraint("revision > 0", name="ck_media_connection_revision"),
        UniqueConstraint("kind", "revision", name="uq_media_connection_revision"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    revision: Mapped[int] = mapped_column(Integer)
    base_url: Mapped[str] = mapped_column(String(2048))
    key_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    has_management_key: Mapped[bool] = mapped_column(Boolean)
    default_config_id: Mapped[str | None] = mapped_column(String(36))
    image_model: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class MediaConnectionHead(Base):
    __tablename__ = "media_service_connection_heads"
    __table_args__ = (
        CheckConstraint("kind IN ('image','video')", name="ck_media_connection_head_kind"),
    )
    kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    connection_id: Mapped[str | None] = mapped_column(ForeignKey("media_service_connections.id"))
    revision: Mapped[int] = mapped_column(Integer, default=0)


class MediaConnection(DTO):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    id: UUID
    kind: Literal["image", "video"]
    base_url: str
    service_key: SecretStr = Field(repr=False)
    management_key: SecretStr | None = Field(default=None, repr=False)
    default_config_id: UUID | None = None
    image_model: str | None = None
    video_audio_enabled: bool = False


def _cipher(settings):
    try:
        return Fernet(settings.text_service_encryption_key.get_secret_value().encode("ascii"))
    except (AttributeError, ValueError, UnicodeError):
        raise MediaServiceError(public_message="服务凭据加密未配置或配置无效。") from None


def connection_head(session, kind, *, lock=False):
    if kind not in {"image", "video"}:
        raise MediaServiceError(404)
    head = session.get(MediaConnectionHead, kind, with_for_update=lock, populate_existing=True)
    if head is None:
        raise MediaServiceError(public_message="媒体连接存储尚未准备好，请先完成数据库迁移。")
    return head


def read_media_connection(session, settings, kind, connection_id=None):
    if connection_id is None:
        connection_id = connection_head(session, kind).connection_id
    row = session.get(MediaConnectionRecord, str(connection_id)) if connection_id else None
    if row is None or row.kind != kind:
        raise MediaServiceError(public_message="请先配置媒体服务连接。")
    try:
        data = json.loads(_cipher(settings).decrypt(row.key_ciphertext))
        if (
            data["purpose"] != "media-service-connection"
            or data["id"] != row.id
            or data["kind"] != kind
            or data["base_url"] != row.base_url
        ):
            raise ValueError()
        return MediaConnection(
            id=row.id,
            kind=kind,
            base_url=row.base_url,
            service_key=data["service_key"],
            management_key=data.get("management_key"),
            default_config_id=row.default_config_id,
            image_model=row.image_model,
            video_audio_enabled=data.get("video_audio_enabled", False),
        )
    except (InvalidToken, ValueError, KeyError, TypeError):
        raise MediaServiceError(public_message="服务凭据无法解密，请检查加密配置。") from None


def connection_view(row=None, *, kind=None):
    from app.admin.media_schemas import MediaConnectionView

    return MediaConnectionView(
        id=row.id if row else None,
        kind=row.kind if row else kind,
        base_url=row.base_url if row else None,
        revision=row.revision if row else 0,
        has_service_key=bool(row and row.key_ciphertext),
        has_management_key=bool(row and row.has_management_key),
        default_config_id=row.default_config_id if row else None,
        image_model=row.image_model if row else None,
    )


def current_connection_view(session, settings, kind):
    head = connection_head(session, kind)
    if not head.connection_id:
        return connection_view(kind=kind)
    row = session.get(MediaConnectionRecord, head.connection_id)
    if row is None or row.kind != kind:
        raise MediaServiceError()
    return connection_view(row)


def update_media_connection(session, settings, kind, dto, actor_id):
    head = connection_head(session, kind, lock=True)
    if head.revision != dto.expected_revision:
        raise MediaServiceError(409, "服务连接已更新，草稿已保留，请重新打开编辑。")
    previous = (
        session.get(MediaConnectionRecord, head.connection_id) if head.connection_id else None
    )
    base_url = dto.base_url or (previous.base_url if previous else None)
    origin_changed = previous is None or previous.base_url != base_url
    if not base_url or (origin_changed and dto.service_key is None):
        raise MediaServiceError(422, "首次配置或更换服务地址时，请填写新的服务访问 Key。")
    if origin_changed and previous and previous.has_management_key and dto.management_key is None:
        raise MediaServiceError(422, "更换服务地址时，请填写新的管理访问 Key。")
    if kind == "image" and dto.management_key is not None:
        raise MediaServiceError(422)
    if kind == "image" and dto.video_audio_enabled is not None:
        raise MediaServiceError(422)
    if kind == "video" and (dto.default_config_id is not None or dto.image_model is not None):
        raise MediaServiceError(422)
    needs_original = dto.service_key is None or (
        previous and previous.has_management_key and dto.management_key is None
    )
    original = read_media_connection(session, settings, kind) if needs_original else None
    if original is None and previous is not None and not origin_changed:
        try:
            original = read_media_connection(session, settings, kind)
        except MediaServiceError:
            # Full key replacement must still recover from an unavailable old
            # encryption key. Unknown audio preferences safely reset to silent.
            pass
    secret = dto.service_key or original.service_key
    management = dto.management_key or (original.management_key if original else None)
    identity = str(uuid4())
    payload = {
        "purpose": "media-service-connection",
        "id": identity,
        "kind": kind,
        "base_url": base_url,
        "service_key": secret.get_secret_value(),
        "management_key": management.get_secret_value() if management else None,
        "video_audio_enabled": (dto.video_audio_enabled if dto.video_audio_enabled is not None
                                else original.video_audio_enabled if original and not origin_changed
                                else False),
    }
    fields = dto.model_fields_set
    default_config = (
        (str(dto.default_config_id) if dto.default_config_id else None)
        if "default_config_id" in fields
        else (
            str(previous.default_config_id)
            if previous and previous.default_config_id and not origin_changed
            else None
        )
    )
    alias = (
        dto.image_model
        if "image_model" in fields
        else (previous.image_model if previous and not origin_changed else None)
    )
    row = MediaConnectionRecord(
        id=identity,
        kind=kind,
        revision=head.revision + 1,
        base_url=base_url,
        key_ciphertext=_cipher(settings).encrypt(json.dumps(payload).encode()),
        has_management_key=management is not None,
        default_config_id=default_config,
        image_model=alias,
        created_at=datetime.now(UTC).replace(tzinfo=None),
        created_by=str(actor_id),
    )
    session.add(row)
    session.flush()
    head.connection_id, head.revision = identity, row.revision
    session.flush()
    return row
