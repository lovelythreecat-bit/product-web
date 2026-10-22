"""Image service v1: fixed inputs, durable upload bindings and original-only recovery.

The first dispatch scope is not absence evidence. An unknown POST or upload is
never repeated automatically; completed tasks still require every target's audit.
"""

import hashlib
import json
import math
import re
from collections.abc import Mapping
from io import BytesIO
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.catalog.schemas import content_digest

from .contracts import (
    Capabilities,
    QueryOutcome,
    ResultItem,
    ResultManifest,
    ResultSource,
    SubmitOutcome,
    VerifiedEvent,
)
from .media_http import MediaClient, MediaServiceError

PROTOCOL = "image-agent-v1"
DOWNLOAD_SOURCE = "image-agent:bound-service"
PLATFORMS = frozenset(
    {"amazon", "taobao", "tmall", "jd", "pinduoduo", "shopee", "lazada", "shein", "temu"}
)
OUTPUT_TYPES = frozenset({"main_image", "detail_page", "pdd_white_background", "long_image"})
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
_MIMES = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
_SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,160}\Z")
_SAFE_ASSET_ID = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,159}\Z")


def _identifier(value):
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError("Invalid image service identifier")
    return value


def _asset_identifier(value):
    # Upstream target keys, e.g. taobao.main_image.default, are also blob IDs.
    # Only a single unescaped path segment is allowed; task/media IDs stay strict.
    if not isinstance(value, str) or not _SAFE_ASSET_ID.fullmatch(value):
        raise ValueError("Invalid image asset identifier")
    return value


class ImageAgentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    base_url: str
    service_key: SecretStr = Field(repr=False)
    agent_config_id: str = Field(min_length=1, max_length=36)
    image_model: Literal["pro", "fast", "base"] = "pro"
    max_result_bytes: int = Field(default=60 * 1024 * 1024, strict=True, ge=1, le=512 * 1024 * 1024)

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
            raise ValueError("Image service requires an exact HTTP(S) origin")
        _ = parts.port
        return value.rstrip("/")

    @field_validator("service_key")
    @classmethod
    def valid_key(cls, value):
        raw = value.get_secret_value()
        if not raw or any(ord(c) < 33 or ord(c) > 126 for c in raw):
            raise ValueError("Invalid image service access key")
        return value

    @field_validator("agent_config_id")
    @classmethod
    def valid_config(cls, value):
        return _identifier(value)


def validate_image_content(data: bytes, media_type: str, *, max_bytes: int) -> str:
    """Verify actual static image decoding, MIME and bounded encoded/pixel size."""
    if not isinstance(data, bytes) or not 0 < len(data) <= max_bytes or media_type not in _MIMES:
        raise ValueError("Unsupported image bytes or MIME")
    try:
        with Image.open(BytesIO(data)) as image:
            if (
                image.format != _MIMES[media_type]
                or getattr(image, "n_frames", 1) != 1
                or image.width * image.height > 60_000_000
            ):
                raise ValueError("Image format or dimensions invalid")
            image.verify()
        # verify() checks the container; decoding also rejects a corrupt pixel stream.
        with Image.open(BytesIO(data)) as image:
            image.load()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise ValueError("Invalid image content") from error
    return media_type


def expected_image_targets(snapshot_or_request) -> tuple[tuple[str, str, str], ...]:
    """Derive delivery count/identities from original choices, never returned assets."""
    source = snapshot_or_request
    if "input_snapshot" in source:
        params = source["input_snapshot"]["parameters"]
        platforms, outputs = [params.get("platform")], [params.get("output_type")]
    else:
        source = source.get("request", source)
        platforms, outputs = source.get("platforms"), source.get("output_types")
    if (
        not isinstance(platforms, list)
        or len(platforms) != 1
        or not isinstance(outputs, list)
        or len(outputs) != 1
        or platforms[0] not in PLATFORMS
        or outputs[0] not in OUTPUT_TYPES
    ):
        raise ValueError("Select one supported image platform and output type")
    variants = ("scene", "feature", "closeup") if outputs[0] == "detail_page" else ("default",)
    return tuple((platforms[0], outputs[0], v) for v in variants)


def image_item_key(target) -> str:
    return "-".join(target)


def _material_key(material):
    if not isinstance(material, Mapping):
        raise ValueError("Invalid image material reference")
    file_id, version = material.get("file_id"), material.get("version")
    if not isinstance(file_id, str) or not file_id or not isinstance(version, str) or not version:
        raise ValueError("Invalid image material identity/version")
    return file_id + ":" + version


def build_image_request(snapshot, profile, uploads=None, validate_only=False):
    source = snapshot["input_snapshot"]
    product, params = source["product"], source["parameters"]
    if not isinstance(params, dict) or params.keys() - {"platform", "output_type"}:
        raise ValueError("Unsupported image parameters")
    expected_image_targets(snapshot)
    if any(
        not isinstance(product.get(k), str) or not product[k].strip() for k in ("name", "category")
    ):
        raise ValueError("Image creation requires product name and category")
    instruction = source.get("instruction", "")
    if not isinstance(instruction, str):
        raise ValueError("Image instruction must be text")
    materials = source.get("material_versions", [])
    if not isinstance(materials, list) or not 1 <= len(materials) <= 8:
        raise ValueError("Image creation requires 1–8 materials")
    keys = [_material_key(m) for m in materials]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate image materials")
    # Explicitly label facts and original instruction; no inferred product facts.
    brief = json.dumps(
        {"product_facts": product, "user_instruction": instruction},
        ensure_ascii=False,
        allow_nan=False,
    )
    request = {
        "schema_version": "1.0",
        "product_name": product["name"].strip(),
        "category": product["category"].strip(),
        "platforms": [params["platform"]],
        "output_types": [params["output_type"]],
        "image_model": profile.image_model,
        "creative_brief": brief,
        "materials": [],
        "selection": {"mode": "auto"},
    }
    if params["output_type"] == "long_image":
        # These are real upstream schema defaults; no marketing copy is invented.
        request["long_image"] = {
            "width": 750,
            "segment_count": 6,
            "segment_aspect_ratio": "3:4",
            "known_info": "",
            "required_copy": [],
        }
    if not validate_only:
        for index, key in enumerate(keys, 1):
            uploaded = (uploads or {}).get(key)
            if not isinstance(uploaded, dict):
                raise ValueError("Original material upload binding unavailable")
            request["materials"].append(
                {
                    "material_id": f"material-{index}",
                    "media_id": _identifier(uploaded.get("media_id")),
                    "role_hint": "auto",
                }
            )
    return {"kind": "create_images", "agent_config_id": profile.agent_config_id, "request": request}


class ImageAgentAdapter:
    agent_id = "image"
    protocol_version = PROTOCOL
    test_only = False
    capabilities = Capabilities(
        sync="unsupported",
        async_="supported",
        stream="unsupported",
        final_text="unsupported",
        idempotent_submit="supported",
        query_external="unsupported",
        query_id="supported",
        callback="unsupported",
        original_result_recovery="supported",
    )

    def __init__(
        self,
        *,
        profile,
        external_submission_id=None,
        material_loader=None,
        load_state=None,
        save_state=None,
        authorize_submission_retry=None,
    ):
        self.profile = profile
        self.external_submission_id = external_submission_id
        self.material_loader = material_loader
        self.load_state, self.save_state = load_state, save_state
        self.authorize_submission_retry = authorize_submission_retry
        self.client = MediaClient(
            profile.base_url,
            profile.service_key,
            timeout=30,
            max_response_bytes=profile.max_result_bytes,
        )

    def _identity(self, external=None, task_id=None):
        return dict(
            protocol_version=PROTOCOL,
            test_only=False,
            external_submission_id=external or self.external_submission_id,
            upstream_task_id=task_id,
        )

    def retry_scope(self):
        return {
            "instance_id": "image:"
            + hashlib.sha256(
                (self.profile.base_url + ":" + self.profile.agent_config_id).encode()
            ).hexdigest(),
            "protocol_version": PROTOCOL,
        }

    def submit_scoped(self, snapshot, external_submission_id, scope):
        if scope != self.retry_scope():
            return SubmitOutcome(status="UNKNOWN", **self._identity(external_submission_id))
        return self.submit(snapshot, external_submission_id)

    def submit(self, snapshot, external_submission_id):
        fallback = self._identity(external_submission_id)
        if not self.load_state or not self.save_state:
            return SubmitOutcome(status="UNSUPPORTED", **fallback)
        try:
            external = _identifier(external_submission_id)
            state = self.load_state()
            if state.get("external_submission_id", external) != external:
                raise ValueError("Image execution identity mismatch")
            if state.get("scope", self.retry_scope()) != self.retry_scope():
                raise ValueError("Image service scope mismatch")
            if state.get("upstream_task_id"):
                return SubmitOutcome(
                    status="ACCEPTED",
                    **self._identity(external, _identifier(state["upstream_task_id"])),
                )
            if state.get("upload_in_flight"):
                return SubmitOutcome(status="UNKNOWN", **fallback)
            if state.get("submission_started") and (
                not self.authorize_submission_retry or not self.authorize_submission_retry()
            ):
                return SubmitOutcome(status="UNKNOWN", **fallback)
            build_image_request(snapshot, self.profile, validate_only=True)
            self.save_state({"external_submission_id": external, "scope": self.retry_scope()})
            body = state.get("request_body")
            if body is None:
                uploads = dict(state.get("uploads", {}))
                references = snapshot["input_snapshot"]["material_versions"]
                loaded = self.material_loader() if self.material_loader else None
                if (
                    not isinstance(loaded, list)
                    or len(loaded) != len(references)
                    or [_material_key(m) for m in loaded] != [_material_key(m) for m in references]
                ):
                    raise ValueError("Original task material loader binding mismatch")
                for reference, material in zip(references, loaded, strict=True):
                    key = _material_key(material)
                    data, mime = material["content"], material["media_type"]
                    validate_image_content(data, mime, max_bytes=MAX_UPLOAD_BYTES)
                    digest = hashlib.sha256(data).hexdigest()
                    if digest != material["sha256"] or reference.get("sha256", digest) != digest:
                        raise ValueError("Original material digest mismatch")
                    if key not in uploads:
                        self.save_state({"upload_in_flight": key})
                        uploaded = self.client.upload("/api/v1/media", data, mime)
                        if (
                            uploaded.get("sha256") != digest
                            or uploaded.get("byte_size") != len(data)
                            or uploaded.get("mime_type") != mime
                        ):
                            raise ValueError("Image upload response integrity mismatch")
                        _identifier(uploaded.get("media_id"))
                        uploads[key] = uploaded
                        self.save_state({"uploads": uploads, "upload_in_flight": None})
                    elif (
                        uploads[key].get("sha256") != digest
                        or uploads[key].get("mime_type") != mime
                        or uploads[key].get("byte_size") != len(data)
                    ):
                        raise ValueError("Saved image upload binding mismatch")
                body = build_image_request(snapshot, self.profile, uploads)
                self.save_state({"request_body": body})
            elif body != build_image_request(snapshot, self.profile, state.get("uploads")):
                raise ValueError("Original image submission body mismatch")
            # Commit intent before POST; no automatic replay when its response is lost.
            # Each wire attempt consumes the previous rejection proof before POST.
            # A crash or lost response can therefore never reuse an earlier 429.
            attempt_id = str(uuid4())
            self.save_state({
                "submission_started": True,
                "submission_attempt_id": attempt_id,
                "submission_rejection": None,
            })
            try:
                status, payload = self.client.json(
                    "POST", "/api/v1/tasks", body, idempotency_key=external
                )
            except MediaServiceError as error:
                if not (
                    error.status_code == 429
                    and getattr(error, "error_code", None) == "queue_full"
                    and getattr(error, "retryable_rejection", False) is True
                    and getattr(error, "resource_id", None) is None
                ):
                    raise
                delay = getattr(error, "retry_after_seconds", None)
                if type(delay) is not int or not 1 <= delay <= 3600:
                    delay = 5
                self.save_state({"submission_rejection": {
                    "attempt_id": attempt_id,
                    "error_code": "queue_full",
                    "external_submission_id": external,
                    "scope": self.retry_scope(),
                    "request_body_digest": content_digest(body),
                    "retry_after_seconds": delay,
                }})
                return SubmitOutcome(
                    status="RATE_LIMITED", retry_after_seconds=delay, **fallback,
                )
            if status != 202:
                return SubmitOutcome(status="UNKNOWN", **fallback)
            task_id = _identifier(payload.get("task_id"))
            self.save_state(
                {
                    "upstream_task_id": task_id,
                    "status": payload.get("status"),
                    "core_status": payload.get("core_status"),
                    "config_versions": payload.get("config_versions", {}),
                }
            )
            return SubmitOutcome(status="ACCEPTED", **self._identity(external, task_id))
        except (MediaServiceError, OSError, ValueError, TypeError, KeyError):
            return SubmitOutcome(status="UNKNOWN", **fallback)

    def query_by_external(self, external_submission_id):
        return QueryOutcome(status="UNSUPPORTED", **self._identity(external_submission_id))

    @staticmethod
    def _metadata(result):
        return {
            "status": result.get("status"),
            "assets": [
                {
                    k: a.get(k)
                    for k in (
                        "asset_id",
                        "platform",
                        "output_type",
                        "variant",
                        "status",
                        "blob_id",
                        "mime_type",
                        "byte_length",
                    )
                }
                | {"quality_passed": (a.get("quality") or {}).get("passed"),
                   "delivery": a.get("delivery"),
                   "long_image_review": a.get("long_image_review")}
                for a in result.get("assets", [])
            ],
            "detail_set_audits": [
                {"platform": a.get("platform"), "passed": a.get("passed")}
                for a in result.get("detail_set_audits", [])
            ],
        }

    def _manifest(self, task_id, body, result):
        # imageAgent retired input_check; it is no longer a delivery prerequisite.
        if (
            result.get("status") != "succeeded"
            or result.get("error_info")
            or result.get("output_errors")
            or result.get("issues")
        ):
            raise ValueError("Image result requires review")
        targets = expected_image_targets(body)
        assets = result.get("assets")
        if not isinstance(assets, list) or len(assets) != len(targets):
            raise ValueError("Image delivery target count mismatch")
        mapped, asset_ids, blobs = {}, set(), set()
        warnings = result.get('warnings') or []
        if not isinstance(warnings, list) or any(not isinstance(w, str) for w in warnings):
            raise ValueError('Invalid image warnings')
        warnings = list(warnings)
        for asset in assets:
            target = (
                asset.get("platform"),
                asset.get("output_type"),
                asset.get("variant") or "default",
            )
            quality = asset.get("quality") or {}
            delivery = asset.get('delivery')
            if target[1] == 'long_image':
                from .image_long import validate_long_image_review

                validate_long_image_review(asset, body)
            if delivery is not None:
                self._validate_best_delivery(asset, delivery)
            if (
                target not in targets
                or target in mapped
                or asset.get("status") != "succeeded"
                or asset.get("error_info")
                or asset.get("error")
                or (delivery is None and target[1] != 'long_image' and (
                    quality.get("passed") is not True
                    or quality.get("failed_checks")
                    or quality.get("critical_failed_checks")
                    or (quality.get("deterministic_checks") or {}).get("passed") is not True
                ))
            ):
                raise ValueError("Image asset is incomplete or unapproved")
            asset_id = _asset_identifier(asset.get("asset_id"))
            blob = _asset_identifier(asset.get("blob_id"))
            if asset_id in asset_ids or blob in blobs:
                raise ValueError("Duplicate image asset/blob identity")
            asset_ids.add(asset_id)
            blobs.add(blob)
            mapped[target] = asset
        sizes = [a.get("byte_length") for a in mapped.values()]
        if (
            any(type(size) is not int or size < 1 for size in sizes)
            or sum(sizes) > self.profile.max_result_bytes
        ):
            raise ValueError("Image declared delivery exceeds total size limit")
        if targets[0][1] == "detail_page":
            audits = result.get("detail_set_audits", [])
            direct = all((a.get('delivery') or {}).get('mode') == 'direct'
                         for a in mapped.values())
            if (
                not direct and (len(audits) != 1
                or audits[0].get("platform") != targets[0][0]
                )
            ):
                raise ValueError("Image detail set audit missing")
            if not direct and (audits[0].get('passed') is not True or audits[0].get('error')
                    or audits[0].get('error_info')):
                warnings.append('详情组图审核未通过或未完成，已交付完整图片。')
        items, total = [], 0
        for target in targets:
            asset = mapped[target]
            locator = f"/api/v1/tasks/{task_id}/blobs/{asset['blob_id']}"
            data, mime = self.client.download(locator)
            validate_image_content(data, mime, max_bytes=self.profile.max_result_bytes)
            if target[1] == 'long_image':
                review = asset['long_image_review']
                with Image.open(BytesIO(data)) as image:
                    if (image.size != (review['width'], review['height'])
                            or hashlib.sha256(data).hexdigest() != review['sha256']):
                        raise ValueError('Long image bytes do not match composition review')
            total += len(data)
            if (
                total > self.profile.max_result_bytes
                or mime != asset.get("mime_type")
                or type(asset.get("byte_length")) is not int
                or len(data) != asset["byte_length"]
                or (asset.get('delivery') is not None
                    and hashlib.sha256(data).hexdigest() != asset['delivery']['sha256'])
            ):
                raise ValueError("Image result content/total size mismatch")
            items.append(
                ResultItem(
                    item_key=image_item_key(target),
                    locator=locator,
                    media_type=mime,
                    byte_length=len(data),
                    sha256=hashlib.sha256(data).hexdigest(),
                )
            )
        return ResultManifest(complete=True, expected_items=len(targets), items=tuple(items),
                              warnings=tuple(dict.fromkeys(warnings)))

    @staticmethod
    def _validate_best_delivery(asset, delivery):
        if (not isinstance(delivery, dict)
                or delivery.get('mode') not in {'best_available', 'direct'}):
            raise ValueError('Unknown image delivery decision')
        _identifier(delivery.get('candidate_id'))
        if not re.fullmatch(r'[a-f0-9]{64}', str(delivery.get('sha256', ''))):
            raise ValueError('Invalid selected image digest')
        score = delivery.get('score')
        if (score is not None and (type(score) not in (int, float)
                                  or not math.isfinite(score) or not 0 <= score <= 100)):
            raise ValueError('Invalid selected image score')
        candidates = asset.get('candidates')
        if not isinstance(candidates, list):
            raise ValueError('Selected image has no candidate provenance')
        selected = [c for c in candidates if isinstance(c, dict)
                    and c.get('candidate_id') == delivery['candidate_id']]
        if len(selected) != 1 or selected[0].get('status') in (None, 'stage'):
            raise ValueError('Selected image is not a final candidate')
        if delivery['mode'] == 'direct' and (
            selected[0].get('status') != 'succeeded' or score is not None
            or asset.get('quality') is not None
        ):
            raise ValueError('Direct delivery must be a completed unscored image')

    def query(self, upstream_task_id):
        return self._query(upstream_task_id)

    def query_for_owner_retry(self, upstream_task_id):
        """Explicit owner action only; never turn an automatic poll into a retry."""
        return self._query(upstream_task_id, owner_retry=True)

    def _query(self, upstream_task_id, *, owner_retry=False):
        fallback = self._identity(task_id=upstream_task_id)
        try:
            task_id = _identifier(upstream_task_id)
            state = self.load_state() if self.load_state else {}
            if (
                not self.save_state
                or state.get("upstream_task_id") != task_id
                or state.get("scope") != self.retry_scope()
            ):
                raise ValueError("Unknown original image task")
            status, task = self.client.json("GET", f"/api/v1/tasks/{task_id}")
            if status != 200 or task.get("task_id") != task_id:
                raise ValueError("Original image task unavailable")
            self.save_state(
                {
                    "status": task.get("status"),
                    "core_status": task.get("core_status"),
                    "config_versions": task.get("config_versions", {}),
                }
            )
            if task.get("status") in {"queued", "running"}:
                return QueryOutcome(status="FOUND", state="RUNNING", **fallback)
            if (task.get("status") != "completed"
                    or task.get("core_status") not in {"succeeded", "failed", "needs_input"}):
                return QueryOutcome(status="UNAVAILABLE", **fallback)
            status, result = self.client.json("GET", f"/api/v1/tasks/{task_id}/result")
            if status != 200:
                raise ValueError("Original image result unavailable")
            self.save_state({"result_metadata": self._metadata(result)})
            if task.get("core_status") == "needs_input":
                if result.get("status") == "needs_input":
                    usage = result.get("usage") or {}
                    if (owner_retry and result.get("assets") == []
                            and type(usage.get("image_calls")) is int
                            and usage["image_calls"] == 0):
                        self.save_state({"failure": {
                            "code": "owner_retry_stopped_input", "stage": "analyze_materials",
                            "retryable": True,
                            "message": "原图片任务已停止且未调用图片生成，用户选择使用原资料重试",
                        }})
                        return QueryOutcome(status="FOUND", state="FAILED", **fallback)
                    return QueryOutcome(status="NEEDS_INPUT",
                                        diagnostic_reason="UPSTREAM_NEEDS_INPUT", **fallback)
                return QueryOutcome(status="UNAVAILABLE", **fallback)
            if task.get("core_status") == "failed":
                usage, error = result.get("usage") or {}, result.get("error_info") or {}
                # A failed analysis with zero image requests is definite failure.
                # Generated/partial/uncertain results still require investigation.
                if (result.get("status") == "failed" and result.get("assets") == []
                        and type(usage.get("image_calls")) is int and usage["image_calls"] == 0
                        and error.get("stage") == "analyze_materials"
                        and isinstance(error.get("code"), str)
                        and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", error["code"])
                        and error["code"] != "generation_uncertain"):
                    self.save_state({"failure": {
                        "code": error["code"], "stage": error["stage"],
                        "retryable": error.get("retryable") is True,
                        "message": "图片素材分析失败，请检查模型服务连接后重试",
                    }})
                    return QueryOutcome(status="FOUND", state="FAILED", **fallback)
                return QueryOutcome(status="UNAVAILABLE", **fallback)
            manifest = self._manifest(task_id, state["request_body"], result)
            if state.get("manifest") and state["manifest"] != manifest.model_dump(mode="json"):
                raise ValueError("Original image result changed")
            self.save_state({"manifest": manifest.model_dump(mode="json")})
            return QueryOutcome(status="FOUND", state="RESULT_READY", result=manifest, **fallback)
        except (MediaServiceError, OSError, ValueError, TypeError, KeyError, AttributeError):
            return QueryOutcome(status="UNAVAILABLE", **fallback)

    def retrieve_original(self, locator):
        fallback = dict(protocol_version=PROTOCOL, test_only=False, locator=locator)
        try:
            state = self.load_state() if self.load_state else {}
            if state.get("scope") != self.retry_scope():
                return ResultSource(status="UNSUPPORTED", **fallback)
            items = (state.get("manifest") or {}).get("items", [])
            item = next((i for i in items if i.get("locator") == locator), None)
            task_id = _identifier(state.get("upstream_task_id"))
            if not item or not locator.startswith(f"/api/v1/tasks/{task_id}/blobs/"):
                return ResultSource(status="UNSUPPORTED", **fallback)
            _asset_identifier(locator.split("/")[-1])
            data, mime = self.client.download(locator)
            validate_image_content(data, mime, max_bytes=self.profile.max_result_bytes)
            digest = hashlib.sha256(data).hexdigest()
            if (
                len(data) != item["byte_length"]
                or mime != item["media_type"]
                or digest != item["sha256"]
            ):
                raise ValueError("Original image content changed")
            return ResultSource(
                status="AVAILABLE",
                content=data,
                complete=True,
                media_type=mime,
                sha256=digest,
                byte_length=len(data),
                **fallback,
            )
        except (MediaServiceError, OSError, ValueError, TypeError, KeyError):
            return ResultSource(status="UNAVAILABLE", **fallback)

    def verify_callback(self, raw, headers):
        return VerifiedEvent(status="UNSUPPORTED", protocol_version=PROTOCOL, test_only=False)
