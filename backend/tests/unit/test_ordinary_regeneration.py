from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError


def context(monkeypatch, *, used=0, kind='copy', matches=True):
    from app.tasks import regeneration

    owner, source, root, agent = (str(uuid4()) for _ in range(4))
    input = dict(product_version='v1', product={'name': '商品'}, instruction='原指令',
                 material_versions=[], parameters={'copy_type': '营销文案'})
    snapshot = SimpleNamespace(input_snapshot=deepcopy(input), agent_snapshot={'kind': kind},
        price_snapshot={'regeneration': {'root_task_id': root, 'free_regenerations_used': 1}})
    task = SimpleNamespace(id=source, user_id=owner, agent_id=agent,
                           conversation_id=str(uuid4()), state='SUCCEEDED')
    session = Mock()
    session.scalar.side_effect = [task, None]
    session.scalars.return_value.all.return_value = [used]
    session.get.return_value = snapshot
    monkeypatch.setattr(regeneration, 'authenticate', lambda *a: None)
    principal = SimpleNamespace(user_id=owner)
    input['product_version'] = 'new-version-with-same-facts'
    if not matches:
        input['instruction'] = '另一种任务'
    return regeneration, session, principal, task, snapshot, input


@pytest.mark.parametrize('used, credits', [(0, 0), (1, 0), (2, 0), (3, 30)])
@pytest.mark.parametrize('kind', ['copy', 'image'])
def test_three_free_uses_share_persisted_chain_not_selected_version(
    monkeypatch, used, credits, kind,
):
    module, session, principal, task, snapshot, input = context(
        monkeypatch, used=used, kind=kind)
    decision = module.RegenerationService(session).decision(
        principal, task.id, task.agent_id, input, 30)
    assert decision.credits == credits
    assert decision.free_regenerations_used == used
    assert decision.eligible is True
    assert decision.root_task_id == snapshot.price_snapshot['regeneration']['root_task_id']


@pytest.mark.parametrize('change', ['content', 'video', 'agent'])
def test_changed_content_and_video_use_standard_price(monkeypatch, change):
    module, session, principal, task, snapshot, input = context(
        monkeypatch, matches=change != 'content', kind='video' if change == 'video' else 'copy')
    decision = module.RegenerationService(session).decision(
        principal, task.id, str(uuid4()) if change == 'agent' else task.agent_id, input, 30)
    assert decision.credits == 30
    assert decision.eligible is False
    assert decision.metadata is None


def test_foreign_task_cannot_supply_entitlement(monkeypatch):
    module, session, principal, task, snapshot, input = context(monkeypatch)
    for answers, status in [([None], 404)]:
        session.scalar.side_effect = answers
        with pytest.raises(HTTPException) as error:
            module.RegenerationService(session).decision(
                principal, task.id, task.agent_id, input, 30)
        assert error.value.status_code == status


def test_quick_source_uses_standard_price_without_ordinary_entitlement(monkeypatch):
    module, session, principal, task, snapshot, input = context(monkeypatch)
    session.scalar.side_effect = [task, object()]
    decision = module.RegenerationService(session).decision(
        principal, task.id, task.agent_id, input, 30)
    assert decision.eligible is False
    assert decision.credits == 30
    assert decision.metadata is None


def test_inflight_source_cannot_be_regenerated(monkeypatch):
    module, session, principal, task, snapshot, input = context(monkeypatch)
    task.state = 'RUNNING'
    with pytest.raises(HTTPException) as error:
        module.RegenerationService(session).decision(principal, task.id, task.agent_id, input, 30)
    assert error.value.status_code == 409


def test_confirmation_rejects_changed_remaining_count_before_admission(monkeypatch):
    module, session, principal, task, snapshot, input = context(monkeypatch, used=3)
    from app.catalog.service import CatalogError
    from app.common.types import RegenerationConfirmation

    confirmation = RegenerationConfirmation(source_task_id=task.id, expected_credits=0,
                                            expected_used=2)
    with pytest.raises(CatalogError) as error:
        module.RegenerationService(session).confirm(
            principal, confirmation, task.agent_id, input, 30)
    assert error.value.status_code == 409
    assert error.value.code == 'QUOTE_STALE'


def test_confirmation_does_not_allow_client_free_flag():
    from app.common.types import RegenerationConfirmation

    with pytest.raises(ValidationError):
        RegenerationConfirmation(source_task_id=uuid4(), expected_credits=0,
                                  expected_used=0, free_regeneration=True)


def test_history_state_reads_do_not_add_locking_scans(monkeypatch):
    from sqlalchemy.dialects.mysql import dialect

    module, session, principal, task, snapshot, input = context(monkeypatch)
    session.info = {'read_only_request': True}
    module.RegenerationService(session).decision(principal, task.id, task.agent_id, input, 30)
    queries = [call.args[0] for call in session.scalar.call_args_list]
    queries.extend(call.args[0] for call in session.scalars.call_args_list)
    assert all('LOCK IN SHARE MODE' not in str(query.compile(dialect=dialect()))
               for query in queries)
