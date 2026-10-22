"""Adapter for ecommerce_copy_api 1.0. No automatic generation retries or fake streaming.

Only server-owned profiles select credentials and model configurations. Record queries
recover original content; the upstream API cannot query by Idempotency-Key.
"""

import base64
import hashlib
import json
import math
from collections.abc import Callable, Mapping
from io import BytesIO
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import UUID

from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from .contracts import (
    Capabilities,
    QueryOutcome,
    ResultItem,
    ResultManifest,
    ResultSource,
    SubmitOutcome,
    VerifiedEvent,
)
from .text_parameters import validate_text_parameters

PROTOCOL = "text-agent-v1"
DOWNLOAD_SOURCE = "text-agent-v1:bound-record"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_BYTES = 10 * 1024 * 1024


class TextAgentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    base_url: str
    service_key: SecretStr = Field(repr=False)
    model_config_id: UUID
    supports_images: bool = False
    timeout_seconds: float = Field(default=360, ge=310, le=600)

    @field_validator("base_url")
    @classmethod
    def valid_url(cls, value):
        parts = urlsplit(value)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or parts.path not in {"", "/"}
            or "\\" in value
            or any(ord(c) <= 32 or ord(c) == 127 for c in value)
        ):
            raise ValueError("Text service requires an exact HTTP(S) origin")
        _ = parts.port  # Invalid ports fail configuration before transmitting a credential.
        return value.rstrip("/")

    @field_validator("service_key")
    @classmethod
    def valid_key(cls, value):
        key = value.get_secret_value()
        if not key.strip() or any(ord(c) < 33 or ord(c) > 126 for c in key):
            raise ValueError("Invalid text service access key")
        return value


class TextAgentRouting(BaseModel):
    """Nonsecret immutable routing saved with the admitted task, never a browser field."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    protocol_version: str = PROTOCOL
    profile: str
    base_url: str
    model_config_id: UUID
    supports_images: bool


def validate_text_image(data, mime):
    if (
        not isinstance(data, bytes)
        or not 0 < len(data) <= MAX_IMAGE_BYTES
        or mime not in {"image/jpeg", "image/png", "image/webp"}
    ):
        raise ValueError("Unsupported text image")
    try:
        with Image.open(BytesIO(data)) as image:
            if (
                image.format
                != {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}[mime]
                or getattr(image, "n_frames", 1) != 1
                or image.width * image.height > 40_000_000
            ):
                raise ValueError("Text images must be static")
            image.verify()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise ValueError("Invalid text image") from error


def build_copy_request(
    snapshot: Mapping[str, Any],
    profile: TextAgentProfile,
    material_loader: Callable | None = None,
    *,
    validate_only=False,
):
    source = snapshot["input_snapshot"]
    product, parameters = source["product"], source["parameters"]
    validate_text_parameters(parameters)
    if not isinstance(product.get("name"), str) or not product["name"].strip():
        raise ValueError("Unsupported text input or parameters")
    points = product.get("selling_points", product.get("sellingPoints", []))
    if isinstance(points, str):
        points = [line.strip() for line in points.splitlines() if line.strip()]
    if not isinstance(points, list) or any(not isinstance(p, str) for p in points):
        raise ValueError("Invalid selling points")
    instructions = source.get("instruction", "")
    if not isinstance(instructions, str):
        raise ValueError("Copy instruction must be a string")
    extra = parameters.get("extra_instructions", "")
    if extra.strip():
        instructions = "\n".join(part for part in (
            instructions, "额外协作要求：" + extra,
        ) if part)
    maximum = parameters.get("max_chars")
    length = parameters.get("length")
    if maximum is None and type(length) is int:
        maximum = length
    elif length is not None:
        instructions += "\n文案长度要求：" + str(length)
    if maximum is not None and (type(maximum) is not int or maximum < 1):
        raise ValueError("Invalid text length")
    attributes = product.get("attributes", {})
    if not isinstance(attributes, dict):
        raise ValueError("Invalid product attributes")
    body = {
        "model_config_id": str(profile.model_config_id),
        "product": {
            "name": product["name"],
            "category": product.get("category", ""),
            "brand": product.get("brand", ""),
            "description": product.get("description", ""),
            "selling_points": points,
            "attributes": {
                **attributes,
                **{
                    k: v
                    for k, v in product.items()
                    if k
                    not in {
                        "name",
                        "category",
                        "brand",
                        "description",
                        "selling_points",
                        "sellingPoints",
                        "attributes",
                    }
                    and v != ""
                },
            },
        },
        "requirements": {
            "copy_type": parameters.get("copy_type", "宣传文案"),
            "platform": parameters.get("platform", ""),
            "audience": parameters.get("audience", product.get("audience", "")),
            "tone": parameters.get("tone", "自然"),
            "language": parameters.get("language", "简体中文"),
            "max_chars": maximum,
            "extra_instructions": instructions,
        },
        "images": [],
    }
    if any(
        not isinstance(body["product"][key], str)
        for key in ("name", "category", "brand", "description")
    ):
        raise ValueError("Product text fields must be strings")
    for key, value in body["product"]["attributes"].items():
        if not isinstance(key, str) or not (
            type(value) in {str, bool, int}
            or type(value) is float
            and math.isfinite(value)
            or isinstance(value, list)
            and all(isinstance(v, str) for v in value)
        ):
            raise ValueError("Invalid product attribute value")
    if any(
        not isinstance(value, str)
        for key, value in body["requirements"].items()
        if key != "max_chars"
    ):
        raise ValueError("Copy requirements must be strings")
    materials = source.get("material_versions", [])
    if len(materials) > 4 or materials and not profile.supports_images:
        raise ValueError("Text model does not support these materials")
    if validate_only:
        return body
    if materials and not material_loader:
        raise ValueError("Original task material loader unavailable")
    for material in materials:
        data, mime = material_loader(material)
        validate_text_image(data, mime)
        body["images"].append(
            {
                "kind": "bytes",
                "media_type": mime,
                "data": base64.urlsafe_b64encode(data).decode("ascii"),
            }
        )
    return body


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class TextAgentAdapter:
    agent_id = "copy"
    protocol_version = PROTOCOL
    test_only = False
    capabilities = Capabilities(
        sync="supported",
        async_="unsupported",
        stream="unsupported",
        final_text="supported",
        idempotent_submit="supported",
        query_external="unsupported",
        query_id="supported",
        callback="unsupported",
        original_result_recovery="supported",
    )

    def __init__(
        self, *, profile: TextAgentProfile, external_submission_id=None, material_loader=None
    ):
        self.profile = profile
        self.external_submission_id = external_submission_id
        self.material_loader = material_loader
        self.timeout = 10.0
        self.retry_after_seconds = 1

    @staticmethod
    def _id(value):
        return str(UUID(value))

    def _request(self, method, path, body=None, *, idempotency_key=None):
        headers = {
            "Authorization": "Bearer " + self.profile.service_key.get_secret_value(),
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        raw = None if body is None else json.dumps(body, allow_nan=False).encode()
        if raw and len(raw) > 60 * 1024 * 1024:
            raise ValueError("Text request exceeds size limit")
        request = Request(self.profile.base_url + path, data=raw, headers=headers, method=method)
        opener = build_opener(ProxyHandler({}), NoRedirects())
        try:
            response = opener.open(
                request,
                timeout=(self.profile.timeout_seconds if method == "POST" else self.timeout),
            )
        except HTTPError as error:
            response = error
        with response:
            if response.status == 429:
                try:
                    self.retry_after_seconds = max(1, min(3600, int(
                        response.headers.get("Retry-After", "1"))))
                except (ValueError, TypeError):
                    self.retry_after_seconds = 1
            status, data = response.status, response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise ValueError("Text response exceeds size limit")
        payload = json.loads(data)
        if not isinstance(payload, dict):
            raise ValueError("Invalid text response")
        return status, payload

    def retry_scope(self):
        # A configured routing scope permits the FIRST dispatch only. It is not an
        # authoritative absence/retry proof and cannot authorize a second POST.
        return {
            "instance_id": "text:"
            + hashlib.sha256(
                (self.profile.base_url + ":" + str(self.profile.model_config_id)).encode()
            ).hexdigest(),
            "protocol_version": PROTOCOL,
        }

    def submit_scoped(self, snapshot, external_submission_id, scope):
        if scope != self.retry_scope():
            return SubmitOutcome(status="UNKNOWN", protocol_version=PROTOCOL)
        return self.submit(snapshot, external_submission_id)

    def _identity(self, external=None, record_id=None):
        return dict(
            protocol_version=PROTOCOL,
            test_only=False,
            external_submission_id=external or self.external_submission_id,
            upstream_task_id=record_id,
        )

    @staticmethod
    def _text(result):
        text = result.get("text") if isinstance(result, dict) else None
        if (
            not isinstance(text, str)
            or not text.strip()
            or len(text.encode("utf-8")) > MAX_RESPONSE_BYTES
        ):
            raise ValueError("Incomplete text result")
        return text.encode("utf-8")

    @classmethod
    def _manifest(cls, record_id, result):
        data = cls._text(result)
        return ResultManifest(
            complete=True,
            expected_items=1,
            warnings=result.get("warnings", ()),
            items=(
                ResultItem(
                    item_key="original-1",
                    locator=f"/v1/copy/results/{record_id}",
                    media_type="text/plain",
                    sha256=hashlib.sha256(data).hexdigest(),
                    byte_length=len(data),
                ),
            ),
        )

    def submit(self, snapshot, external_submission_id):
        external = self._id(external_submission_id)
        fallback = self._identity(external)
        record_id = None
        try:
            body = build_copy_request(snapshot, self.profile, self.material_loader)
            status, payload = self._request(
                "POST", "/v1/copy/generate", body, idempotency_key=external
            )
            record_id = self._id(payload["record_id"]) if payload.get("record_id") else None
            if (status == 429 and not record_id
                    and payload.get("error", {}).get("code") == "concurrency_limit"):
                return SubmitOutcome(status="RATE_LIMITED", **fallback,
                                     retry_after_seconds=self.retry_after_seconds)
            if status == 200:
                if not record_id:
                    raise ValueError("Missing record identity")
                return SubmitOutcome(
                    status="COMPLETED",
                    **self._identity(external, record_id),
                    result=self._manifest(record_id, payload.get("result")),
                )
            if record_id and payload.get("error", {}).get("code") != "idempotency_conflict":
                # Even persistence errors may have incurred model costs. Query the
                # original record rather than infer failure from HTTP status alone.
                return SubmitOutcome(status="ACCEPTED", **self._identity(external, record_id))
            return SubmitOutcome(status="UNKNOWN", **fallback)
        except (URLError, OSError, ValueError, TypeError, KeyError):
            if record_id:
                return SubmitOutcome(status="ACCEPTED", **self._identity(external, record_id))
            return SubmitOutcome(status="UNKNOWN", **fallback)

    def query_by_external(self, external_submission_id):
        return QueryOutcome(status="UNSUPPORTED", **self._identity(external_submission_id))

    def _record(self, record_id):
        record_id = self._id(record_id)
        status, payload = self._request("GET", f"/v1/call-records/{record_id}")
        if status != 200:
            return status, payload
        if payload.get("id") != record_id or payload.get("model_config_id") != str(
            self.profile.model_config_id
        ):
            raise ValueError("Record identity mismatch")
        return status, payload

    def query(self, upstream_task_id):
        fallback = self._identity(record_id=upstream_task_id)
        try:
            status, payload = self._record(upstream_task_id)
            if status == 404:
                return QueryOutcome(status="NOT_FOUND", **fallback)
            if status != 200 or payload.get("content_expired"):
                return QueryOutcome(status="UNAVAILABLE", **fallback)
            state = payload.get("status")
            if state == "succeeded":
                return QueryOutcome(
                    status="FOUND",
                    state="RESULT_READY",
                    **fallback,
                    result=self._manifest(upstream_task_id, payload.get("result_json")),
                )
            if state == "running":
                return QueryOutcome(status="FOUND", state="RUNNING", **fallback)
            if state == "failed":
                return QueryOutcome(status="FOUND", state="FAILED", **fallback)
            # Interrupted or unknown records require investigation, never a new generation.
            return QueryOutcome(status="UNAVAILABLE", **fallback)
        except (URLError, OSError, ValueError, TypeError, KeyError):
            return QueryOutcome(status="UNAVAILABLE", **fallback)

    def retrieve_original(self, locator):
        fallback = dict(protocol_version=PROTOCOL, test_only=False, locator=locator)
        prefix = "/v1/copy/results/"
        try:
            if not locator.startswith(prefix):
                return ResultSource(status="UNSUPPORTED", **fallback)
            record_id = self._id(locator[len(prefix) :])
            if locator != prefix + record_id:
                return ResultSource(status="UNSUPPORTED", **fallback)
            status, payload = self._record(record_id)
            if status == 404:
                return ResultSource(status="NOT_FOUND", **fallback)
            if payload.get("content_expired"):
                return ResultSource(status="EXPIRED", **fallback)
            if status != 200 or payload.get("status") != "succeeded":
                return ResultSource(status="UNAVAILABLE", **fallback)
            data = self._text(payload.get("result_json"))
            return ResultSource(
                status="AVAILABLE",
                complete=True,
                content=data,
                media_type="text/plain",
                byte_length=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                **fallback,
            )
        except (URLError, OSError, ValueError, TypeError, KeyError):
            return ResultSource(status="UNAVAILABLE", **fallback)

    def verify_callback(self, raw, headers):
        return VerifiedEvent(status="UNSUPPORTED", protocol_version=PROTOCOL, test_only=False)
