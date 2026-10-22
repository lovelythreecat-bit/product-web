from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.catalog.schemas import AgentVersion
from app.catalog.service import CatalogError, CatalogService
from app.common.types import InputSnapshot


def test_parameter_update_rejects_fraction_negative_bool_and_overflow():
    from app.catalog.parameters import ParameterConfigUpdate

    for value in (-1, 1.5, True, 2**53):
        with pytest.raises(ValidationError):
            ParameterConfigUpdate(
                expected_version=None, text_price=value, image_price=None, video_price=None
            )


def test_parameter_save_preserves_zero_cas_and_audit():
    from app.catalog.models import ParameterConfig, ParameterHead
    from app.catalog.parameters import ParameterConfigUpdate, read_parameters, update_parameters

    head = SimpleNamespace(version=None)
    records = {}
    audit = []

    def get(table, key, **kw):
        return head if table is ParameterHead else records.get(str(key))

    def add(row):
        if isinstance(row, ParameterConfig):
            records[row.version] = row
        else:
            audit.append(row)

    session = SimpleNamespace(get=get, add=add, flush=lambda: None)
    initial = read_parameters(session, "mock")
    assert initial.text_price is None and initial.version is None
    dto = ParameterConfigUpdate(
        expected_version=None, text_price=0, image_price=7, video_price=None
    )
    saved = update_parameters(session, "mock", dto, uuid4())
    assert read_parameters(session, "mock").text_price == 0
    assert saved.image_price == 7 and saved.video_price is None
    assert audit[0].action == "generation_parameters"
    assert audit[0].changes["text_price"] == 0
    with pytest.raises(HTTPException) as error:
        update_parameters(session, "mock", dto, uuid4())
    assert error.value.status_code == 409
    assert len(records) == 1


def agent():
    return AgentVersion(
        agent_id=uuid4(),
        version="v1",
        kind="copy",
        name="文本",
        mode="mock",
        test_only=True,
        enabled=True,
        protocol_version="v1",
        input_support=dict(
            product_required_fields=["name"],
            instruction_required=False,
            min_materials=0,
            max_materials=0,
        ),
        policy_versions={},
        secret_configured=True,
    )


def test_kind_quote_requires_configuration_and_invalidates_after_price_change(monkeypatch):
    from app.catalog import parameters

    current = SimpleNamespace(version=str(uuid4()), text_price=None, image_price=3, video_price=9)
    monkeypatch.setattr(parameters, "read_parameters", lambda *a, **kw: current)
    selected = agent()
    catalog = CatalogService(None, mode="mock")
    monkeypatch.setattr(catalog, "_principal", lambda *a, **kw: None)
    monkeypatch.setattr(catalog, "_current_agent", lambda *a: selected)
    monkeypatch.setattr(catalog, "_agent_gate", lambda *a: None)
    value = InputSnapshot(
        product_version="p1",
        product={"name": "商品"},
        instruction="",
        parameters={},
        material_versions=[],
    )
    with pytest.raises(CatalogError):
        catalog.quote_agent(None, value, selected.agent_id)
    current.text_price = 0
    old = catalog.quote_agent(None, value, selected.agent_id)
    assert old.credits == 0
    assert catalog.validate_confirmed_quote(old, value).quote == old
    current.version = str(uuid4())
    current.text_price = 8
    with pytest.raises(CatalogError) as error:
        catalog.validate_confirmed_quote(old, value)
    assert error.value.code == "QUOTE_STALE"
    assert error.value.current_quotes[0].credits == 8
    assert old.credits == 0
    value.parameters = {"old_spec_option": 1}
    with pytest.raises(CatalogError):
        catalog.quote_agent(None, value, selected.agent_id)


def test_legacy_new_intent_is_stale_even_if_old_spec_is_still_enabled():
    from app.common.types import Quote

    value = InputSnapshot(
        product_version="p1",
        product={"name": "商品"},
        instruction="",
        parameters={},
        material_versions=[],
    )
    quote = Quote(
        spec_id=uuid4(),
        spec_version="legacy",
        price_version="old",
        agent_version="v1",
        policy_versions={},
        credits=4,
        input_digest="old",
    )
    with pytest.raises(CatalogError) as error:
        CatalogService(None).validate_confirmed_quote(quote, value)
    assert error.value.code == "QUOTE_STALE"


@pytest.mark.parametrize(('output_type', 'expected'), [
    ('main_image', 7), ('detail_page', 21), ('pdd_white_background', 7), ('long_image', 7),
])
def test_image_quote_charges_each_delivered_image(monkeypatch, output_type, expected):
    from app.catalog import parameters
    current = SimpleNamespace(version=str(uuid4()), image_price=7)
    monkeypatch.setattr(parameters, 'read_parameters', lambda *a, **kw: current)
    selected = agent().model_copy(update={'kind': 'image', 'protocol_version': 'image-agent-v1'})
    catalog = CatalogService(None, mode='mock')
    monkeypatch.setattr(catalog, '_current_agent', lambda *a: selected)
    value = InputSnapshot(product_version='p1', product={'name': '商品', 'category': '茶具'},
                          instruction='',
                          parameters={'platform': 'taobao', 'output_type': output_type},
                          material_versions=[])
    validated = catalog._agent_quote(value, selected.agent_id)
    assert validated.quote.credits == expected
    assert validated.price.credits == expected
    assert catalog.validate_confirmed_quote(validated.quote, value).quote == validated.quote


def test_unaccepted_detail_quote_must_reconfirm_three_image_price(monkeypatch):
    from app.catalog import parameters

    current = SimpleNamespace(version=str(uuid4()), image_price=7)
    monkeypatch.setattr(parameters, 'read_parameters', lambda *a, **kw: current)
    selected = agent().model_copy(update={'kind': 'image', 'protocol_version': 'image-agent-v1'})
    catalog = CatalogService(None, mode='mock')
    monkeypatch.setattr(catalog, '_current_agent', lambda *a: selected)
    value = InputSnapshot(product_version='p1', product={'name': '商品', 'category': '茶具'},
                          instruction='',
                          parameters={'platform': 'taobao', 'output_type': 'detail_page'},
                          material_versions=[])
    old = catalog._agent_quote(value, selected.agent_id).quote.model_copy(update={'credits': 7})

    with pytest.raises(CatalogError) as error:
        catalog.validate_confirmed_quote(old, value)

    assert error.value.code == 'QUOTE_STALE'
    assert error.value.current_quotes[0].credits == 21


def test_free_detail_image_price_remains_zero(monkeypatch):
    from app.catalog import parameters

    monkeypatch.setattr(parameters, 'read_parameters', lambda *a, **kw: SimpleNamespace(
        version=str(uuid4()), image_price=0))
    selected = agent().model_copy(update={'kind': 'image', 'protocol_version': 'image-agent-v1'})
    catalog = CatalogService(None, mode='mock')
    monkeypatch.setattr(catalog, '_current_agent', lambda *a: selected)
    value = InputSnapshot(product_version='p1', product={'name': '商品'}, instruction='',
                          parameters={'platform': 'taobao', 'output_type': 'detail_page'},
                          material_versions=[])

    validated = catalog._agent_quote(value, selected.agent_id)

    assert validated.quote.credits == validated.price.credits == 0


def test_quick_image_batch_quotes_three_detail_images_and_single_siblings(monkeypatch):
    from app.catalog import parameters
    from app.quick_generation.schemas import QuickDraft, QuickPrepare
    from app.quick_generation.service import QuickGenerationService

    monkeypatch.setattr(parameters, 'read_parameters', lambda *a, **kw: SimpleNamespace(
        version=str(uuid4()), image_price=7))
    selected = agent().model_copy(update={'kind': 'image', 'protocol_version': 'image-agent-v1'})
    catalog = CatalogService(None, mode='mock')
    monkeypatch.setattr(catalog, '_current_agent', lambda *a: selected)
    monkeypatch.setattr(catalog, '_principal', lambda *a: None)
    monkeypatch.setattr(catalog, 'list_agents', lambda: [selected])
    monkeypatch.setattr('app.quick_generation.service.CatalogService', lambda *a, **kw: catalog)
    product = SimpleNamespace(version=str(uuid4()), product={'name': '商品', 'category': '茶具'})
    draft = QuickDraft(product_version=product.version, image_platform='taobao',
                       image_outputs=['main_image', 'detail_page', 'long_image'])
    row = SimpleNamespace(version=1, conversation_id=str(uuid4()), state={
        'step': 3, 'draft': draft.model_dump(mode='json'), 'confirmed_copy': '确认后的文案',
        'current': {'copy': None, 'image': None, 'video': None}, 'batches': [],
        'pending_batch': None,
    })
    service = QuickGenerationService(None, SimpleNamespace(mode='mock'))
    monkeypatch.setattr(service, 'product', lambda *a: product)
    monkeypatch.setattr(service, 'current_tasks', lambda *a: [])
    monkeypatch.setattr(service, 'change', lambda row, state: setattr(row, 'state', state))

    batch = service.prepare(None, row, QuickPrepare(version=1, kind='image'))

    assert [item['request']['confirmed_quote']['credits'] for item in batch['items']] == [7, 21, 7]
    assert sum(item['request']['confirmed_quote']['credits'] for item in batch['items']) == 35


def test_detail_image_quote_freezes_and_consumes_three_prices_once(monkeypatch):
    from contextlib import nullcontext
    from datetime import timedelta

    from app.catalog import parameters
    from app.dispatch.consumer import Lease
    from app.ledger import service as ledger
    from app.ledger.models import CreditLedger, CreditReservation
    from app.tasks.models import GenerationTask
    from app.tasks.state_machine import (
        TransitionEvidence,
        TransitionVerifiers,
        VerifiedTransition,
    )

    monkeypatch.setattr(parameters, 'read_parameters', lambda *a, **kw: SimpleNamespace(
        version=str(uuid4()), image_price=7))
    selected = agent().model_copy(update={'kind': 'image', 'protocol_version': 'image-agent-v1'})
    catalog = CatalogService(None, mode='mock')
    monkeypatch.setattr(catalog, '_current_agent', lambda *a: selected)
    value = InputSnapshot(product_version='p1', product={'name': '商品'}, instruction='',
                          parameters={'platform': 'taobao', 'output_type': 'detail_page'},
                          material_versions=[])
    validated = catalog._agent_quote(value, selected.agent_id)
    snapshot = SimpleNamespace(quote=validated.quote.model_dump(mode='json'),
                               price_snapshot=validated.price.model_dump(mode='json'))
    current = datetime.now(UTC).replace(tzinfo=None)
    task = SimpleNamespace(id=str(uuid4()), user_id=str(uuid4()), state='SAVING',
        settlement_state='FROZEN', agent_id=str(selected.agent_id), agent_version='v1',
        external_submission_id='submission', upstream_id=None, lease_owner='worker',
        fencing_token=1, lease_expires_at=current + timedelta(minutes=1))
    account = SimpleNamespace(available=100, frozen=0, consumed=0)
    reservations, entries = [], []

    def scalar(query):
        model = query.column_descriptions[0]['entity']
        if model is GenerationTask:
            return task
        if model is CreditReservation:
            return reservations[0] if reservations else None
        return next((row for row in entries if row.operation_key == f'settle:{task.id}'), None)

    def add(row):
        (reservations if isinstance(row, CreditReservation) else entries).append(row)

    proof = VerifiedTransition(task.id, task.agent_id, task.agent_version,
        task.external_submission_id, 'publication', 'saved:original', 'image-agent-v1')
    session = SimpleNamespace(scalar=scalar, add=add, flush=lambda: None,
        get=lambda *a: snapshot, begin_nested=nullcontext,
        info={'transition_verifiers': TransitionVerifiers({'publication': lambda *a: proof})})
    monkeypatch.setattr(ledger, 'locked_account', lambda *a: account)
    monkeypatch.setattr(ledger, 'lock_task_resources',
        lambda *a: (task, account, reservations[0]))
    monkeypatch.setattr('app.dispatch.recovery.database_now', lambda *a: current)

    ledger.freeze_credits(session, task.user_id, task.id, validated.quote.credits)
    ledger.freeze_credits(session, task.user_id, task.id, validated.quote.credits)
    assert ledger.balances(account) == {'available': 79, 'frozen': 21, 'consumed': 0}
    evidence = TransitionEvidence(Lease(task.id, 'worker', 1, task.lease_expires_at),
                                  'saved:original')
    receipt = ledger.settle_credits(session, task.id, evidence)
    task.state = 'SUCCEEDED'
    replay = ledger.settle_credits(session, task.id, evidence)

    assert receipt.amount == replay.amount == 21
    assert receipt.changed and not replay.changed
    assert ledger.balances(account) == {'available': 79, 'frozen': 0, 'consumed': 21}
    assert [(row.kind, row.amount) for row in entries if isinstance(row, CreditLedger)] == [
        ('freeze', 21), ('consume', 21)]


@pytest.fixture
def parameter_api(monkeypatch):
    from fastapi.testclient import TestClient

    from app.admin import routes
    from app.auth.routes import get_session, require_active_principal, require_csrf
    from app.catalog.models import ParameterConfig, ParameterHead
    from app.config import Settings
    from app.main import create_app

    head = SimpleNamespace(version=None)
    records, audits = {}, []

    def get(table, key, **kwargs):
        return head if table is ParameterHead else records.get(str(key))

    def add(row):
        if isinstance(row, ParameterConfig):
            records[row.version] = row
        else:
            audits.append(row)

    session = SimpleNamespace(
        get=get, add=add, flush=lambda: None, rollback=lambda: None, commit=lambda: None
    )
    app = create_app(Settings())
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[require_active_principal] = lambda: SimpleNamespace(user_id=uuid4())
    app.dependency_overrides[require_csrf] = lambda: None
    monkeypatch.setattr(routes, "authorize_admin", lambda *a: None)
    return TestClient(app), app, records, audits


def test_parameter_api_reloads_persisted_prices_and_rejects_stale_edits(parameter_api):
    client, _, records, audits = parameter_api
    assert client.get("/api/v1/admin/parameter-config").json()["text_price"] is None
    body = dict(expected_version=None, text_price=0, image_price=3, video_price=10)
    response = client.patch("/api/v1/admin/parameter-config", json=body)
    assert response.status_code == 200
    assert client.get("/api/v1/admin/parameter-config").json() == response.json()
    assert client.patch("/api/v1/admin/parameter-config", json=body).status_code == 409
    assert len(records) == 1 and len(audits) == 1


def test_parameter_api_enforces_live_admin_and_csrf_before_write(parameter_api, monkeypatch):
    from app.admin import routes
    from app.auth.routes import require_csrf

    client, app, records, audits = parameter_api
    body = dict(expected_version=None, text_price=0, image_price=None, video_price=None)

    def deny(*args):
        raise HTTPException(403)

    monkeypatch.setattr(routes, "authorize_admin", deny)
    assert client.get("/api/v1/admin/parameter-config").status_code == 403
    assert client.patch("/api/v1/admin/parameter-config", json=body).status_code == 403
    monkeypatch.setattr(routes, "authorize_admin", lambda *a: None)

    def deny_csrf():
        raise HTTPException(403)

    app.dependency_overrides[require_csrf] = deny_csrf
    assert client.patch("/api/v1/admin/parameter-config", json=body).status_code == 403
    assert not records and not audits


def test_removed_spec_and_price_endpoints_are_not_published(parameter_api):
    _, app, _, _ = parameter_api
    paths = app.openapi()["paths"]
    assert "/api/v1/admin/specs" not in paths
    assert "/api/v1/admin/prices" not in paths
    assert "/api/v1/agents/{agent_id}/specs" not in paths


def test_original_admitted_intent_replays_without_using_new_prices(monkeypatch):
    from app.common.types import SubmitTaskRequest
    from app.tasks import admission

    owner, conversation, selected = uuid4(), uuid4(), uuid4()
    request = SubmitTaskRequest(
        conversation_id=conversation,
        agent_id=selected,
        input=dict(
            product_version="p",
            product={"name": "原商品"},
            instruction="原要求",
            parameters={"legacy": 1},
            material_versions=[],
        ),
        confirmed_quote=dict(
            spec_id=uuid4(),
            spec_version="old",
            price_version="old",
            agent_version="old",
            policy_versions={},
            credits=7,
            input_digest="old",
        ),
    )
    task_id = uuid4()
    # This admitted request predates the optional regeneration field. Its stored
    # hash must use the original payload, not a newly defaulted null field.
    original_payload = request.model_dump(mode="json", exclude={"regeneration"})
    row = SimpleNamespace(request_hash=admission.content_digest(original_payload))
    session = SimpleNamespace(scalar=lambda *a: row)
    monkeypatch.setattr(admission, "authenticate", lambda *a: None)
    monkeypatch.setattr(
        admission,
        "task_view",
        lambda *a: dict(
            task_id=task_id,
            display_number="T20261016-000001",
            state="SUBMITTED",
            state_version=1,
            settlement_state="FROZEN",
            quote=request.confirmed_quote,
            work_ids=[],
            investigation_reason=None,
            created_at=datetime(2026, 10, 18, tzinfo=UTC),
            updated_at=datetime(2026, 10, 18, tzinfo=UTC),
        ),
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("replay must not reprice or refreeze")

    monkeypatch.setattr(admission.CatalogService, "validate_confirmed_quote", forbidden)
    monkeypatch.setattr(admission, "freeze_credits", forbidden)
    result = admission.AdmissionService(session, SimpleNamespace()).admit_task(
        SimpleNamespace(user_id=owner), "original-key", request
    )
    assert result.replayed is True
    assert result.task.quote.credits == 7
    assert result.task.quote.price_version == "old"


@pytest.mark.parametrize("parameters", [
    {},
    {"copy_type": "宣传文案", "platform": "淘宝", "audience": "学生",
     "tone": "自然", "max_chars": 300},
    {"copy_type": "自定义类型", "language": "简体中文", "extra_instructions": "突出场景"},
    {"length": 120, "count": 1},
])
def test_new_single_contract_result_rule_needs_no_admin_spec(monkeypatch, parameters):
    from app.agents.text import PROTOCOL, TextAgentAdapter, TextAgentProfile
    from app.results import manifest
    from app.tasks.state_machine import TransitionError

    selected = agent().model_copy(update={"protocol_version": PROTOCOL})
    catalog = CatalogService(None)
    monkeypatch.setattr(catalog, "_current_agent", lambda *a: selected)
    spec, _ = catalog.single_context(selected.agent_id)
    snapshot = SimpleNamespace(
        agent_snapshot=selected.model_dump(mode="json"),
        spec_snapshot=spec.model_dump(mode="json"),
        input_snapshot={"parameters": parameters},
        quote={"policy_versions": {"platform-pricing": str(uuid4())}},
    )
    session = SimpleNamespace(get=lambda *a: snapshot)
    task = SimpleNamespace(
        id="task", agent_id=str(selected.agent_id), agent_version=selected.version
    )
    profile = TextAgentProfile(
        base_url="http://127.0.0.1:8000",
        service_key="TEST_ONLY_key",
        model_config_id=uuid4(),
        supports_images=False,
    )
    binding = SimpleNamespace(
        protocol_version=PROTOCOL, wire_agent_id="copy", adapter=TextAgentAdapter(profile=profile)
    )
    monkeypatch.setattr(
        manifest,
        "exact_policy",
        lambda *a: {"agents": {str(selected.agent_id): {"protocol_version": PROTOCOL}}},
    )
    rule = manifest.result_rule(session, task, binding)
    assert rule["expected_item_keys"] == ["original-1"]
    assert rule["media_type"] == "text/plain"
    for invalid in ({"max_chars": True}, {"max_chars": 0}, {"tone": False},
                    {"count": 2}, {"unexpected": "x"}, None):
        snapshot.input_snapshot = {"parameters": invalid}
        with pytest.raises(TransitionError, match="RESULT_POLICY_UNAVAILABLE"):
            manifest.result_rule(session, task, binding)
    snapshot.input_snapshot = {"parameters": parameters}
    snapshot.spec_snapshot["delivery_kind"] = "multiple"
    with pytest.raises(TransitionError):
        manifest.result_rule(session, task, binding)
