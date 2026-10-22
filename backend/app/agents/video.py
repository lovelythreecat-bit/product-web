"""Video planning/explicit confirmation protocol; polling never starts generation.

Create fixes a planning snapshot; confirm fixes the upstream generation snapshot at
that later instant. There is no expected-config-version API to close that window.
The task uses versioned audio preferences and no independent real audio models;
legacy tasks remain silent. Duration uses the upstream default and
the resolved options must be shown in the plan before the user confirms.
"""

import hashlib
from collections.abc import Mapping
from copy import deepcopy
from io import BytesIO
from urllib.parse import urlencode, urlsplit
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
from .media_http import MediaClient, MediaServiceError

PROTOCOL = "video-agent-v1"
DOWNLOAD_SOURCE = "video-agent:bound-service"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
_ERRORS = (MediaServiceError, OSError, ValueError, TypeError, KeyError)


def _id(value):
    canonical = str(UUID(str(value)))
    if str(value) != canonical:
        raise ValueError("Noncanonical video identity")
    return canonical


def _key(value):
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 128
        or any(not 33 <= ord(char) <= 126 for char in value)
    ):
        raise MediaServiceError(422)
    return value


class VideoAgentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    base_url: str
    service_key: SecretStr = Field(repr=False)
    max_result_bytes: int = Field(strict=True, ge=1)
    video_audio_enabled: bool = Field(default=False, strict=True)

    @field_validator("base_url")
    @classmethod
    def valid_origin(cls, value):
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
            raise ValueError("Video service requires an exact HTTP(S) origin")
        _ = parts.port
        return value.rstrip("/")

    @field_validator("service_key")
    @classmethod
    def valid_key(cls, value):
        key = value.get_secret_value()
        if not key or any(not 33 <= ord(c) <= 126 for c in key):
            raise ValueError("Invalid video service key")
        return value


def _product(product, *, wire=False):
    if not isinstance(product, dict):
        raise ValueError("Invalid video product")
    name = product.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Video product requires a name")
    points = product.get("selling_points", product.get("sellingPoints", []))
    # Preserve the entire original text as one fact rather than invent separators.
    if isinstance(points, str):
        points = [points] if points else []
    if not isinstance(points, list) or any(not isinstance(point, str) for point in points):
        raise ValueError("Invalid video selling points")
    category, specs = product.get("category"), product.get("specs")
    if any(value is not None and not isinstance(value, str) for value in (category, specs)):
        raise ValueError("Invalid video product text")
    known = {"name", "category", "selling_points", "sellingPoints", "specs", "extra"}
    extra = product.get("extra", {})
    if not isinstance(extra, dict):
        raise ValueError("Invalid video product extra")
    if wire and product.keys() - known:
        raise ValueError("Unsupported video product field")
    extra = {**extra, **{key: value for key, value in product.items() if key not in known}}
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in extra.items()):
        raise ValueError("Video product extra must contain strings")
    return {
        "name": name,
        "category": category,
        "selling_points": deepcopy(points),
        "specs": specs,
        "extra": extra,
    }


def _materials(source):
    refs = source.get("material_versions")
    if not isinstance(refs, list) or not 1 <= len(refs) <= 12:
        raise ValueError("Video requires frozen images")
    result = []
    for ref in refs:
        file_id, version = _id(ref["file_id"]), ref["version"]
        if not isinstance(version, str) or not version or len(version) > 200:
            raise ValueError("Invalid video material version")
        result.append((file_id, version))
    if len({file_id for file_id, _ in result}) != len(result):
        raise ValueError("Duplicate video material")
    return result


def build_video_request(snapshot, uploads=None, *, validate_only=False, video_audio_enabled=None):
    """Map immutable local inputs to the actual strict upstream create schema."""
    source = snapshot["input_snapshot"]
    params = source["parameters"]
    if (not isinstance(params, dict) or "first_frame_file_id" not in params
            or params.keys() - {"first_frame_file_id", "duration_seconds", "aspect_ratio"}):
        raise ValueError("Video requires an explicit first-frame selection")
    duration = params.get("duration_seconds")
    ratio = params.get("aspect_ratio", "9:16")
    if (("duration_seconds" in params and (type(duration) is not int or not 1 <= duration <= 30))
            or ratio not in ("9:16", "16:9", "1:1", "4:5", "3:4", "4:3", "3:2", "2:3")):
        raise ValueError("Unsupported video duration or aspect ratio")
    refs = _materials(source)
    first = _id(params["first_frame_file_id"])
    if first not in {file_id for file_id, _ in refs}:
        raise ValueError("First frame is not a frozen task image")
    prompt = source.get("instruction", "")
    if not isinstance(prompt, str):
        raise ValueError("Invalid video user prompt")
    if video_audio_enabled is None:
        video_audio_enabled = (snapshot.get("routing_snapshot") or {}).get(
            "video_audio_enabled", False
        )
    if type(video_audio_enabled) is not bool:
        raise ValueError("Invalid video audio preference")
    body = {
        "product_info": _product(source["product"]),
        "user_prompt": prompt,
        "images": [],
        "first_frame_asset_id": None,
        "video_options": {
            "duration_seconds": duration,
            "aspect_ratio": ratio,
            "subtitles": True,
            "voiceover": video_audio_enabled,
            "music": video_audio_enabled,
        },
        "audio_options": {
            "language": None,
            "voice_preference": "",
            "music_direction": "",
            "music_asset_id": None,
        },
    }
    if not validate_only:
        for file_id, version in refs:
            asset_id = _id((uploads or {})[file_id + ":" + version]["asset_id"])
            body["images"].append(asset_id)
            if file_id == first:
                body["first_frame_asset_id"] = asset_id
        if len(set(body["images"])) != len(refs):
            raise ValueError("Video uploads must be distinct assets")
    return body


def _image(data, mime):
    formats = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_IMAGE_BYTES or mime not in formats:
        raise ValueError("Invalid video material")
    try:
        with Image.open(BytesIO(data)) as image:
            if (
                image.format != formats[mime]
                or getattr(image, "n_frames", 1) != 1
                or image.width * image.height > 40_000_000
            ):
                raise ValueError("Invalid video material image")
            image.verify()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise ValueError("Invalid video material image") from error


class VideoAgentAdapter:
    agent_id = "video"
    protocol_version = PROTOCOL
    test_only = False
    capabilities = Capabilities(
        sync="unsupported",
        async_="supported",
        stream="unsupported",
        final_text="unsupported",
        idempotent_submit="supported",
        query_external="supported",
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
    ):
        self.profile = profile
        self.external_submission_id = external_submission_id
        self.material_loader = material_loader
        self._memory = {}
        self.load_state = load_state or (lambda: deepcopy(self._memory))
        self.save_state = save_state or (lambda patch: self._memory.update(deepcopy(patch)))
        self.client = MediaClient(
            profile.base_url,
            profile.service_key,
            timeout=30,
            max_response_bytes=profile.max_result_bytes,
        )

    def _save(self, **patch):
        self.save_state(deepcopy(patch))

    def _identity(self, task_id=None, external=None):
        return {
            "protocol_version": PROTOCOL,
            "test_only": False,
            "external_submission_id": external or self.external_submission_id,
            "upstream_task_id": task_id,
        }

    def retry_scope(self):
        # A routing identity permits initial dispatch; it is not an absence proof.
        return {
            "instance_id": "video:" + hashlib.sha256(self.profile.base_url.encode()).hexdigest(),
            "protocol_version": PROTOCOL,
        }

    def submit_scoped(self, snapshot, external_submission_id, scope):
        if scope != self.retry_scope():
            return SubmitOutcome(
                status="UNKNOWN", **self._identity(external=external_submission_id)
            )
        return self.submit(snapshot, external_submission_id)

    def _upload(self, snapshot):
        state = self.load_state()
        refs = _materials(snapshot["input_snapshot"])
        uploads = deepcopy(state.get("uploads", {}))
        missing = [(fid, version) for fid, version in refs if fid + ":" + version not in uploads]
        if not missing:
            return uploads
        if self.material_loader is None:
            raise ValueError("Frozen video material loader unavailable")
        materials = self.material_loader()
        if (
            not isinstance(materials, list)
            or [(_id(item["file_id"]), item["version"]) for item in materials] != refs
        ):
            raise ValueError("Video material versions do not match the original request")
        for item in materials:
            key = item["file_id"] + ":" + item["version"]
            if key in uploads:
                continue
            data, mime = item["content"], item["media_type"]
            _image(data, mime)
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError("Video material digest mismatch")
            asset = self.client.upload("/api/v1/assets", data, mime, fields={"kind": "image"})
            _id(asset["asset_id"])
            if (
                asset.get("kind") != "image"
                or asset.get("media_type") != mime
                or asset.get("byte_size") != len(data)
            ):
                raise ValueError("Video uploaded asset mismatch")
            uploads[key] = {
                name: asset[name]
                for name in ("asset_id", "kind", "media_type", "byte_size", "filename")
            }
            self._save(uploads=uploads)
        return uploads

    def submit(self, snapshot, external_submission_id):
        fallback = self._identity(external=external_submission_id)
        try:
            external = _id(external_submission_id)
            if self.external_submission_id and external != self.external_submission_id:
                raise ValueError("Video external identity mismatch")
            self.external_submission_id = external
            state = self.load_state()
            if state.get("request_body", {}).get("external_request_id") not in {None, external}:
                raise ValueError("Original video external identity changed")
            if state.get("upstream_task_id"):
                return SubmitOutcome(
                    status="ACCEPTED", **self._identity(_id(state["upstream_task_id"]))
                )
            if state.get("submission_attempted"):
                return SubmitOutcome(status="UNKNOWN", **fallback)
            build_video_request(
                snapshot, validate_only=True, video_audio_enabled=self.profile.video_audio_enabled
            )
            body = build_video_request(
                snapshot, self._upload(snapshot),
                video_audio_enabled=self.profile.video_audio_enabled,
            )
            owner = state.get("user_id", snapshot.get("user_id"))
            if snapshot.get("user_id") is not None and snapshot["user_id"] != owner:
                raise ValueError("Video task owner mismatch")
            body.update(external_request_id=external, external_user_id=_id(owner))
            if state.get("request_body") is not None and state["request_body"] != body:
                raise ValueError("Frozen video create body changed")
            self._save(
                request_body=body,
                submission_attempted=True,
                task_options_source="video-agent-v1:first-release-task-policy",
            )
            status, payload = self.client.json(
                "POST", "/api/v1/tasks", body, idempotency_key=external
            )
            if status != 201:
                return SubmitOutcome(status="UNKNOWN", **fallback)
            task_id = _id(payload["task_id"])
            self._assert_task(payload, task_id)
            self._save(upstream_task_id=task_id)
            self._metadata(payload)
            return SubmitOutcome(status="ACCEPTED", **self._identity(task_id))
        except _ERRORS:
            return SubmitOutcome(status="UNKNOWN", **fallback)

    def _assert_task(self, view, task_id):
        state = self.load_state()
        body = state.get("request_body")
        if (
            not isinstance(view, dict)
            or not isinstance(body, dict)
            or view.get("task_id") != task_id
            or state.get("upstream_task_id") not in {None, task_id}
            or view.get("external_request_id") != body.get("external_request_id")
            or view.get("external_user_id") != body.get("external_user_id")
            or self.external_submission_id != body.get("external_request_id")
        ):
            raise MediaServiceError(503)
        expected = {**body, **state.get("input_overrides", {})}
        intent = state.get("input_intent", {}).get("body", {})
        # An uncertain PATCH may already be applied. Both old and intended inputs
        # bind the same task, and only an observed exact intended view commits it.
        candidates = [expected, {**expected, **intent}] if intent else [expected]
        for candidate in candidates:
            if all(
                view.get(key) == candidate.get(key)
                for key in ("product_info", "user_prompt", "first_frame_asset_id", "audio_options")
            ):
                if view.get("image_asset_ids") != candidate["images"]:
                    continue
                actual_options = view.get("video_options", {})
                if not isinstance(actual_options, dict):
                    continue
                if any(
                    actual_options.get(key) != value
                    for key, value in candidate["video_options"].items()
                    if value is not None
                ):
                    continue
                if intent and candidate != expected:
                    self._save(
                        input_overrides={**state.get("input_overrides", {}), **intent},
                        input_intent_applied=True,
                    )
                return
        raise MediaServiceError(503)

    def _metadata(self, view):
        patch = {"status": view["status"]}
        questions = view.get("questions", [])
        if (
            not isinstance(questions, list)
            or len(questions) > 100
            or any(not isinstance(question, str) or len(question) > 10000 for question in questions)
        ):
            raise ValueError("Invalid video questions")
        patch["questions"] = questions
        for key in ("head_plan_version", "completed_shots", "total_shots"):
            value = view.get(key)
            if value is not None:
                if type(value) is not int or value < 0:
                    raise ValueError("Invalid video progress")
                patch[key] = value
        stage = view.get("stage")
        if isinstance(stage, str) and len(stage) <= 100:
            patch["stage"] = stage
        failure = view.get("failure")
        if isinstance(failure, dict):
            patch["failure"] = {
                "retryable": failure.get("retryable") is True,
                "message": "视频服务处理失败，请检查阶段与错误码",
            }
            for key in ("code", "stage"):
                value = failure.get(key)
                if (
                    isinstance(value, str)
                    and len(value) <= 100
                    and all(char.isalnum() or char in "_-" for char in value)
                ):
                    patch["failure"][key] = value
        self._save(**patch)

    def _plan(self, task_id, version):
        status, plan = self.client.json("GET", f"/api/v1/tasks/{task_id}/plans/{version}")
        if (
            status != 200
            or not isinstance(plan, dict)
            or plan.get("task_id") != task_id
            or plan.get("plan_version") != version
            or plan.get("is_head") is not True
            or plan.get("abandoned") is not False
        ):
            raise ValueError("Video plan identity mismatch")
        document = plan.get("document")
        allowed = {
            "creative",
            "audience",
            "selling_points",
            "shared_visual",
            "shots",
            "music_direction",
            "music_asset_id",
            "duration_seconds",
            "aspect_ratio",
            "fit",
            "subtitles",
            "voiceover",
            "music",
            "first_frame_source",
            "first_frame_asset_id",
            "model_capabilities",
            "language",
            "voice_preference",
        }
        if not isinstance(document, dict):
            raise ValueError("Invalid video plan")
        body = self.load_state()["request_body"]
        if (
            document.get("first_frame_source") != "selected"
            or document.get("first_frame_asset_id") != body["first_frame_asset_id"]
            or type(document.get("duration_seconds")) is not int
            or not 1 <= document["duration_seconds"] <= 30
            or any(
                type(document.get(key)) is not bool for key in ("subtitles", "voiceover", "music")
            )
            or any(
                document.get(key) != body["video_options"][key]
                for key in ("aspect_ratio", "subtitles", "voiceover", "music")
            )
        ):
            raise ValueError("Unsupported video plan options")
        safe = {key: deepcopy(value) for key, value in document.items() if key in allowed}
        for field, fields in {
            "shared_visual": {
                "product_reference",
                "scene",
                "lighting",
                "palette",
                "style",
                "character",
                "scene_change",
            },
            "shots": {
                "shot_id",
                "content",
                "action",
                "shot_size",
                "camera",
                "scene_id",
                "start_frame",
                "end_frame",
                "subtitle_text",
                "voiceover_text",
            },
        }.items():
            if field == "shots":
                if (
                    not isinstance(safe.get(field), list)
                    or not 1 <= len(safe[field]) <= 100
                    or any(not isinstance(shot, dict) for shot in safe[field])
                ):
                    raise ValueError("Invalid video plan shots")
                safe[field] = [
                    {key: value for key, value in shot.items() if key in fields}
                    for shot in safe[field]
                    if isinstance(shot, dict)
                ]
            else:
                if not isinstance(safe.get(field), dict):
                    raise ValueError("Invalid video plan visual")
                safe[field] = {key: value for key, value in safe[field].items() if key in fields}
                if any(
                    value is not None and not isinstance(value, str)
                    for value in safe[field].values()
                ):
                    raise ValueError("Invalid video plan visual text")
        if any(
            not isinstance(safe.get(key), str)
            for key in ("creative", "audience", "aspect_ratio", "fit", "model_capabilities")
        ):
            raise ValueError("Invalid video plan text")
        if any(
            value is not None and not isinstance(value, str)
            for key, value in safe.items()
            if key in {"music_direction", "music_asset_id", "language", "voice_preference"}
        ):
            raise ValueError("Invalid video plan optional text")
        points = safe.get("selling_points")
        if (
            not isinstance(points, list)
            or len(points) > 100
            or any(not isinstance(point, str) for point in points)
        ):
            raise ValueError("Invalid video plan selling points")
        for shot in safe["shots"]:
            if any(
                not isinstance(value, str)
                for key, value in shot.items()
                if key not in {"start_frame", "end_frame"}
            ):
                raise ValueError("Invalid video shot text")
            if (
                any(type(shot.get(key)) is not int for key in ("start_frame", "end_frame"))
                or not 0 <= shot["start_frame"] < shot["end_frame"]
            ):
                raise ValueError("Invalid video shot frames")
        safe_plan = {
            "task_id": task_id,
            "plan_version": version,
            "is_head": True,
            "confirmed": plan.get("confirmed") is True,
            "abandoned": False,
            "document": safe,
        }
        self._save(plan=safe_plan)

    def query_by_external(self, external_submission_id):
        fallback = self._identity(external=external_submission_id)
        try:
            external = _id(external_submission_id)
            body = self.load_state().get("request_body", {})
            if (
                external != self.external_submission_id
                or body.get("external_request_id") != external
                or not body.get("external_user_id")
            ):
                raise ValueError("Original video query identity unavailable")
            ids = []
            for offset in range(0, 1000, 100):
                query = urlencode(
                    {
                        "external_request_id": external,
                        "external_user_id": body["external_user_id"],
                        "limit": 100,
                        "offset": offset,
                    }
                )
                status, page = self.client.json("GET", "/api/v1/tasks?" + query)
                if (
                    status != 200
                    or not isinstance(page, dict)
                    or not isinstance(page.get("items"), list)
                ):
                    raise ValueError("Invalid video lookup")
                ids.extend(_id(item["task_id"]) for item in page["items"])
                if len(set(ids)) > 1:
                    raise ValueError("Ambiguous video external identity")
                total = page["total"]
                if type(total) is not int or total < 0 or total > 1000:
                    raise ValueError("Unbounded video lookup")
                if offset + 100 >= total:
                    break
            if not ids:
                return QueryOutcome(status="NOT_FOUND", **fallback)
            return self.query(ids[0])
        except _ERRORS:
            return QueryOutcome(status="UNAVAILABLE", **fallback)

    def query(self, upstream_task_id):
        fallback = self._identity(upstream_task_id)
        try:
            task_id = _id(upstream_task_id)
            status, view = self.client.json("GET", f"/api/v1/tasks/{task_id}")
            if status == 404:
                return QueryOutcome(status="NOT_FOUND", **fallback)
            if status != 200:
                raise ValueError("Video task unavailable")
            self._assert_task(view, task_id)
            self._save(upstream_task_id=task_id)
            self._metadata(view)
            state = self.load_state()
            phase = view["status"]
            if phase == "awaiting_confirmation" and view.get("head_plan_version") is not None:
                self._plan(task_id, view["head_plan_version"])
                self._recover_revision()
            generation = state.get("generation_id")
            if generation is None and view.get("generation_id"):
                intended = state.get("confirmation_intent", {}).get("plan_version")
                if intended is None or view.get("confirmed_plan_version") != intended:
                    raise ValueError("Unrecognized video generation")
                generation = _id(view["generation_id"])
                self._save(generation_id=generation, confirmed_plan_version=intended)
                state = self.load_state()
            if generation:
                status, generated = self.client.json("GET", f"/api/v1/generations/{generation}")
                if (
                    status != 200
                    or not isinstance(generated, dict)
                    or generated.get("generation_id") != generation
                    or generated.get("task_id") != task_id
                    or generated.get("plan_version") != state["confirmed_plan_version"]
                ):
                    raise ValueError("Video generation identity mismatch")
                generation_state = generated.get("status")
                if generation_state == "succeeded":
                    manifest = self._result(task_id, generation, state["confirmed_plan_version"])
                    return QueryOutcome(
                        status="FOUND", state="RESULT_READY", result=manifest, **fallback
                    )
                if generation_state == "failed":
                    return QueryOutcome(status="FOUND", state="FAILED", **fallback)
                if generation_state not in {"queued", "pending", "generating", "running"}:
                    raise ValueError("Unknown video generation state")
                return QueryOutcome(status="FOUND", state="RUNNING", **fallback)
            if phase == "failed":
                return QueryOutcome(status="FOUND", state="FAILED", **fallback)
            if phase in {"pending", "planning", "awaiting_input", "awaiting_confirmation"}:
                return QueryOutcome(status="FOUND", state="RUNNING", **fallback)
            raise ValueError("Unknown video state")
        except _ERRORS:
            return QueryOutcome(status="UNAVAILABLE", **fallback)

    def _artifact(self, task_id, generation, version):
        status, artifacts = self.client.json("GET", f"/api/v1/tasks/{task_id}/artifacts")
        if status != 200 or not isinstance(artifacts, list):
            raise ValueError("Video artifacts unavailable")
        matches = [
            item
            for item in artifacts
            if isinstance(item, dict)
            and item.get("task_id") == task_id
            and item.get("generation_id") == generation
            and item.get("plan_version") == version
        ]
        if len(matches) != 1:
            raise ValueError("No unique approved video artifact")
        artifact = matches[0]
        # A deliberately disabled check is a supported output mode. Its flag is
        # derived upstream from this generation's immutable configuration, never
        # from today's admin settings or an untrusted free-text quality reason.
        if not (
            artifact.get("quality_status") == "passed"
            or artifact.get("quality_status") == "not_assessed"
            and artifact.get("visual_check_enabled") is False
        ):
            raise ValueError("Video artifact requires a completed or explicitly disabled check")
        artifact_id = _id(matches[0]["artifact_id"])
        if self.load_state().get("artifact_id") not in {None, artifact_id}:
            raise ValueError("Original video artifact changed")
        return artifact_id

    def _download(self, artifact_id):
        locator = f"/api/v1/artifacts/{artifact_id}/content"
        data, mime = self.client.download(locator)
        if (
            not isinstance(data, bytes)
            or not 0 < len(data) <= self.profile.max_result_bytes
            or mime != "video/mp4"
        ):
            raise ValueError("Invalid video content")
        digest = hashlib.sha256(data).hexdigest()
        state = self.load_state()
        if state.get("artifact_sha256") not in {None, digest} or state.get(
            "artifact_byte_length"
        ) not in {None, len(data)}:
            raise ValueError("Original video content changed")
        return locator, data, digest

    def _result(self, task_id, generation, version):
        artifact_id = self._artifact(task_id, generation, version)
        # Persist identity before downloading: a saving interruption stays bound
        # to this exact artifact and can never choose a later regenerated result.
        self._save(artifact_id=artifact_id)
        locator, data, digest = self._download(artifact_id)
        self._save(artifact_sha256=digest, artifact_byte_length=len(data))
        return ResultManifest(
            complete=True,
            expected_items=1,
            items=(
                ResultItem(
                    item_key="original-1",
                    locator=locator,
                    media_type="video/mp4",
                    sha256=digest,
                    byte_length=len(data),
                ),
            ),
        )

    def retrieve_original(self, locator):
        fallback = {"protocol_version": PROTOCOL, "test_only": False, "locator": locator}
        try:
            state = self.load_state()
            artifact_id = _id(state["artifact_id"])
            if locator != f"/api/v1/artifacts/{artifact_id}/content":
                return ResultSource(status="UNSUPPORTED", **fallback)
            self._artifact(
                _id(state["upstream_task_id"]),
                _id(state["generation_id"]),
                state["confirmed_plan_version"],
            )
            _, data, digest = self._download(artifact_id)
            self._save(artifact_sha256=digest, artifact_byte_length=len(data))
            return ResultSource(
                status="AVAILABLE",
                complete=True,
                content=data,
                media_type="video/mp4",
                sha256=digest,
                byte_length=len(data),
                **fallback,
            )
        except _ERRORS:
            return ResultSource(status="UNAVAILABLE", **fallback)

    def confirm(self, plan_version, idempotency_key):
        state = self.load_state()
        if (
            type(plan_version) is not int
            or plan_version < 1
            or state.get("head_plan_version") != plan_version
            or state.get("plan", {}).get("plan_version") != plan_version
            or state.get("plan", {}).get("task_id") != state.get("upstream_task_id")
        ):
            raise MediaServiceError(409)
        task_id = _id(state["upstream_task_id"])
        intent = {"plan_version": plan_version, "idempotency_key": _key(idempotency_key)}
        if state.get("confirmation_intent") not in (None, intent):
            raise MediaServiceError(409)
        if state.get("confirmation_intent") == intent:
            if state.get("generation_id") and state.get("confirmed_plan_version") == plan_version:
                return state
            # The intent was persisted before transport, including by older
            # versions that did not write confirmation_attempted. A timeout or
            # generic 429 does not establish that generation was not accepted.
            # Recover that exact generation through reads; never repeat POST.
            outcome = self.query(task_id)
            recovered = self.load_state()
            if (
                outcome.status == "FOUND"
                and recovered.get("confirmation_intent") == intent
                and recovered.get("confirmed_plan_version") == plan_version
                and recovered.get("generation_id")
            ):
                return recovered
            raise MediaServiceError(503)
        if (
            state.get("confirmation_intent") is None
            and state.get("status") != "awaiting_confirmation"
        ):
            raise MediaServiceError(409)
        self._save(confirmation_intent=intent, confirmation_attempted=True)
        status, view = self.client.json(
            "POST",
            f"/api/v1/tasks/{task_id}/confirm",
            {"plan_version": plan_version},
            idempotency_key=idempotency_key,
        )
        if status != 202:
            raise MediaServiceError(status)
        self._assert_task(view, task_id)
        if view.get("confirmed_plan_version") != plan_version:
            raise MediaServiceError(503)
        generation = _id(view["generation_id"])
        if state.get("generation_id") not in {None, generation}:
            raise MediaServiceError(409)
        self._save(generation_id=generation, confirmed_plan_version=plan_version)
        self._metadata(view)
        return self.load_state()

    def _recover_revision(self):
        state = self.load_state()
        intent = state.get("revision_intent")
        if not intent or state.get("revision_intent_applied"):
            return
        body = intent["body"]
        plan = state.get("plan", {})
        if (state.get("status") != "awaiting_confirmation"
                or plan.get("plan_version", 0) <= body["plan_version"]
                or plan.get("plan_version") != state.get("head_plan_version")):
            return
        # A single durable command owns this task while its receipt is unknown.
        # For direct edits, also prove every requested field in the new version.
        document = plan.get("document", {})
        patch = body.get("patch", {})
        if ("music_direction" in patch
                and document.get("music_direction") != patch["music_direction"]):
            return
        shots = {shot.get("shot_id"): shot for shot in document.get("shots", [])}
        for edit in patch.get("shot_texts", []):
            if any(shots.get(edit["shot_id"], {}).get(key) != value for key, value in edit.items()):
                return
        self._save(revision_intent_applied=True)

    def revise_plan(self, body, idempotency_key):
        from app.tasks.media_routes import VideoPlanRevision

        body = VideoPlanRevision.model_validate(body).model_dump(exclude_none=True)
        state = self.load_state()
        intent = {"body": deepcopy(body), "idempotency_key": _key(idempotency_key)}
        previous = state.get("revision_intent")
        if previous == intent:
            if state.get("revision_intent_applied") is True:
                return state
            # A lost receipt must only query the original task. Repeating the
            # planning POST could start paid work on older upstream services.
            self.query(_id(state["upstream_task_id"]))
            recovered = self.load_state()
            if recovered.get("revision_intent_applied") is True:
                return recovered
            raise MediaServiceError(503)
        if (previous and (previous["idempotency_key"] == idempotency_key
                          or state.get("revision_intent_applied") is not True)
                or state.get("status") != "awaiting_confirmation"
                or state.get("generation_id")
                or state.get("head_plan_version") != body["plan_version"]
                or state.get("plan", {}).get("plan_version") != body["plan_version"]
                or state.get("plan", {}).get("task_id") != state.get("upstream_task_id")):
            raise MediaServiceError(409)
        task_id = _id(state["upstream_task_id"])
        self._save(revision_intent=intent, revision_intent_applied=False)
        payload = {key: value for key, value in body.items() if key != "plan_version"}
        status, view = self.client.json(
            "POST", f"/api/v1/tasks/{task_id}/plan-revisions", payload,
            idempotency_key=idempotency_key,
        )
        if status not in {200, 202}:
            raise MediaServiceError(status)
        self._assert_task(view, task_id)
        if view.get("generation_id"):
            raise MediaServiceError(503)
        self._metadata(view)
        if view.get("status") == "awaiting_confirmation":
            self._plan(task_id, view["head_plan_version"])
            self._recover_revision()
            if not self.load_state().get("revision_intent_applied"):
                raise MediaServiceError(503)
        else:
            self._save(revision_intent_applied=True)
        return self.load_state()

    def update_inputs(self, body, idempotency_key):
        state = self.load_state()
        if (
            not isinstance(body, dict)
            or not body
            or body.keys() - {"product_info", "user_prompt"}
            or "user_prompt" in body
            and not isinstance(body["user_prompt"], str)
        ):
            raise MediaServiceError(422)
        body = deepcopy(body)
        if "product_info" in body:
            try:
                body["product_info"] = _product(body["product_info"], wire=True)
            except (ValueError, TypeError):
                raise MediaServiceError(422) from None
        intent = {"body": body, "idempotency_key": _key(idempotency_key)}
        previous = state.get("input_intent")
        if previous and previous["idempotency_key"] == idempotency_key and previous != intent:
            raise MediaServiceError(409)
        if previous and previous != intent and state.get("input_intent_applied") is not True:
            raise MediaServiceError(409)
        if previous != intent and state.get("status") != "awaiting_input":
            raise MediaServiceError(409)
        task_id = _id(state["upstream_task_id"])
        if previous == intent:
            if state.get("input_intent_applied") is True:
                return state
            # A repeated input command may already have started paid planning.
            # Only an exact original task view can recover it; never PATCH twice.
            self.query(task_id)
            recovered = self.load_state()
            if (recovered.get("input_intent") == intent
                    and recovered.get("input_intent_applied") is True):
                return recovered
            raise MediaServiceError(503)
        self._save(input_intent=intent, input_intent_applied=False)
        status, view = self.client.json(
            "PATCH", f"/api/v1/tasks/{task_id}/inputs", body, idempotency_key=idempotency_key
        )
        if status not in {200, 202}:
            raise MediaServiceError(status)
        self._assert_task(view, task_id)
        self._save(
            input_overrides={**state.get("input_overrides", {}), **body}, input_intent_applied=True
        )
        self._metadata(view)
        return self.load_state()

    def verify_callback(self, raw, headers: Mapping[str, str]):
        return VerifiedEvent(status="UNSUPPORTED", protocol_version=PROTOCOL)
