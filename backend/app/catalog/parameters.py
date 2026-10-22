"""Versioned platform prices, locked through quotation validation and admission."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import ConfigDict, Field, SecretStr, field_validator

from app.audit.service import audit_admin
from app.catalog.models import ParameterConfig, ParameterHead
from app.common.types import DTO

Price = Annotated[int, Field(strict=True, ge=0, le=2**53 - 1)]


class ParameterConfigView(DTO):
    version: UUID | None
    text_price: Price | None
    image_price: Price | None
    video_price: Price | None
    assist_base_url: str | None = None
    assist_model: str | None = None
    has_assist_api_key: bool = False


class ParameterConfigUpdate(DTO):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    expected_version: UUID | None
    text_price: Price | None
    image_price: Price | None
    video_price: Price | None
    assist_base_url: str | None = Field(default=None, min_length=1, max_length=2048)
    assist_model: str | None = Field(default=None, min_length=1, max_length=200, pattern=r"\S")
    assist_api_key: SecretStr | None = Field(
        default=None, min_length=1, max_length=8192, repr=False,
    )

    @field_validator("assist_base_url")
    @classmethod
    def valid_url(cls, value):
        from app.assist.configuration import valid_assist_url

        return valid_assist_url(value) if value is not None else None

    @field_validator("assist_api_key")
    @classmethod
    def valid_key(cls, value):
        from app.agents.text import TextAgentProfile

        return TextAgentProfile.valid_key(value) if value is not None else None


def read_parameters(session, mode, *, write=False):
    head = session.get(
        ParameterHead, mode, with_for_update={"read": not write}, populate_existing=True
    )
    if head is None:
        raise HTTPException(503, detail="参数配置存储尚未准备好，请完成数据库迁移。")
    if head.version is None:
        return ParameterConfigView(
            version=None, text_price=None, image_price=None, video_price=None
        )
    row = session.get(
        ParameterConfig, head.version, with_for_update={"read": True}, populate_existing=True
    )
    if row is None or row.mode != mode:
        raise HTTPException(503)
    return ParameterConfigView(
        version=row.version,
        text_price=row.text_price,
        image_price=row.image_price,
        video_price=row.video_price,
        assist_base_url=row.assist_base_url,
        assist_model=row.assist_model,
        has_assist_api_key=bool(row.assist_key_ciphertext),
    )


def update_parameters(session, mode, dto, actor_id, *, settings=None):
    current = read_parameters(session, mode, write=True)
    if current.version != dto.expected_version:
        raise HTTPException(409, detail="参数配置已更新，请刷新并核对最新价格。")
    version = str(uuid4())
    values = dto.model_dump(include={"text_price", "image_price", "video_price"})
    previous = session.get(ParameterConfig, str(current.version)) if current.version else None
    from app.assist.configuration import updated_assist_fields

    assist = updated_assist_fields(previous, dto, mode, settings)
    session.add(ParameterConfig(version=version, mode=mode, **values, **assist))
    session.flush()
    head = session.get(ParameterHead, mode)
    head.version = version
    audit_admin(
        session,
        actor_id,
        "generation_parameters",
        version,
        "修改创作参数配置",
        values
        | {
            "version": version,
            "previous_version": str(current.version) if current.version else None,
            "secret_configured": bool(assist["assist_key_ciphertext"]),
        },
    )
    return ParameterConfigView(version=version, **values,
                               assist_base_url=assist["assist_base_url"],
                               assist_model=assist["assist_model"],
                               has_assist_api_key=bool(assist["assist_key_ciphertext"]))
