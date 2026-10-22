"""Free quick-generation admission retains normal gates and auditable zero settlement."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException


@pytest.fixture
def free_admission(monkeypatch):
    from app.catalog.schemas import PriceVersion
    from app.common.types import Quote, SubmitTaskRequest
    from app.tasks import admission
    from app.tasks.models import TaskSnapshot

    owner, agent_id, conversation = uuid4(), uuid4(), uuid4()
    quote = Quote(spec_id=agent_id, spec_version='v1', price_version='p1', agent_version='v1',
                  credits=30, input_digest='input', policy_versions={'platform-pricing': 'p1'})
    price = PriceVersion(spec_id=agent_id, version='p1', credits=30, enabled=True,
                         policy_version='platform-parameters')
    request = SubmitTaskRequest(
        conversation_id=conversation, agent_id=agent_id,
        input=dict(product_version='product', product={'name': '原商品'}, instruction='原指令',
                   material_versions=[], parameters={}), confirmed_quote=quote,
    )
    agent = SimpleNamespace(agent_id=agent_id, version='v1', protocol_version='mock-copy-v1',
                            kind='copy', policy_versions={}, model_dump=lambda **kw: {})
    spec = SimpleNamespace(spec_id=agent_id, version='v1', model_dump=lambda **kw: {})

    def validate(confirmed, input):
        if confirmed != quote:
            raise HTTPException(409)
        return SimpleNamespace(quote=quote, price=price, agent=agent, spec=spec)

    monkeypatch.setattr(admission, 'CatalogService', lambda *a, **kw: SimpleNamespace(
        validate_confirmed_quote=validate))
    policies = {
        'D-01': {'agents': {str(agent_id): {'protocol_version': 'mock-copy-v1'}}},
        'D-05': {'generation': {'max_concurrent_tasks': None, 'enforcement_ref': 'test'}},
        'D-10': {'generation': {
            'account_quota_bytes': 10000, 'server_budget_bytes': 100000,
            'reservation_seconds': 120, 'estimation_ref': 'estimate',
            'reclamation_ref': 'test', 'alert_ref': 'test', 'allowed_download_sources': ['test'],
            'max_download_bytes': 1000, 'download_timeout_seconds': 10, 'max_redirects': 0,
            'link_validity_ref': 'test', 'recovery_ref': 'test',
        }},
    }
    monkeypatch.setattr(admission, 'PolicyService', lambda *a: SimpleNamespace(
        require_feature=lambda *a: SimpleNamespace(decision_versions={}),
        _read=lambda decision, version: SimpleNamespace(payload=policies[decision])))
    monkeypatch.setattr(admission, 'authenticate', lambda *a: None)
    monkeypatch.setattr(admission, 'owned_conversation', lambda *a: None)
    monkeypatch.setattr(admission, 'locked_account', lambda *a: SimpleNamespace(available=0))
    monkeypatch.setattr(admission, 'LocalStore', lambda *a: SimpleNamespace(
        require_space=lambda *a: None, free_bytes=100000))
    monkeypatch.setattr(admission, 'capacity_policy', lambda *a: None)
    monkeypatch.setattr(admission, 'lock_capacity', lambda *a: None)
    monkeypatch.setattr(admission, 'reserve_capacity',
                        lambda *a, **kw: SimpleNamespace(id='capacity'))
    monkeypatch.setattr(admission, 'enqueue_outbox', lambda *a: None)
    monkeypatch.setattr(admission, 'append_durable_event', lambda *a, **kw: None)
    frozen, rows = [], []
    monkeypatch.setattr(admission, 'freeze_credits', lambda *a: frozen.append(a[-1]))
    session = Mock()
    session.scalar.side_effect = [
        None, SimpleNamespace(version='product', product={'name': '原商品'})]
    session.add.side_effect = rows.append

    def view(session, task):
        snapshot = next(row for row in rows if isinstance(row, TaskSnapshot))
        return dict(task_id=task.id, display_number='T20261020-000001', state=task.state,
                    state_version=1, settlement_state=task.settlement_state, quote=snapshot.quote,
                    work_ids=[], investigation_reason=None, created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC))

    monkeypatch.setattr(admission, 'task_view', view)
    settings = SimpleNamespace(mode='mock', test_only=True, generation_policy_versions={
        'D-01': 'v1', 'D-05': 'v1', 'D-10': 'v1'}, storage_persistent=True,
        generation_capacity_estimates={str(agent_id): dict(spec_version='v1',
            policy_version='v1', estimation_ref='estimate', total_bytes=100)}, storage_root='test')
    return (admission.AdmissionService(session, settings), SimpleNamespace(user_id=owner),
            request, rows, frozen)


def test_free_admission_needs_no_balance_and_snapshots_actual_zero_charge(free_admission):
    from app.tasks.models import TaskSnapshot

    service, principal, request, rows, frozen = free_admission
    result = service.admit_task(principal, 'quick:run:batch:0', request, free_regeneration=True)
    snapshot = next(row for row in rows if isinstance(row, TaskSnapshot))
    assert result.task.quote.credits == 0
    assert frozen == [0]
    assert snapshot.quote['credits'] == snapshot.price_snapshot['credits'] == 0
    assert snapshot.price_snapshot['standard_quote']['credits'] == 30
    assert request.confirmed_quote.credits == 30


def test_free_admission_still_rejects_tampered_standard_quote(free_admission):
    service, principal, request, rows, frozen = free_admission
    request.confirmed_quote = request.confirmed_quote.model_copy(update={'credits': 0})
    with pytest.raises(HTTPException) as error:
        service.admit_task(principal, 'quick:run:batch:0', request, free_regeneration=True)
    assert error.value.status_code == 409
    assert not rows and not frozen


def test_normal_admission_still_requires_full_balance(free_admission):
    from app.ledger.service import LedgerError

    service, principal, request, rows, frozen = free_admission
    with pytest.raises(LedgerError) as error:
        service.admit_task(principal, 'normal', request)
    assert error.value.code == 'INSUFFICIENT_CREDITS'
    assert not rows and not frozen


@pytest.mark.parametrize('used, charge', [(0, 0), (1, 0), (2, 0), (3, 30)])
def test_ordinary_confirmed_regeneration_persists_chain_and_actual_charge(
    free_admission, monkeypatch, used, charge,
):
    from app.common.types import RegenerationConfirmation
    from app.tasks import admission, regeneration
    from app.tasks.models import GenerationTask, TaskSnapshot

    service, principal, request, rows, frozen = free_admission
    source_id = str(uuid4())
    source = SimpleNamespace(id=source_id, user_id=str(principal.user_id),
        conversation_id=str(uuid4()), agent_id=str(request.agent_id), state='SUCCEEDED')
    snapshot = SimpleNamespace(input_snapshot=request.input.model_dump(mode='json'),
        agent_snapshot={'kind': 'copy'}, price_snapshot={})
    service.session.scalar.side_effect = [None,
        SimpleNamespace(version='product', product={'name': '原商品'}), source, None]
    service.session.get.return_value = snapshot
    service.session.scalars.return_value.all.return_value = [used]
    monkeypatch.setattr(regeneration, 'authenticate', lambda *a: None)
    monkeypatch.setattr(admission, 'locked_account', lambda *a: SimpleNamespace(available=charge))
    request.regeneration = RegenerationConfirmation(
        source_task_id=source_id, expected_credits=charge, expected_used=used)

    result = service.admit_task(principal, 'ordinary-regeneration', request)
    stored = next(row for row in rows if isinstance(row, TaskSnapshot))
    assert frozen == [charge]
    assert stored.quote['credits'] == stored.price_snapshot['credits'] == charge
    assert stored.price_snapshot['regeneration'] == dict(root_task_id=source_id,
        source_task_id=source_id, free_regenerations_used=min(used + 1, 3))
    assert result.task.quote.credits == charge

    # Even after an allowance is used, replay returns before consulting the count.
    accepted = next(row for row in rows if isinstance(row, GenerationTask))
    service.session.scalar.side_effect = [accepted]
    replay = service.admit_task(principal, 'ordinary-regeneration', request)
    assert replay.replayed and replay.task.task_id == result.task.task_id
    assert frozen == [charge]


def test_old_submission_hash_survives_optional_regeneration_contract(free_admission):
    from app.catalog.schemas import content_digest
    from app.tasks.models import GenerationTask

    service, principal, request, rows, frozen = free_admission
    old_payload = request.model_dump(mode='json')
    old_payload.pop('regeneration')
    # Use the same trusted quick entitlement to avoid changing the fixture balance.
    service.admit_task(principal, 'legacy-key', request, free_regeneration=True)
    accepted = next(row for row in rows if isinstance(row, GenerationTask))
    assert accepted.request_hash == content_digest(
        {'request': old_payload, 'free_regeneration': True})
