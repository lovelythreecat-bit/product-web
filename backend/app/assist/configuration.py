"""Independent encrypted model connection for draft assistance only."""

import ipaddress
import json
from urllib.parse import urlsplit
from uuid import UUID

from cryptography.fernet import InvalidToken
from fastapi import HTTPException
from pydantic import ConfigDict, Field, SecretStr

from app.agents.service_connection import cipher
from app.agents.text import TextAgentProfile
from app.catalog.models import ParameterConfig, ParameterHead
from app.common.types import DTO


def valid_assist_url(value):
    parts = urlsplit(value)
    if (parts.scheme not in {"http", "https"} or not parts.hostname
            or parts.username or parts.password or parts.query or parts.fragment
            or "\\" in value or any(ord(c) <= 32 or ord(c) == 127 for c in value)
            or any(segment in {".", ".."} for segment in parts.path.split("/"))
            or "%" in parts.netloc or "%" in parts.path):
        raise ValueError("Use an HTTP(S) API base URL without credentials or query")
    _ = parts.port
    # Explicit admin-managed local/private model gateways remain supported, as
    # with textAgent. Link-local metadata and unspecified/multicast targets do not.
    try:
        address = ipaddress.ip_address(parts.hostname)
    except ValueError:
        address = None
    if address is not None and (
        address.is_link_local or address.is_unspecified or address.is_multicast
        or (address.version == 6 and address.ipv4_mapped is not None
            and address.ipv4_mapped.is_link_local)
    ):
        raise ValueError("Unsupported model endpoint")
    if parts.hostname.lower().rstrip(".") in {"metadata.google.internal", "metadata"}:
        raise ValueError("Unsupported model endpoint")
    return value.rstrip("/")


class AssistConnection(DTO):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    version: UUID
    base_url: str
    model: str
    api_key: SecretStr = Field(repr=False)


def decode_connection(row, settings):
    try:
        data = json.loads(cipher(settings).decrypt(row.assist_key_ciphertext))
        if (data["purpose"] != "prompt-assist-model" or data["mode"] != row.mode
                or data["base_url"] != row.assist_base_url
                or data["model"] != row.assist_model):
            raise ValueError()
        valid_assist_url(row.assist_base_url)
        return AssistConnection(version=row.version, base_url=row.assist_base_url,
                                model=row.assist_model, api_key=data["api_key"])
    except (InvalidToken, ValueError, KeyError, TypeError):
        raise HTTPException(503) from None


def read_assist_connection(session, settings, *, required=True):
    head = session.get(ParameterHead, settings.mode, with_for_update={"read": True},
                       populate_existing=True)
    row = session.get(ParameterConfig, head.version, with_for_update={"read": True},
                      populate_existing=True) if head and head.version else None
    if row is None or not any((row.assist_base_url, row.assist_model, row.assist_key_ciphertext)):
        if not required:
            return None
        raise HTTPException(503)
    if (row.mode != settings.mode or not row.assist_base_url
            or not row.assist_model or not row.assist_key_ciphertext):
        raise HTTPException(503)
    return decode_connection(row, settings)


def updated_assist_fields(previous, dto, mode, settings):
    fields = dto.model_fields_set
    base_url = (dto.assist_base_url if "assist_base_url" in fields
                else getattr(previous, "assist_base_url", None))
    model = (dto.assist_model if "assist_model" in fields
             else getattr(previous, "assist_model", None))
    previous_ciphertext = getattr(previous, "assist_key_ciphertext", None)
    if base_url is None and model is None:
        if dto.assist_api_key is not None:
            raise HTTPException(422)
        return dict(assist_base_url=None, assist_model=None, assist_key_ciphertext=None)
    if not base_url or not model:
        raise HTTPException(422)
    if dto.assist_api_key is None:
        if not previous_ciphertext or base_url != previous.assist_base_url:
            raise HTTPException(422)
        key = decode_connection(previous, settings).api_key
    else:
        key = TextAgentProfile.valid_key(dto.assist_api_key)
    payload = dict(purpose="prompt-assist-model", mode=mode, base_url=base_url,
                   model=model, api_key=key.get_secret_value())
    return dict(assist_base_url=base_url, assist_model=model,
                assist_key_ciphertext=cipher(settings).encrypt(json.dumps(payload).encode()))
