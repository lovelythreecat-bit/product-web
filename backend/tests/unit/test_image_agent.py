"""Offline contract tests; no upstream/model requests are made."""

from copy import deepcopy
from hashlib import sha256
from io import BytesIO

import pytest
from PIL import Image

from app.agents.image import (
    ImageAgentAdapter,
    ImageAgentProfile,
    build_image_request,
    validate_image_content,
)


@pytest.fixture
def profile():
    return ImageAgentProfile(
        base_url="http://127.0.0.1:8100",
        service_key="private-key",
        agent_config_id="agent-1",
        image_model="fast",
    )


@pytest.fixture
def snapshot():
    return {
        "input_snapshot": {
            "product": {"name": "杯子", "category": "茶具"},
            "instruction": "保持商品本来颜色",
            "parameters": {"platform": "taobao", "output_type": "main_image"},
            "material_versions": [{"file_id": "file-1", "version": "v1"}],
        }
    }


def png():
    out = BytesIO()
    Image.new("RGB", (3, 4), "red").save(out, format="PNG")
    return out.getvalue()


class Service:
    def __init__(self):
        self.calls = []
        self.result = {
            "status": "succeeded",
            "input_check": {"matches": True},
            "output_errors": [],
            "issues": [],
            "assets": [self.asset()],
        }
        self.task = {"task_id": "task-1", "status": "completed", "core_status": "succeeded"}

    @staticmethod
    def asset(variant=None):
        return {
            "asset_id": "asset-" + str(variant),
            "platform": "taobao",
            "output_type": "main_image",
            "variant": variant,
            "status": "succeeded",
            "blob_id": "blob-" + str(variant),
            "mime_type": "image/png",
            "byte_length": len(png()),
            "quality": {
                "passed": True,
                "model_passed": True,
                "failed_checks": [],
                "critical_failed_checks": [],
                "deterministic_checks": {"passed": True},
            },
        }

    def json(self, method, path, body=None, idempotency_key=None):
        self.calls.append((method, path, deepcopy(body)))
        if method == "POST":
            return 202, {"task_id": "task-1", "status": "queued"}
        return 200, deepcopy(self.result if path.endswith("/result") else self.task)

    def upload(self, path, data, mime, fields=None):
        self.calls.append(("UPLOAD", path, None))
        return {
            "media_id": "media-1",
            "mime_type": mime,
            "byte_size": len(data),
            "sha256": sha256(data).hexdigest(),
        }

    def download(self, path):
        self.calls.append(("DOWNLOAD", path, None))
        return png(), "image/png"


def adapter(profile, snapshot, service, state=None, **options):
    state = {} if state is None else state

    def save(patch):
        state.update(deepcopy(patch))

    obj = ImageAgentAdapter(
        profile=profile,
        external_submission_id="external-1",
        load_state=lambda: deepcopy(state),
        save_state=save,
        material_loader=lambda: [
            {
                "file_id": "file-1",
                "version": "v1",
                "content": png(),
                "media_type": "image/png",
                "sha256": sha256(png()).hexdigest(),
            }
        ],
        **options,
    )
    obj.client = service
    return obj, state


def test_request_requires_explicit_choices_and_category(profile, snapshot):
    for field in ("platform", "output_type"):
        source = deepcopy(snapshot)
        del source["input_snapshot"]["parameters"][field]
        with pytest.raises(ValueError):
            build_image_request(source, profile, validate_only=True)
    snapshot["input_snapshot"]["product"]["category"] = ""
    with pytest.raises(ValueError):
        build_image_request(snapshot, profile, validate_only=True)


@pytest.mark.parametrize(
    "platform",
    ["amazon", "taobao", "tmall", "jd", "pinduoduo", "shopee", "lazada", "shein", "temu"],
)
def test_all_actual_platforms_map_without_default(profile, snapshot, platform):
    snapshot["input_snapshot"]["parameters"]["platform"] = platform
    body = build_image_request(snapshot, profile, {"file-1:v1": {"media_id": "media-1"}})
    assert body["request"]["platforms"] == [platform]
    assert body["request"]["materials"][0]["media_id"] == "media-1"
    assert body["request"]["image_model"] == "fast"


@pytest.mark.parametrize("count", [0, 9])
def test_material_count_is_rejected(profile, snapshot, count):
    snapshot["input_snapshot"]["material_versions"] *= count
    with pytest.raises(ValueError):
        build_image_request(snapshot, profile, validate_only=True)


@pytest.mark.parametrize('platform', [
    'amazon', 'taobao', 'tmall', 'jd', 'pinduoduo', 'shopee', 'lazada', 'shein', 'temu',
])
def test_white_background_preserves_selected_platform(profile, snapshot, platform):
    snapshot['input_snapshot']['parameters']['platform'] = platform
    snapshot["input_snapshot"]["parameters"]["output_type"] = "pdd_white_background"
    body = build_image_request(snapshot, profile, validate_only=True)
    assert body['request']['platforms'] == [platform]


def test_submit_persists_upload_and_exact_body_before_post_and_never_reposts(profile, snapshot):
    service = Service()
    obj, state = adapter(profile, snapshot, service)
    original_json = service.json

    def checked(method, path, body=None, idempotency_key=None):
        if method == "POST":
            assert state["uploads"]["file-1:v1"]["media_id"] == "media-1"
            assert state["request_body"] == body
            assert state["submission_started"] is True
        return original_json(method, path, body, idempotency_key)

    service.json = checked
    assert obj.submit_scoped(snapshot, "external-1", obj.retry_scope()).status == "ACCEPTED"
    assert state["upstream_task_id"] == "task-1"
    assert obj.submit(snapshot, "external-1").status == "ACCEPTED"
    assert sum(call[0] == "POST" for call in service.calls) == 1


def test_lost_task_reference_is_unknown_and_no_retry(profile, snapshot):
    service = Service()
    obj, state = adapter(profile, snapshot, service)

    def lost(*args, **kwargs):
        service.calls.append(("POST", "/api/v1/tasks", None))
        raise OSError("response lost")

    service.json = lost
    assert obj.submit(snapshot, "external-1").status == "UNKNOWN"
    assert obj.submit(snapshot, "external-1").status == "UNKNOWN"
    assert len([call for call in service.calls if call[0] == "POST"]) == 1
    assert state["request_body"]["request"]["materials"][0]["media_id"] == "media-1"
    assert obj.query_by_external("external-1").status == "UNSUPPORTED"


def queue_error(*, status=429, code="queue_full", resource_id=None, trusted=True):
    from app.agents.media_http import MediaServiceError

    error = MediaServiceError(status)
    error.error_code = code
    error.resource_id = resource_id
    error.retry_after_seconds = 7
    error.retryable_rejection = trusted
    return error


def test_explicit_queue_rejection_is_durable_without_resetting_submission(profile, snapshot):
    from app.catalog.schemas import content_digest

    service = Service()
    obj, state = adapter(profile, snapshot, service)

    def rejected(*args, **kwargs):
        raise queue_error()

    service.json = rejected
    outcome = obj.submit(snapshot, "external-1")
    assert outcome.status == "RATE_LIMITED"
    assert outcome.retry_after_seconds == 7
    assert state["submission_started"] is True
    assert state["submission_rejection"] == {
        "attempt_id": state["submission_attempt_id"],
        "error_code": "queue_full",
        "external_submission_id": "external-1",
        "scope": obj.retry_scope(),
        "request_body_digest": content_digest(state["request_body"]),
        "retry_after_seconds": 7,
    }


@pytest.mark.parametrize("error", [
    queue_error(code="rate_limit"),
    queue_error(resource_id="already-created"),
    queue_error(status=503),
    queue_error(trusted=False),
    OSError("connection lost"),
])
def test_ambiguous_rejections_remain_unknown_and_never_repost(profile, snapshot, error):
    service = Service()
    obj, state = adapter(profile, snapshot, service)

    def rejected(*args, **kwargs):
        service.calls.append(("POST", "/api/v1/tasks", None))
        raise error

    service.json = rejected
    assert obj.submit(snapshot, "external-1").status == "UNKNOWN"
    assert obj.submit(snapshot, "external-1").status == "UNKNOWN"
    assert state.get("submission_rejection") is None
    assert sum(call[0] == "POST" for call in service.calls) == 1


def test_upload_queue_rejection_never_authorizes_generation_retry(profile, snapshot):
    service = Service()
    obj, state = adapter(profile, snapshot, service)

    def rejected(*args, **kwargs):
        service.calls.append(("UPLOAD", "/api/v1/media", None))
        raise queue_error()

    service.upload = rejected
    assert obj.submit(snapshot, "external-1").status == "UNKNOWN"
    assert obj.submit(snapshot, "external-1").status == "UNKNOWN"
    assert state["upload_in_flight"] == "file-1:v1"
    assert "submission_rejection" not in state
    assert [call[0] for call in service.calls] == ["UPLOAD"]


def test_queue_rejection_needs_trusted_authorizer_before_repost(profile, snapshot):
    service = Service()
    obj, state = adapter(profile, snapshot, service)

    def rejected(*args, **kwargs):
        service.calls.append(("POST", "/api/v1/tasks", None))
        raise queue_error()

    service.json = rejected
    assert obj.submit(snapshot, "external-1").status == "RATE_LIMITED"
    assert obj.submit(snapshot, "external-1").status == "UNKNOWN"
    obj.authorize_submission_retry = lambda: False
    assert obj.submit(snapshot, "external-1").status == "UNKNOWN"
    assert state["submission_started"] is True
    assert sum(call[0] == "POST" for call in service.calls) == 1


@pytest.mark.parametrize("retry_result", ["accepted", "disconnect"])
def test_authorized_retry_keeps_upload_body_and_key_and_consumes_old_proof(
    profile, snapshot, retry_result,
):
    state = {}
    service = Service()
    obj, state = adapter(
        profile, snapshot, service, state,
        authorize_submission_retry=lambda: bool(state.get("submission_rejection")),
    )
    posts = []
    first_attempt = None

    def submit(method, path, body=None, idempotency_key=None):
        nonlocal first_attempt
        posts.append((deepcopy(body), idempotency_key))
        assert state.get("submission_rejection") is None
        if len(posts) == 1:
            first_attempt = state["submission_attempt_id"]
            raise queue_error()
        assert state["submission_attempt_id"] != first_attempt
        if retry_result == "disconnect":
            raise OSError("response lost after rejection retry")
        return 202, {"task_id": "task-1", "status": "queued"}

    service.json = submit
    assert obj.submit(snapshot, "external-1").status == "RATE_LIMITED"
    original = deepcopy(state["request_body"])
    assert obj.submit_scoped(snapshot, "external-1", obj.retry_scope()).status == (
        "ACCEPTED" if retry_result == "accepted" else "UNKNOWN"
    )
    assert posts == [(original, "external-1"), (original, "external-1")]
    assert sum(call[0] == "UPLOAD" for call in service.calls) == 1
    assert obj.submit(snapshot, "external-1").status == (
        "ACCEPTED" if retry_result == "accepted" else "UNKNOWN"
    )
    assert len(posts) == 2
    assert state.get("submission_rejection") is None


def test_authorized_retry_still_rejects_changed_original_body(profile, snapshot):
    state = {}
    service = Service()
    obj, state = adapter(
        profile, snapshot, service, state, authorize_submission_retry=lambda: True,
    )

    def rejected(*args, **kwargs):
        service.calls.append(("POST", "/api/v1/tasks", None))
        raise queue_error()

    service.json = rejected
    assert obj.submit(snapshot, "external-1").status == "RATE_LIMITED"
    snapshot["input_snapshot"]["instruction"] = "changed after first POST"
    assert obj.submit(snapshot, "external-1").status == "UNKNOWN"
    assert sum(call[0] == "POST" for call in service.calls) == 1


@pytest.mark.parametrize(
    "status",
    [
        "partial",
        "accepted",
        "pending_audit",
        "audit_error",
        "quality_failed",
        "generation_uncertain",
        "needs_input",
    ],
)
def test_completed_unapproved_results_remain_unavailable(profile, snapshot, status):
    service = Service()
    service.result["status"] = status
    obj, state = adapter(profile, snapshot, service)
    obj.submit(snapshot, "external-1")
    assert obj.query("task-1").status == "UNAVAILABLE"
    assert state["result_metadata"]["status"] == status
    assert not any(call[0] == "DOWNLOAD" for call in service.calls)


def analysis_failure(service):
    service.task["core_status"] = "failed"
    service.result.update(
        status="failed", assets=[], usage={"image_calls": 0, "vision_calls": 3},
        error_info={"code": "provider_transport", "stage": "analyze_materials",
                    "retryable": True, "message": "private upstream error"},
    )


def test_completed_needs_input_is_manual_wait_without_generation(profile, snapshot):
    service = Service()
    service.task["core_status"] = "needs_input"
    service.result.update(status="needs_input", input_check={"matches": False},
                          issues=[{"message": "private product mismatch"}], assets=[],
                          usage={"image_calls": 0})
    obj, state = adapter(profile, snapshot, service)
    obj.submit(snapshot, "external-1")
    service.calls.clear()
    outcome = obj.query("task-1")
    assert outcome.status == "NEEDS_INPUT"
    assert outcome.diagnostic_reason == "UPSTREAM_NEEDS_INPUT"
    assert outcome.upstream_task_id == "task-1"
    assert outcome.external_submission_id == "external-1"
    assert outcome.result is None and outcome.state is None
    assert all(call[0] == "GET" for call in service.calls)
    assert state["result_metadata"]["status"] == "needs_input"
    assert "private product mismatch" not in outcome.model_dump_json()


def test_needs_input_result_transport_outage_stays_recoverable(profile, snapshot):
    service = Service()
    service.task["core_status"] = "needs_input"
    obj, _ = adapter(profile, snapshot, service)
    obj.submit(snapshot, "external-1")
    original = service.json

    def unavailable(method, path, **kwargs):
        if path.endswith("/result"):
            return 503, {}
        return original(method, path, **kwargs)

    service.json = unavailable
    assert obj.query("task-1").status == "UNAVAILABLE"


def test_owner_retry_verifies_stopped_input_wait_without_submitting(profile, snapshot):
    service = Service()
    service.task["core_status"] = "needs_input"
    service.result.update(status="needs_input", assets=[], usage={"image_calls": 0})
    obj, _ = adapter(profile, snapshot, service)
    obj.submit(snapshot, "external-1")
    service.calls.clear()
    outcome = obj.query_for_owner_retry("task-1")
    assert (outcome.status, outcome.state) == ("FOUND", "FAILED")
    assert outcome.upstream_task_id == "task-1"
    assert all(call[0] == "GET" for call in service.calls)
    # Ordinary recovery must continue to wait for the owner's choice.
    assert obj.query("task-1").status == "NEEDS_INPUT"


@pytest.mark.parametrize("usage,assets", [({}, []), ({"image_calls": 1}, []),
                                         ({"image_calls": False}, []),
                                         ({"image_calls": 0}, [Service.asset()])])
def test_owner_retry_refuses_unproven_or_partial_input_wait(profile, snapshot, usage, assets):
    service = Service()
    service.task["core_status"] = "needs_input"
    service.result.update(status="needs_input", assets=assets, usage=usage)
    obj, _ = adapter(profile, snapshot, service)
    obj.submit(snapshot, "external-1")
    assert obj.query_for_owner_retry("task-1").status == "NEEDS_INPUT"


def test_analysis_failure_is_definite_and_keeps_safe_reason(profile, snapshot):
    service = Service()
    analysis_failure(service)
    obj, state = adapter(profile, snapshot, service)
    obj.submit(snapshot, "external-1")
    outcome = obj.query("task-1")
    assert (outcome.status, outcome.state) == ("FOUND", "FAILED")
    assert state["failure"]["code"] == "provider_transport"
    assert state["failure"]["stage"] == "analyze_materials"
    assert state["failure"]["retryable"] is True
    assert "private" not in str(state["failure"])
    assert not any(call[0] == "DOWNLOAD" for call in service.calls)
    assert sum(call[0] == "POST" for call in service.calls) == 1


@pytest.mark.parametrize("mutation", ["uncertain", "generated", "missing_usage", "assets",
                                    "mismatched_result", "interrupted"])
def test_uncertain_image_failures_still_require_investigation(profile, snapshot, mutation):
    service = Service()
    analysis_failure(service)
    if mutation == "uncertain":
        service.result["status"] = "generation_uncertain"
    elif mutation == "generated":
        service.result["usage"]["image_calls"] = 1
    elif mutation == "missing_usage":
        del service.result["usage"]
    elif mutation == "assets":
        service.result["assets"] = [Service.asset()]
    elif mutation == "mismatched_result":
        service.result["status"] = "succeeded"
    else:
        service.task["status"] = "interrupted"
    obj, _ = adapter(profile, snapshot, service)
    obj.submit(snapshot, "external-1")
    assert obj.query("task-1").status == "UNAVAILABLE"


def test_complete_result_has_computed_hash_and_bound_recovery(profile, snapshot):
    service = Service()
    obj, state = adapter(profile, snapshot, service)
    obj.submit(snapshot, "external-1")
    outcome = obj.query("task-1")
    assert outcome.state == "RESULT_READY"
    item = outcome.result.items[0]
    assert item.item_key == "taobao-main_image-default"
    assert item.locator == "/api/v1/tasks/task-1/blobs/blob-None"
    assert item.sha256 == sha256(png()).hexdigest()
    assert item.byte_length == len(png())
    assert obj.retrieve_original(item.locator).content == png()
    assert obj.retrieve_original("/api/v1/tasks/other/blobs/blob-None").status == "UNSUPPORTED"
    assert obj.query("other").status == "UNAVAILABLE"


@pytest.mark.parametrize("output_type", ["main_image", "detail_page"])
def test_real_target_key_blob_ids_deliver_and_recover_originals(profile, snapshot, output_type):
    snapshot["input_snapshot"]["parameters"]["output_type"] = output_type
    service = Service()
    variants = ("scene", "feature", "closeup") if output_type == "detail_page" else (None,)
    service.result["assets"] = [
        service.asset(variant) | {
            "output_type": output_type,
            "asset_id": f"taobao.{output_type}.{variant or 'default'}",
            "blob_id": f"taobao.{output_type}.{variant or 'default'}",
        } for variant in variants
    ]
    if output_type == "detail_page":
        service.result["detail_set_audits"] = [{"platform": "taobao", "passed": True}]
    obj, _ = adapter(profile, snapshot, service)
    assert obj.submit(snapshot, "external-1").status == "ACCEPTED"
    outcome = obj.query("task-1")
    assert outcome.state == "RESULT_READY"
    assert outcome.result.expected_items == len(variants)
    for item, variant in zip(outcome.result.items, variants, strict=True):
        target_key = f"taobao.{output_type}.{variant or 'default'}"
        assert item.locator == f"/api/v1/tasks/task-1/blobs/{target_key}"
        assert obj.retrieve_original(item.locator).content == png()


@pytest.mark.parametrize("blob_id", [".", "..", "../other", "a/b", "a\\b", "%2e%2e", "a?b", "a#b"])
def test_result_blob_ids_cannot_escape_original_blob_route(profile, snapshot, blob_id):
    service = Service()
    service.result["assets"][0]["blob_id"] = blob_id
    obj, _ = adapter(profile, snapshot, service)
    obj.submit(snapshot, "external-1")
    assert obj.query("task-1").status == "UNAVAILABLE"
    assert not any(call[0] == "DOWNLOAD" for call in service.calls)


def test_detail_page_requires_all_variants_and_keeps_set_audit_as_warning(profile, snapshot):
    snapshot["input_snapshot"]["parameters"]["output_type"] = "detail_page"
    service = Service()
    service.result["assets"] = [
        service.asset(v) | {"output_type": "detail_page"} for v in ("scene", "feature")
    ]
    service.result["detail_set_audits"] = [{"platform": "taobao", "passed": True}]
    obj, _ = adapter(profile, snapshot, service)
    obj.submit(snapshot, "external-1")
    assert obj.query("task-1").status == "UNAVAILABLE"
    service.result["assets"].append(service.asset("closeup") | {"output_type": "detail_page"})
    service.result["detail_set_audits"][0]["passed"] = False
    outcome = obj.query('task-1')
    assert outcome.result.expected_items == 3
    assert outcome.result.warnings


def test_result_mime_length_and_total_limit_are_enforced(profile, snapshot):
    service = Service()
    obj, _ = adapter(profile, snapshot, service)
    obj.submit(snapshot, "external-1")
    service.result["assets"][0]["byte_length"] += 1
    assert obj.query("task-1").status == "UNAVAILABLE"
    service.result["assets"][0]["byte_length"] = len(png())
    service.download = lambda _: (b"not a real png", "image/png")
    assert obj.query("task-1").status == "UNAVAILABLE"


def test_no_durable_state_means_no_generation(profile, snapshot):
    obj = ImageAgentAdapter(profile=profile)
    obj.client = Service()
    assert obj.submit(snapshot, "external-1").status == "UNSUPPORTED"


def test_final_quality_verdict_is_authoritative_over_model_advice(profile, snapshot):
    service = Service()
    service.result["assets"][0]["quality"]["model_passed"] = False
    obj, _ = adapter(profile, snapshot, service)
    obj.submit(snapshot, "external-1")
    assert obj.query("task-1").state == "RESULT_READY"


def test_declared_total_over_limit_is_rejected_before_any_blob_download(profile, snapshot):
    snapshot["input_snapshot"]["parameters"]["output_type"] = "detail_page"
    service = Service()
    service.result["assets"] = [
        service.asset(v) | {"output_type": "detail_page"} for v in ("scene", "feature", "closeup")
    ]
    service.result["detail_set_audits"] = [{"platform": "taobao", "passed": True}]
    obj, _ = adapter(
        profile.model_copy(update={"max_result_bytes": len(png()) * 2}), snapshot, service
    )
    obj.submit(snapshot, "external-1")
    assert obj.query("task-1").status == "UNAVAILABLE"
    assert not any(c[0] == "DOWNLOAD" for c in service.calls)


def test_corrupt_pixel_stream_is_rejected_even_with_valid_png_chunk_checksums():
    import struct
    import zlib

    valid = png()
    data = bytearray(valid[:8])
    pos = 8
    while pos < len(valid):
        count = struct.unpack(">I", valid[pos : pos + 4])[0]
        kind, chunk = valid[pos + 4 : pos + 8], valid[pos + 8 : pos + 8 + count]
        if kind == b"IDAT":
            chunk = b"not zlib"
        data.extend(struct.pack(">I", len(chunk)) + kind + chunk)
        data.extend(struct.pack(">I", zlib.crc32(kind + chunk)))
        pos += count + 12
    with pytest.raises(ValueError):
        validate_image_content(bytes(data), "image/png", max_bytes=1024)


def best_delivery(asset):
    asset['quality'].update(passed=False, failed_checks=['identity'],
                            critical_failed_checks=['identity'])
    asset['delivery'] = dict(mode='best_available', candidate_id='c0001', score=82.5,
                             sha256=sha256(png()).hexdigest(), stop_reason='quality_repair_limit')
    asset['candidates'] = [dict(candidate_id='c0001', index=1, status='quality_failed')]
    return asset


@pytest.mark.parametrize('output_type,variants', [
    ('main_image', [None]), ('detail_page', ['scene', 'feature', 'closeup']),
])
@pytest.mark.parametrize('legacy_input_check', [
    {}, {'input_check': None}, {'input_check': {}},
    {'input_check': {'matches': False}}, {'input_check': {'matches': True}},
    {'input_check': 'retired'},
], ids=['missing', 'null', 'empty', 'false', 'true', 'retired-format'])
def test_direct_delivery_accepts_unaudited_complete_images(
    profile, snapshot, output_type, variants, legacy_input_check,
):
    snapshot['input_snapshot']['parameters']['output_type'] = output_type
    service = Service()
    service.result.pop('input_check')
    service.result.update(legacy_input_check)
    assets = []
    for variant in variants:
        asset = service.asset(variant) | {'output_type': output_type, 'quality': None}
        asset['delivery'] = dict(mode='direct', candidate_id='c0001', score=None,
                                 sha256=sha256(png()).hexdigest(),
                                 stop_reason='generation_completed')
        asset['candidates'] = [dict(candidate_id='c0001', index=1, status='succeeded')]
        assets.append(asset)
    service.result.update(assets=assets, detail_set_audits=[])
    obj, _ = adapter(profile, snapshot, service)
    obj.submit(snapshot, 'external-1')
    outcome = obj.query('task-1')
    assert outcome.state == 'RESULT_READY'
    assert outcome.result.expected_items == len(variants)
    assert not outcome.result.warnings
    for item in outcome.result.items:
        assert item.sha256 == sha256(png()).hexdigest()
        assert obj.retrieve_original(item.locator).content == png()
    assert sum(call[0] == 'POST' for call in service.calls) == 1


@pytest.mark.parametrize('mutation', ['digest', 'candidate', 'stage', 'failed', 'score'])
def test_direct_delivery_keeps_byte_and_candidate_binding(profile, snapshot, mutation):
    service = Service()
    service.result.pop('input_check')
    asset = service.result['assets'][0]
    asset['quality'] = None
    asset['delivery'] = dict(mode='direct', candidate_id='c0001', score=None,
                             sha256=sha256(png()).hexdigest(), stop_reason='generation_completed')
    asset['candidates'] = [dict(candidate_id='c0001', index=1, status='succeeded')]
    if mutation == 'digest':
        asset['delivery']['sha256'] = 'a' * 64
    elif mutation == 'candidate':
        asset['delivery']['candidate_id'] = 'other'
    elif mutation in ('stage', 'failed'):
        asset['candidates'][0]['status'] = mutation
    else:
        asset['delivery']['score'] = 90
    obj, _ = adapter(profile, snapshot, service)
    obj.submit(snapshot, 'external-1')
    assert obj.query('task-1').status == 'UNAVAILABLE'


def test_best_available_delivery_is_ready_with_original_warnings(profile, snapshot):
    service = Service()
    best_delivery(service.result['assets'][0])
    service.result['warnings'] = ['已交付评分最高候选；原审核未通过']
    obj, state = adapter(profile, snapshot, service)
    obj.submit(snapshot, 'external-1')
    outcome = obj.query('task-1')
    assert outcome.state == 'RESULT_READY'
    assert outcome.result.warnings == ('已交付评分最高候选；原审核未通过',)
    assert obj.retrieve_original(outcome.result.items[0].locator).content == png()
    assert state['result_metadata']['assets'][0]['delivery']['candidate_id'] == 'c0001'


@pytest.mark.parametrize('mutation', ['digest', 'missing_candidate', 'stage', 'score', 'mode'])
def test_best_available_decision_must_bind_final_candidate_and_bytes(profile, snapshot, mutation):
    service = Service()
    asset = best_delivery(service.result['assets'][0])
    if mutation == 'digest':
        asset['delivery']['sha256'] = 'a' * 64
    elif mutation == 'missing_candidate':
        asset['delivery']['candidate_id'] = 'other'
    elif mutation == 'stage':
        asset['candidates'][0]['status'] = 'stage'
    elif mutation == 'score':
        asset['delivery']['score'] = float('nan')
    else:
        asset['delivery']['mode'] = 'approved'
    obj, _ = adapter(profile, snapshot, service)
    obj.submit(snapshot, 'external-1')
    assert obj.query('task-1').status == 'UNAVAILABLE'


def test_complete_detail_set_delivers_despite_set_audit_warning(profile, snapshot):
    snapshot['input_snapshot']['parameters']['output_type'] = 'detail_page'
    service = Service()
    service.result['assets'] = [
        best_delivery(service.asset(v) | {'output_type': 'detail_page'})
        for v in ('scene', 'feature', 'closeup')
    ]
    service.result['detail_set_audits'] = [dict(platform='taobao', passed=False, reason='similar')]
    obj, _ = adapter(profile, snapshot, service)
    obj.submit(snapshot, 'external-1')
    outcome = obj.query('task-1')
    assert outcome.state == 'RESULT_READY' and len(outcome.result.items) == 3
    assert outcome.result.warnings
