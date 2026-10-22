"""Quick generation gates preserve confirmed versions and immutable task requests."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.quick_generation.schemas import QuickDraft
from app.quick_generation.service import build_input, invalidate_downstream, require_complete


def run_state():
    return {"step": 3, "draft": QuickDraft().model_dump(mode="json"),
            "confirmed_copy": "确认文案", "confirmed_images": None,
            "current": {"copy": None, "image": None, "video": None},
            "pending_batch": None, "batches": []}


def test_confirmed_copy_is_passed_without_mutating_product_facts():
    product = SimpleNamespace(version=str(uuid4()), product={"name": "耳机", "category": "数码"})
    draft = QuickDraft(product_version=product.version, image_platform="taobao",
                       image_outputs=["main_image"], image_instruction="保持实物",
                       copy_texts={"详情介绍": "已人工修改的文案", "营销策略": "不传给图片的策略"})
    result = build_input(draft, product, "image", "已人工修改的文案", "main_image",
                         confirmed_copy_types=["详情介绍"])
    assert result.product == product.product
    assert result.parameters == {"platform": "taobao", "output_type": "main_image"}
    assert "已人工修改的文案" in result.instruction
    assert result.instruction == "已人工修改的文案"
    assert result.product is not product.product


def test_image_instruction_only_uses_confirmed_detail_copy():
    product = SimpleNamespace(version=str(uuid4()), product={"name": "耳机", "category": "数码"})
    draft = QuickDraft(image_platform="taobao", image_instruction="保持实物",
                       copy_texts={"详情介绍": "人工确认的完整详情", "营销策略": "策略全文"})
    result = build_input(draft, product, "image", "【详情介绍】\n人工确认的完整详情\n\n【营销策略】\n策略全文", "main_image",
                         confirmed_copy_types=["详情介绍", "营销策略"])
    assert "人工确认的完整详情" in result.instruction
    assert "策略全文" not in result.instruction
    assert result.instruction == "人工确认的完整详情"


def test_image_without_detail_copy_does_not_fall_back_to_all_marketing_copy():
    product = SimpleNamespace(version=str(uuid4()), product={"name": "耳机", "category": "数码"})
    draft = QuickDraft(image_platform="taobao", copy_texts={"营销策略": "策略全文"})
    result = build_input(draft, product, "image", "策略全文", "main_image")
    assert "策略全文" not in result.instruction
    assert result.product == product.product


def test_single_detail_uses_confirmed_edit_instead_of_stale_multi_copy_draft():
    product = SimpleNamespace(version=str(uuid4()), product={"name": "杯子"})
    draft = QuickDraft(image_platform="taobao", copy_texts={"详情介绍": "旧正文"})
    result = build_input(draft, product, "image", "人工确认的最新正文", "main_image",
                         confirmed_copy_types=["详情介绍"])
    assert result.instruction == "人工确认的最新正文"


def test_image_does_not_send_a_stale_detail_draft_that_was_not_confirmed():
    product = SimpleNamespace(version=str(uuid4()), product={"name": "耳机", "category": "数码"})
    draft = QuickDraft(image_platform="taobao", copy_types=["营销策略"],
                       copy_texts={"详情介绍": "未确认的旧详情", "营销策略": "策略全文"})
    result = build_input(draft, product, "image", "【营销策略】\n策略全文", "main_image",
                         confirmed_copy_types=["营销策略"])
    assert "未确认的旧详情" not in result.instruction


def test_upstream_change_invalidates_only_downstream_confirmations_and_keeps_history():
    state = {"step": 4, "confirmed_copy": "旧稿", "confirmed_images": "b2",
             "current": {"copy": "b1", "image": "b2", "video": "b3"},
             "batches": [{"id": "b1"}, {"id": "b2"}]}
    old = QuickDraft(product_version=str(uuid4()), copy_text="旧稿")
    new = old.model_copy(update={"copy_text": "新稿"})
    invalidate_downstream(state, old, new)
    assert state["step"] == 2
    assert state["confirmed_copy"] is None
    assert state["confirmed_images"] is None
    assert state["current"] == {"copy": "b1", "image": None, "video": None}
    assert len(state["batches"]) == 2


@pytest.mark.parametrize("state,settlement", [("RUNNING", "FROZEN"),
                          ("SAVE_RECOVERY", "FROZEN"), ("FAILED", "FROZEN")])
def test_incomplete_or_uncertain_task_cannot_advance(state, settlement):
    with pytest.raises(HTTPException) as caught:
        require_complete([SimpleNamespace(state=state, settlement_state=settlement)])
    assert caught.value.status_code == 409


def test_empty_batch_cannot_advance():
    with pytest.raises(HTTPException):
        require_complete([])


def test_only_fully_saved_success_advances():
    require_complete([SimpleNamespace(state="SUCCEEDED", settlement_state="CONSUMED")])


def test_video_uses_only_uploaded_frame_and_confirmed_copy():
    frame = str(uuid4())
    product = SimpleNamespace(version=str(uuid4()), product={"name": "杯子"})
    draft = QuickDraft(product_version=product.version,
                       material_versions=[{"file_id": frame, "version": "v1"}],
                       video_first_frame_file_id=frame)
    result = build_input(draft, product, "video", "确认后的文案")
    assert result.parameters == {"first_frame_file_id": frame}
    draft.video_first_frame_file_id = str(uuid4())
    with pytest.raises(HTTPException):
        build_input(draft, product, "video", "确认后的文案")


def video_preparation(monkeypatch):
    """Keep admission external while exercising the real batch/input construction."""
    from app.common.types import Quote
    from app.quick_generation.schemas import QuickPrepare
    from app.quick_generation.service import QuickGenerationService
    from app.storage.models import CapacityReservation, File
    from app.works.models import Work, WorkItem

    owner, conversation, frame, task_id = [str(uuid4()) for _ in range(4)]
    product = SimpleNamespace(version=str(uuid4()), product={"name": "杯子"})
    draft = QuickDraft(product_version=product.version,
                       material_versions=[{"file_id": str(uuid4()), "version": "ref-v1"}],
                       video_first_frame_file_id=frame)
    state = run_state()
    state.update(step=4, draft=draft.model_dump(mode="json"), confirmed_images="images")
    state["current"]["image"] = "images"
    row = SimpleNamespace(state=state, version=1, user_id=owner,
                          conversation_id=conversation)
    work = SimpleNamespace(id="work", task_id=task_id, user_id=owner,
                           conversation_id=conversation, deleted_at=None)
    item = SimpleNamespace(work_id="work", user_id=owner, file_id=frame,
                           file_version="generated-v1")
    file = SimpleNamespace(id=frame, version="generated-v1", user_id=owner,
                           state="durable", deleted_at=None, actual_mime="image/png",
                           actual_bytes=100, reservation_id="reservation",
                           reservation=SimpleNamespace(user_id=owner, intent_id="generation:task"))
    objects = {Work: work, WorkItem: item}
    def get(model, key):
        if model is File and key == frame:
            return file
        if model is CapacityReservation and key == "reservation":
            return file.reservation
        return None
    session = SimpleNamespace(scalar=lambda query: objects[query.column_descriptions[0]["entity"]],
                              get=get)
    svc = QuickGenerationService(session, SimpleNamespace(mode="mock"))
    agent_id = uuid4()
    agent = SimpleNamespace(agent_id=agent_id, kind="video", enabled=True,
                            protocol_version="video-agent-v1")
    quote = Quote(spec_id=agent_id, spec_version="v1", price_version="p1",
                  agent_version="video-agent-v1", policy_versions={}, credits=10,
                  input_digest="video")
    monkeypatch.setattr("app.quick_generation.service.CatalogService",
                        lambda *args, **kwargs: SimpleNamespace(
                            list_agents=lambda: [agent], quote_agent=lambda *args: quote))
    monkeypatch.setattr(svc, "product", lambda *args: product)
    image_task = SimpleNamespace(id=task_id, state="SUCCEEDED", settlement_state="CONSUMED")
    monkeypatch.setattr(svc, "current_tasks", lambda row, kind: [image_task] if kind == "image" else [])
    monkeypatch.setattr(svc, "change", lambda row, state: setattr(row, "state", state))
    prepare = lambda: svc.prepare(SimpleNamespace(user_id=owner), row,
                                  QuickPrepare(version=1, kind="video"))
    return prepare, row, work, item, file, image_task


def test_video_batch_freezes_current_generated_image_without_changing_product_references(monkeypatch):
    prepare, row, work, item, file, _ = video_preparation(monkeypatch)
    original_refs = row.state["draft"]["material_versions"].copy()
    batch = prepare()
    video_input = batch["items"][0]["request"]["input"]
    assert video_input["material_versions"] == [{"file_id": file.id, "version": "generated-v1"}]
    assert video_input["parameters"] == {"first_frame_file_id": file.id}
    assert row.state["draft"]["material_versions"] == original_refs
    assert row.state["confirmed_images"] == "images"
    assert row.state["current"]["image"] == "images"


@pytest.mark.parametrize("invalid", ["owner", "conversation", "historical_task", "deleted_work",
                         "item_owner", "item_work", "item_file", "wrong_version", "file_owner",
                         "non_image", "unavailable", "deleted_file", "oversized", "old_confirmation"])
def test_video_batch_rejects_generated_frame_outside_confirmed_usable_results(monkeypatch, invalid):
    prepare, row, work, item, file, _ = video_preparation(monkeypatch)
    if invalid == "owner": work.user_id = str(uuid4())
    elif invalid == "conversation": work.conversation_id = str(uuid4())
    elif invalid == "historical_task": work.task_id = str(uuid4())
    elif invalid == "deleted_work": work.deleted_at = object()
    elif invalid == "item_owner": item.user_id = str(uuid4())
    elif invalid == "item_work": item.work_id = "old-work"
    elif invalid == "item_file": item.file_id = str(uuid4())
    elif invalid == "wrong_version": file.version = "other-version"
    elif invalid == "file_owner": file.user_id = str(uuid4())
    elif invalid == "non_image": file.actual_mime = "video/mp4"
    elif invalid == "unavailable": file.state = "unavailable"
    elif invalid == "deleted_file": file.deleted_at = object()
    elif invalid == "oversized": file.actual_bytes = 20 * 1024 * 1024 + 1
    elif invalid == "old_confirmation": row.state["confirmed_images"] = "old-images"
    with pytest.raises(HTTPException):
        prepare()
    assert row.state["pending_batch"] is None


def test_video_batch_uses_only_the_selected_uploaded_frame(monkeypatch):
    prepare, row, _, _, file, _ = video_preparation(monkeypatch)
    file.reservation.intent_id = "upload:frame"
    row.state["draft"]["material_versions"].append({"file_id": file.id, "version": file.version})
    batch = prepare()
    assert batch["items"][0]["request"]["input"]["material_versions"] == [
        {"file_id": file.id, "version": file.version}]
    assert len(row.state["draft"]["material_versions"]) == 2


def test_historical_generated_frame_cannot_be_disguised_as_uploaded_material(monkeypatch):
    prepare, row, work, _, file, _ = video_preparation(monkeypatch)
    row.state["draft"]["material_versions"].append({"file_id": file.id, "version": file.version})
    work.task_id = str(uuid4())
    with pytest.raises(HTTPException):
        prepare()
    assert row.state["pending_batch"] is None


def test_stale_save_does_not_replace_server_progress():
    from app.quick_generation.schemas import QuickSave
    from app.quick_generation.service import QuickGenerationService

    row = SimpleNamespace(version=2, state=run_state())
    with pytest.raises(HTTPException) as caught:
        QuickGenerationService(None, None).save(None, row, QuickSave(version=1, draft=QuickDraft()))
    assert caught.value.status_code == 409
    assert row.state["confirmed_copy"] == "确认文案"


def test_submitted_batch_replay_never_calls_admission():
    from app.quick_generation.service import QuickGenerationService

    state = run_state()
    state["batches"] = [{"id": "batch", "submitted": True}]
    row = SimpleNamespace(state=state)
    QuickGenerationService(None, None).submit(None, row, "batch")
    assert row.state == state


def test_old_quote_cannot_submit_after_draft_changes():
    from app.quick_generation.service import QuickGenerationService

    state = run_state()
    state["batches"] = [{"id": "batch", "submitted": False, "draft_digest": "old"}]
    state["pending_batch"] = "batch"
    row = SimpleNamespace(state=state)
    with pytest.raises(HTTPException) as caught:
        QuickGenerationService(None, None).submit(None, row, "batch")
    assert caught.value.status_code == 409


def test_every_image_must_succeed_before_video_can_be_confirmed(monkeypatch):
    from app.quick_generation.schemas import QuickAdvance
    from app.quick_generation.service import QuickGenerationService

    svc = QuickGenerationService(None, None)
    monkeypatch.setattr(svc, "current_tasks", lambda *args: [
        SimpleNamespace(state="SUCCEEDED", settlement_state="CONSUMED"),
        SimpleNamespace(state="FAILED", settlement_state="FROZEN"),
    ])
    row = SimpleNamespace(state=run_state(), version=1)
    with pytest.raises(HTTPException):
        svc.advance(row, QuickAdvance(version=1, action="confirm_images"))
    assert row.state["step"] == 3
    assert row.state["confirmed_images"] is None


def test_a_new_copy_cannot_hide_an_active_downstream_task(monkeypatch):
    from app.quick_generation.schemas import QuickPrepare
    from app.quick_generation.service import QuickGenerationService

    svc = QuickGenerationService(None, SimpleNamespace(mode="mock"))
    monkeypatch.setattr(svc, "product", lambda *args: object())
    monkeypatch.setattr(svc, "current_tasks", lambda row, kind: [
        SimpleNamespace(state="RUNNING", settlement_state="FROZEN")
    ] if kind == "image" else [])
    row = SimpleNamespace(state=run_state(), version=1)
    with pytest.raises(HTTPException) as caught:
        svc.prepare(None, row, QuickPrepare(version=1, kind="copy"))
    assert caught.value.status_code == 409


def test_cancelled_unsubmitted_batch_cannot_charge(monkeypatch):
    from app.quick_generation.service import QuickGenerationService

    state = run_state()
    state["pending_batch"] = "b1"
    state["batches"] = [{"id": "b1", "submitted": False, "draft_digest": "old"}]
    row = SimpleNamespace(state=state)
    svc = QuickGenerationService(None, None)
    monkeypatch.setattr(svc, "change", lambda row, state: setattr(row, "state", state))
    svc.cancel_batch(row, "b1")
    assert row.state["pending_batch"] is None
    with pytest.raises(HTTPException):
        svc.submit(None, row, "b1")


def test_cancel_after_submission_preserves_committed_tasks():
    from app.quick_generation.service import QuickGenerationService

    state = run_state()
    state["batches"] = [{"id": "b1", "submitted": True, "items": [{"task_id": "t1"}]}]
    row = SimpleNamespace(state=state)
    QuickGenerationService(None, None).cancel_batch(row, "b1")
    assert row.state == state


@pytest.mark.parametrize('supports_images', [False, True])
def test_copy_batch_uses_actual_model_image_capability_and_keeps_workflow_materials(
    monkeypatch, supports_images,
):
    from app.agents.text import PROTOCOL
    from app.common.types import Quote
    from app.quick_generation.schemas import QuickPrepare
    from app.quick_generation.service import QuickGenerationService

    agent_id = uuid4()
    materials = [{'file_id': str(uuid4()), 'version': 'v1'}]
    draft = QuickDraft(product_version=str(uuid4()), material_versions=materials,
                       copy_instruction='保持真实卖点')
    state = run_state()
    state.update(step=1, draft=draft.model_dump(mode='json'), confirmed_copy=None)
    row = SimpleNamespace(state=state, version=1, conversation_id=str(uuid4()))
    product = SimpleNamespace(version=draft.product_version, product={'name': '杯子'})
    agent = SimpleNamespace(agent_id=agent_id, kind='copy', enabled=True,
                            protocol_version=PROTOCOL)
    quote = Quote(spec_id=agent_id, spec_version='v1', price_version='p1',
                  agent_version=PROTOCOL, policy_versions={}, credits=10, input_digest='test')
    monkeypatch.setattr('app.quick_generation.service.CatalogService',
                        lambda *args, **kw: SimpleNamespace(
                            list_agents=lambda: [agent], quote_agent=lambda *args: quote))
    monkeypatch.setattr('app.agents.text_runtime.resolve_text_profile',
                        lambda *args: SimpleNamespace(supports_images=supports_images))
    svc = QuickGenerationService(None, SimpleNamespace(mode='mock'))
    monkeypatch.setattr(svc, 'product', lambda *args: product)
    monkeypatch.setattr(svc, 'current_tasks', lambda *args: [])
    monkeypatch.setattr(svc, 'change', lambda row, state: setattr(row, 'state', state))

    batch = svc.prepare(None, row, QuickPrepare(version=1, kind='copy'))

    assert batch['items'][0]['request']['input']['material_versions'] == (
        materials if supports_images else [])
    assert batch['items'][0]['request']['input']['instruction'] == '保持真实卖点'
    assert row.state['draft']['material_versions'] == materials
    assert row.state['pending_batch'] == batch['id']


def test_copy_types_normalize_without_losing_selection_order():
    draft = QuickDraft(copy_types=[' 宣传文案 ', '直播口播', '宣传文案'])
    assert draft.copy_types == ['宣传文案', '直播口播']
    assert QuickDraft().copy_types == []
    assert QuickDraft().copy_texts == {}


def test_seven_copy_types_including_marketing_strategy_can_save_their_results():
    types = ['宣传文案', '直播口播', '短视频脚本', '商品标题', '商品卖点', '社媒文案', '营销策略']
    texts = {kind: '创作结果' for kind in types}
    draft = QuickDraft(copy_types=types, copy_texts=texts)
    assert draft.copy_types == types
    assert draft.copy_texts == texts


@pytest.mark.parametrize('types', [[' '], ['a' * 101], [str(i) for i in range(8)]])
def test_copy_types_reject_invalid_selection(types):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        QuickDraft(copy_types=types)


def copy_preparation(monkeypatch, draft):
    from app.common.types import Quote
    from app.quick_generation.schemas import QuickPrepare
    from app.quick_generation.service import QuickGenerationService

    agent_id = uuid4()
    agent = SimpleNamespace(agent_id=agent_id, kind='copy', enabled=True,
                            protocol_version='mock-copy-v1')
    def quote_agent(principal, snapshot, requested_agent):
        kind = snapshot.parameters.get('copy_type', '')
        return Quote(spec_id=agent_id, spec_version='v1', price_version='p1',
                     agent_version='mock-copy-v1', policy_versions={},
                     credits=10 if kind == '宣传文案' else 20, input_digest=kind or 'legacy')
    monkeypatch.setattr('app.quick_generation.service.CatalogService',
                        lambda *args, **kwargs: SimpleNamespace(
                            list_agents=lambda: [agent], quote_agent=quote_agent))
    state = run_state()
    state.update(step=1, draft=draft.model_dump(mode='json'), confirmed_copy=None)
    row = SimpleNamespace(state=state, version=1, conversation_id=str(uuid4()))
    svc = QuickGenerationService(None, SimpleNamespace(mode='mock'))
    monkeypatch.setattr(svc, 'product', lambda *args: SimpleNamespace(
        version=draft.product_version, product={'name': '杯子'}))
    monkeypatch.setattr(svc, 'current_tasks', lambda *args: [])
    monkeypatch.setattr(svc, 'change', lambda row, state: setattr(row, 'state', state))
    return svc, row, lambda: svc.prepare(None, row, QuickPrepare(version=1, kind='copy'))


def test_selected_copy_types_receive_separate_immutable_inputs_and_quotes(monkeypatch):
    draft = QuickDraft(product_version=str(uuid4()), copy_types=['宣传文案', '直播口播'],
                       copy_parameters={'copy_type': '旧类型', 'tone': '自然'})
    _, row, prepare = copy_preparation(monkeypatch, draft)
    batch = prepare()
    assert [item['label'] for item in batch['items']] == ['宣传文案', '直播口播']
    assert [item['request']['input']['parameters'] for item in batch['items']] == [
        {'copy_type': '宣传文案', 'tone': '自然'}, {'copy_type': '直播口播', 'tone': '自然'}]
    assert [item['request']['confirmed_quote']['credits'] for item in batch['items']] == [10, 20]
    assert row.state['draft']['copy_parameters']['copy_type'] == '旧类型'


def test_legacy_copy_type_still_prepares_one_task(monkeypatch):
    _, _, prepare = copy_preparation(monkeypatch, QuickDraft(
        product_version=str(uuid4()), copy_parameters={'copy_type': '直播口播'}))
    items = prepare()['items']
    assert len(items) == 1
    assert items[0]['request']['input']['parameters']['copy_type'] == '直播口播'


def copy_confirmation(monkeypatch, texts, *, copy_text='旧合并稿'):
    from app.quick_generation.schemas import QuickAdvance
    from app.quick_generation.service import QuickGenerationService

    state = run_state()
    state['draft'] = QuickDraft(copy_text=copy_text, copy_texts=texts).model_dump(mode='json')
    state['current']['copy'] = 'copy-batch'
    state['batches'] = [{'id': 'copy-batch', 'kind': 'copy', 'submitted': True, 'items': [
        {'label': kind, 'task_id': kind, 'request': {'input': {'parameters': {'copy_type': kind}}}}
        for kind in ['宣传文案', '直播口播']]}]
    row = SimpleNamespace(state=state, version=1)
    svc = QuickGenerationService(None, None)
    tasks = [SimpleNamespace(state='SUCCEEDED', settlement_state='CONSUMED') for _ in range(2)]
    monkeypatch.setattr(svc, 'current_tasks', lambda *args: tasks)
    monkeypatch.setattr(svc, 'change', lambda row, state: setattr(row, 'state', state))
    return row, tasks, lambda: svc.advance(row, QuickAdvance(version=1, action='confirm_copy'))


def test_multi_copy_confirmation_uses_batch_order_and_all_edited_texts(monkeypatch):
    row, _, confirm = copy_confirmation(
        monkeypatch, {'直播口播': ' 口播正文 ', '宣传文案': ' 宣传正文 '})
    confirm()
    assert row.state['confirmed_copy'] == '【宣传文案】\n宣传正文\n\n【直播口播】\n口播正文'
    assert row.state['draft']['copy_text'] == row.state['confirmed_copy']
    assert row.state['step'] == 3


@pytest.mark.parametrize('texts', [
    {}, {'宣传文案': '已完成'}, {'宣传文案': '已完成', '直播口播': ' '},
])
def test_multi_copy_confirmation_rejects_missing_text_despite_legacy_text(monkeypatch, texts):
    row, _, confirm = copy_confirmation(monkeypatch, texts)
    with pytest.raises(HTTPException) as caught:
        confirm()
    assert caught.value.status_code == 422
    assert row.state['confirmed_copy'] == '确认文案'


def test_multi_copy_confirmation_waits_for_every_task(monkeypatch):
    _, tasks, confirm = copy_confirmation(monkeypatch, {'宣传文案': '宣传', '直播口播': '口播'})
    tasks[1].state = 'RUNNING'
    tasks[1].settlement_state = 'FROZEN'
    with pytest.raises(HTTPException) as caught:
        confirm()
    assert caught.value.status_code == 409


def test_multi_copy_confirmation_rejects_oversized_aggregate(monkeypatch):
    _, _, confirm = copy_confirmation(
        monkeypatch, {'宣传文案': 'a' * 50000, '直播口播': 'b' * 50000})
    with pytest.raises(HTTPException) as caught:
        confirm()
    assert caught.value.status_code == 422


def test_editing_one_copy_invalidates_downstream_but_keeps_copy_batch():
    state = run_state()
    state.update(step=4, confirmed_images='image-batch')
    state['current'] = {'copy': 'copy-batch', 'image': 'image-batch', 'video': 'video-batch'}
    old = QuickDraft(copy_texts={'宣传文案': '旧稿'})
    new = old.model_copy(update={'copy_texts': {'宣传文案': '新稿'}})
    invalidate_downstream(state, old, new)
    assert state['confirmed_copy'] is None
    assert state['confirmed_images'] is None
    assert state['current'] == {'copy': 'copy-batch', 'image': None, 'video': None}
    assert state['step'] == 2


def test_new_copy_submission_clears_all_previous_editable_text(monkeypatch):
    from app.catalog.schemas import content_digest
    from app.quick_generation.service import QuickGenerationService

    state = run_state()
    state['draft'] = QuickDraft(
        copy_text='旧稿', copy_texts={'宣传文案': '旧稿'}).model_dump(mode='json')
    state['pending_batch'] = 'new-copy'
    state['batches'] = [{'id': 'new-copy', 'kind': 'copy', 'submitted': False,
                        'draft_digest': content_digest(state['draft']),
                        'items': [{'task_id': 'already-admitted', 'request': {}}]}]
    row = SimpleNamespace(state=state)
    svc = QuickGenerationService(None, None)
    monkeypatch.setattr(svc, 'change', lambda row, state: setattr(row, 'state', state))
    svc.submit(None, row, 'new-copy')
    assert row.state['draft']['copy_text'] == ''
    assert row.state['draft']['copy_texts'] == {}


@pytest.mark.parametrize('operation', ['save', 'prepare', 'confirm_copy', 'confirm_images',
                                        'finish', 'back', 'submit', 'cancel'])
def test_completed_run_rejects_writes_without_changing_history(monkeypatch, operation):
    from copy import deepcopy

    from app.quick_generation.schemas import QuickAdvance, QuickPrepare, QuickSave
    from app.quick_generation.service import QuickGenerationService

    state = run_state()
    state['step'] = 5
    state['pending_batch'] = 'pending'
    state['batches'] = [{'id': 'pending', 'submitted': False}]
    row = SimpleNamespace(state=state, version=1)
    original = deepcopy(state)
    svc = QuickGenerationService(None, None)
    monkeypatch.setattr(svc, 'change', lambda *_: pytest.fail('completed history was changed'))
    monkeypatch.setattr(svc, 'product', lambda *_: pytest.fail('write reached product lookup'))
    with pytest.raises(HTTPException) as caught:
        if operation == 'save':
            svc.save(None, row, QuickSave(version=1, draft=QuickDraft(copy_text='改稿')))
        elif operation == 'prepare':
            svc.prepare(None, row, QuickPrepare(version=1, kind='copy'))
        elif operation == 'submit':
            svc.submit(None, row, 'pending')
        elif operation == 'cancel':
            svc.cancel_batch(row, 'pending')
        else:
            svc.advance(row, QuickAdvance(version=1, action=operation))
    assert caught.value.status_code == 409
    assert '只读' in caught.value.detail
    assert row.state == original


def test_completed_run_allows_replaying_an_already_submitted_batch_without_writes():
    from app.quick_generation.service import QuickGenerationService

    row = SimpleNamespace(state={'step': 5, 'batches': [{'id': 'done', 'submitted': True}]})
    QuickGenerationService(None, None).submit(None, row, 'done')


def regeneration_preparation(monkeypatch, *, kind='copy', used=0):
    from app.quick_generation.schemas import QuickPrepare

    draft = QuickDraft(product_version=str(uuid4()), copy_types=['宣传文案', '直播口播'],
                       copy_texts={'宣传文案': '已编辑宣传', '直播口播': '已编辑口播'},
                       image_platform='taobao', image_outputs=['main_image', 'detail_page'])
    svc, row, _ = copy_preparation(monkeypatch, draft)
    row.id = str(uuid4())
    row.state['confirmed_copy'] = '确认文案'
    batch = svc.prepare(None, row, QuickPrepare(version=1, kind='copy'))
    batch.update(id='original', submitted=True, kind=kind)
    for index, item in enumerate(batch['items']):
        item.update(task_id=f'old-{index}', free_regenerations_used=used)
        if kind == 'image':
            item['request']['input']['parameters'] = {
                'platform': 'taobao', 'output_type': ['main_image', 'detail_page'][index]}
    if kind == 'image':
        from app.quick_generation.service import CatalogService

        CatalogService(None).list_agents()[0].kind = 'image'
    row.state['current'][kind] = 'original'
    row.state['pending_batch'] = None
    monkeypatch.setattr(svc, 'task', lambda *args: SimpleNamespace(
        state='SUCCEEDED', settlement_state='CONSUMED'))
    return svc, row


@pytest.mark.parametrize('kind', ['copy', 'image'])
@pytest.mark.parametrize('used,free', [(0, True), (1, True), (2, True), (3, False)])
def test_single_regeneration_preserves_order_inputs_and_sibling_counts(
    monkeypatch, kind, used, free,
):
    from copy import deepcopy

    from app.quick_generation.schemas import QuickPrepare

    svc, row = regeneration_preparation(monkeypatch, kind=kind, used=used)
    original = deepcopy(row.state['batches'][0])
    batch = svc.prepare(None, row, QuickPrepare(version=1, kind=kind, item_index=0))
    assert batch['items'][1] == original['items'][1]
    replacement = batch['items'][0]
    assert replacement['task_id'] is None
    assert replacement['request']['input'] == original['items'][0]['request']['input']
    assert replacement['regeneration_of'] == 'old-0'
    assert replacement['free_regeneration'] is free
    assert replacement['free_regenerations_used'] == used
    assert replacement['request']['confirmed_quote']['credits'] == (10 if kind == 'copy' else 20)
    assert row.state['batches'][0] == original


@pytest.mark.parametrize('used,want_free,want_used', [(0, True, 1), (2, True, 3), (3, False, 3)])
def test_submit_regeneration_counts_once_and_retains_other_edited_copy(
    monkeypatch, used, want_free, want_used,
):
    from app.quick_generation.schemas import QuickPrepare

    svc, row = regeneration_preparation(monkeypatch, used=used)
    batch = svc.prepare(None, row, QuickPrepare(version=1, kind='copy', item_index=1))
    admissions = []

    def admit(principal, key, request, **kwargs):
        admissions.append(kwargs.get('free_regeneration', False))
        return SimpleNamespace(task=SimpleNamespace(task_id='new-task'))

    monkeypatch.setattr('app.quick_generation.service.AdmissionService',
                        lambda *args: SimpleNamespace(admit_task=admit))
    svc.submit(None, row, batch['id'])
    svc.submit(None, row, batch['id'])
    items = row.state['batches'][-1]['items']
    assert admissions == [want_free]
    assert items[0]['free_regenerations_used'] == used
    assert items[1]['free_regenerations_used'] == want_used
    assert row.state['draft']['copy_texts'] == {'宣传文案': '已编辑宣传'}
    assert row.state['draft']['copy_text'] == '【宣传文案】\n已编辑宣传'
    assert row.state['confirmed_copy'] is None


def test_cancelled_regeneration_keeps_original_count_and_current_result(monkeypatch):
    from app.quick_generation.schemas import QuickPrepare

    svc, row = regeneration_preparation(monkeypatch, used=2)
    batch = svc.prepare(None, row, QuickPrepare(version=1, kind='copy', item_index=0))
    svc.cancel_batch(row, batch['id'])
    assert row.state['current']['copy'] == 'original'
    assert row.state['batches'][0]['items'][0]['free_regenerations_used'] == 2
    assert row.state['draft']['copy_texts']['宣传文案'] == '已编辑宣传'
    with pytest.raises(HTTPException):
        svc.submit(None, row, batch['id'])


@pytest.mark.parametrize('kind,index', [('copy', 2), ('image', 2), ('video', 0)])
def test_single_regeneration_rejects_invalid_target(monkeypatch, kind, index):
    from app.quick_generation.schemas import QuickPrepare

    svc, row = regeneration_preparation(monkeypatch)
    with pytest.raises(HTTPException):
        svc.prepare(None, row, QuickPrepare(version=1, kind=kind, item_index=index))


def test_regeneration_dto_never_accepts_client_free_entitlement():
    from pydantic import ValidationError

    from app.quick_generation.schemas import QuickPrepare

    with pytest.raises(ValidationError):
        QuickPrepare(version=1, kind='copy', item_index=0, free_regeneration=True)


def test_failed_regeneration_admission_keeps_usage_and_original_current_result(monkeypatch):
    from copy import deepcopy

    from app.quick_generation.schemas import QuickPrepare

    svc, row = regeneration_preparation(monkeypatch, used=2)
    batch = svc.prepare(None, row, QuickPrepare(version=1, kind='copy', item_index=0))
    before = deepcopy(row.state)

    def reject(*args, **kwargs):
        raise HTTPException(402)

    monkeypatch.setattr('app.quick_generation.service.AdmissionService',
                        lambda *args: SimpleNamespace(admit_task=reject))
    with pytest.raises(HTTPException):
        svc.submit(None, row, batch['id'])
    assert row.state == before
    assert row.state['current']['copy'] == 'original'


@pytest.mark.parametrize('kind,price', [('copy', 10), ('image', 20)])
def test_each_regeneration_chain_keeps_three_free_uses_after_paid_regeneration(monkeypatch, kind, price):
    from app.quick_generation.schemas import QuickPrepare

    svc, row = regeneration_preparation(monkeypatch, kind=kind)
    charges = []

    def admit(principal, key, request, **kwargs):
        charges.append(0 if kwargs.get('free_regeneration') else request.confirmed_quote.credits)
        return SimpleNamespace(task=SimpleNamespace(task_id=f'task-{len(charges)}'))

    monkeypatch.setattr('app.quick_generation.service.AdmissionService',
                        lambda *args: SimpleNamespace(admit_task=admit))
    for _ in range(5):
        batch = svc.prepare(None, row, QuickPrepare(version=1, kind=kind, item_index=0))
        svc.submit(None, row, batch['id'])
        svc.submit(None, row, batch['id'])  # A repeated receipt never consumes another use.
    assert charges == [0, 0, 0, price, price]
    assert row.state['batches'][-1]['items'][0]['free_regenerations_used'] == 3
    assert row.state['batches'][-1]['items'][1]['free_regenerations_used'] == 0


@pytest.mark.parametrize('step', [3, 5])
def test_view_keeps_successful_image_versions_after_regeneration(monkeypatch, step):
    from copy import deepcopy
    from app.common.types import TaskView
    from app.quick_generation.schemas import QuickSummary
    from app.tasks.schemas import TaskDetail

    svc, row = regeneration_preparation(monkeypatch, kind='image')
    original = row.state['batches'][0]
    current = deepcopy(original)
    current['id'] = 'current'
    current['items'][0]['task_id'] = 'new-main'
    cancelled = deepcopy(current)
    cancelled.update(id='cancelled', submitted=False)
    cancelled['items'][0]['task_id'] = None
    failed = deepcopy(original)
    failed.update(id='failed')
    failed['items'] = [{**failed['items'][0], 'task_id': 'failed-old'}]
    row.state['batches'] += [failed, current, cancelled]
    row.state['current']['image'] = 'current'
    row.state['step'] = step
    before = deepcopy(row.state)
    principal = SimpleNamespace(user_id=uuid4())
    monkeypatch.setattr(svc, 'summary', lambda _: QuickSummary(
        run_id=uuid4(), conversation_id=uuid4(), title='商品', step=step, version=1))
    monkeypatch.setattr(svc, 'task', lambda _, key: SimpleNamespace(
        id=key, state='FAILED' if key == 'failed-old' else 'SUCCEEDED'))
    reads = []

    def read_task(owner, key):
        assert owner is principal
        reads.append(key)
        return TaskDetail.model_construct(task=TaskView.model_construct(task_id=key))

    monkeypatch.setattr('app.quick_generation.service.TaskRepository',
                        lambda _: SimpleNamespace(read_task=read_task))
    result = svc.view(principal, row)
    assert set(result.tasks) == {'old-0', 'old-1', 'new-main'}
    assert sorted(reads) == ['new-main', 'old-0', 'old-1']
    assert row.state == before


def test_legacy_image_output_subset_keeps_existing_free_usage_and_item_order(monkeypatch):
    from app.quick_generation.schemas import QuickPrepare

    svc, row = regeneration_preparation(monkeypatch, kind='image', used=3)
    batch = svc.prepare(None, row, QuickPrepare(version=1, kind='image', outputs=['main_image']))
    assert [item['request']['input']['parameters']['output_type']
            for item in batch['items']] == ['main_image', 'detail_page']
    assert batch['items'][0]['free_regenerations_used'] == 3
    assert batch['items'][1]['task_id'] == 'old-1'
