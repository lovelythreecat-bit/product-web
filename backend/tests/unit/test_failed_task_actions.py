from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException


def test_failed_task_waits_for_owner_choice_without_settling():
    from app.tasks.state_machine import failed_settlement_valid

    assert failed_settlement_valid("FROZEN", "frozen")
    assert failed_settlement_valid("RELEASED", "released")
    assert not failed_settlement_valid("CONSUMED", "consumed")
    assert not failed_settlement_valid("FROZEN", "released")


def test_release_failed_task_moves_frozen_credits_once(monkeypatch):
    from app.tasks import failed_actions as actions

    task = SimpleNamespace(id="task", user_id="owner", state="FAILED",
                           settlement_state="FROZEN", state_version=4,
                           capacity_reservation_id="capacity")
    account = SimpleNamespace(available=70, frozen=30, consumed=0)
    reservation = SimpleNamespace(id="reservation", state="frozen", amount=30, version=1)
    session = Mock()
    session.scalar.return_value = None
    session.get.return_value = SimpleNamespace(quote={"credits": 30},
                                              price_snapshot={"credits": 30})
    monkeypatch.setattr(actions, "lock_task_resources",
                        lambda *_: (task, account, reservation))
    release_capacity = Mock()
    monkeypatch.setattr(actions, "release_capacity", release_capacity)
    monkeypatch.setattr(actions, "database_now", lambda _: datetime(2026, 10, 16))
    monkeypatch.setattr(actions, "append_durable_event", Mock())
    assert actions.release_failed_hold(session, task.id)
    assert (account.available, account.frozen, account.consumed) == (100, 0, 0)
    assert reservation.state == "released" and task.settlement_state == "RELEASED"
    assert task.state == "FAILED" and task.state_version == 5
    assert not actions.release_failed_hold(session, task.id)
    assert (account.available, account.frozen, account.consumed) == (100, 0, 0)
    release_capacity.assert_called_once_with(session, "capacity")


@pytest.mark.parametrize("state", ["RUNNING", "INVESTIGATING", "SAVING", "SUCCEEDED"])
def test_owner_cannot_release_running_uncertain_or_successful_task(monkeypatch, state):
    from app.tasks import failed_actions as actions

    task = SimpleNamespace(state=state)
    monkeypatch.setattr(actions, "lock_task_resources", lambda *_: (task, None, None))
    with pytest.raises(HTTPException) as rejected:
        actions.release_failed_hold(Mock(), "task")
    assert rejected.value.status_code == 409


def test_task_view_exposes_utc_creation_and_last_state_change():
    from app.tasks.repository import task_view

    created = datetime(2026, 10, 16, 1, 2, 3)
    updated = datetime(2026, 10, 16, 1, 4, 5)
    session = Mock()
    session.scalar.side_effect = [
        SimpleNamespace(quote=dict(spec_id="11111111-1111-4111-8111-111111111111",
                                  spec_version="v1", price_version="v1", agent_version="v1",
                                  policy_versions={}, credits=30, input_digest="input")),
        updated,
    ]
    session.scalars.return_value = []
    row = SimpleNamespace(id="22222222-2222-4222-8222-222222222222",
                          display_number="T20261016-000001", state="FAILED", state_version=4,
                          settlement_state="FROZEN", investigation_reason=None, created_at=created)
    view = task_view(session, row)
    assert view.created_at == created.replace(tzinfo=UTC)
    assert view.updated_at == updated.replace(tzinfo=UTC)


def test_retry_replays_existing_successor_without_releasing_or_admitting_again(monkeypatch):
    from app.common.types import TaskView
    from app.tasks import failed_actions as actions

    service = actions.FailedTaskActions(Mock(), Mock())
    original = SimpleNamespace(id="original", state="FAILED", settlement_state="RELEASED")
    successor = object()
    view = TaskView(
        task_id=uuid4(), display_number="T20261016-000002", state="RUNNING", state_version=2,
        settlement_state="FROZEN", work_ids=[], investigation_reason=None,
        quote=dict(spec_id=uuid4(), spec_version="v", price_version="v", agent_version="v",
                   credits=30, input_digest="input", policy_versions={}),
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )
    service._owned = Mock(return_value=original)
    service._successor = Mock(return_value=successor)
    monkeypatch.setattr(actions, "task_view", lambda session, task: view)
    release = Mock()
    admit = Mock()
    monkeypatch.setattr(actions, "release_failed_hold", release)
    monkeypatch.setattr(actions, "AdmissionService", admit)
    result = service.retry(Mock(), "original")
    assert result.replayed and result.task.task_id == view.task_id
    release.assert_not_called()
    admit.assert_not_called()


def test_release_loses_to_committed_retry_without_touching_successor(monkeypatch):
    from app.tasks import failed_actions as actions

    service = actions.FailedTaskActions(Mock(), Mock())
    service._owned = Mock(return_value=SimpleNamespace(id="original"))
    service._successor = Mock(return_value=SimpleNamespace(id="successor"))
    release = Mock()
    monkeypatch.setattr(actions, "release_failed_hold", release)
    with pytest.raises(HTTPException) as denied:
        service.release(Mock(), "original")
    assert denied.value.status_code == 409
    release.assert_not_called()


def test_retry_loses_to_committed_owner_release(monkeypatch):
    from app.tasks import failed_actions as actions

    service = actions.FailedTaskActions(Mock(), Mock())
    service._owned = Mock(return_value=SimpleNamespace(
        id="original", state="FAILED", settlement_state="RELEASED"))
    service._successor = Mock(return_value=None)
    release = Mock()
    monkeypatch.setattr(actions, "release_failed_hold", release)
    with pytest.raises(HTTPException) as denied:
        service.retry(Mock(), "original")
    assert denied.value.status_code == 409
    release.assert_not_called()


def test_retry_passes_exact_original_snapshot_to_normal_admission(monkeypatch):
    from app.tasks import failed_actions as actions

    session, settings, principal = Mock(), Mock(), Mock()
    original = SimpleNamespace(id=str(uuid4()), conversation_id=str(uuid4()),
                               agent_id=str(uuid4()), state="FAILED", settlement_state="FROZEN")
    snapshot = SimpleNamespace(
        input_snapshot=dict(product_version="original-product", product={"name": "原商品"},
                            instruction="原指令", material_versions=[], parameters={}),
        quote=dict(spec_id=str(uuid4()), spec_version="v1", price_version="price1",
                   agent_version="agent1", credits=30, input_digest="digest", policy_versions={}),
    )
    session.get.return_value = snapshot
    service = actions.FailedTaskActions(session, settings)
    service._owned = Mock(return_value=original)
    service._successor = Mock(return_value=None)
    order = []
    monkeypatch.setattr(actions, "release_failed_hold", lambda *args: order.append("release"))
    admission = Mock()

    def admit(actor, key, request):
        order.append("admit")
        assert actor is principal
        assert key == actions.successor_key(original.id)
        assert request.input.model_dump(mode="json") == snapshot.input_snapshot
        assert request.confirmed_quote.model_dump(mode="json") == snapshot.quote
        return "accepted"

    admission.admit_task.side_effect = admit
    monkeypatch.setattr(actions, "AdmissionService", lambda source, config: admission)
    assert service.retry(principal, original.id) == "accepted"
    assert order == ["release", "admit"]
    session.commit.assert_not_called()


def test_owner_checks_do_not_disclose_another_users_task(monkeypatch):
    from app.tasks import failed_actions as actions

    session = Mock()
    session.scalar.return_value = None
    monkeypatch.setattr(actions, "authenticate", Mock())
    principal = SimpleNamespace(user_id=uuid4())
    with pytest.raises(HTTPException) as denied:
        actions.FailedTaskActions(session, Mock())._owned(principal, uuid4())
    assert denied.value.status_code == 404
    sql = str(session.scalar.call_args.args[0])
    assert "generation_tasks.user_id =" in sql


def test_public_submit_rejects_reserved_retry_identity():
    from app.tasks.routes import admit_task

    session = Mock()
    with pytest.raises(HTTPException) as denied:
        admit_task(Mock(), Mock(), Mock(), session, Mock(), "failed-retry:" + str(uuid4()))
    assert denied.value.status_code == 422
    session.commit.assert_not_called()


def test_ambiguous_retry_commit_is_never_automatically_retried(monkeypatch):
    from sqlalchemy.exc import OperationalError

    from app.tasks import failed_actions as actions
    from app.tasks import stopped_image_retry
    from app.tasks.routes import failed_task_action

    service, session = Mock(), Mock()
    monkeypatch.setattr(actions, "FailedTaskActions", lambda *args: service)
    monkeypatch.setattr(stopped_image_retry, "prepare_stopped_image_retry", lambda *args: None)
    session.commit.side_effect = OperationalError("commit", {}, Exception(1213, "uncertain"))
    with pytest.raises(OperationalError):
        failed_task_action("retry", uuid4(), Mock(), session, Mock(), "request-key")
    service.retry.assert_called_once()


@pytest.mark.parametrize('with_chain', [False, True])
def test_free_regeneration_failure_retry_preserves_entitlement_and_standard_quote(
    monkeypatch, with_chain,
):
    from app.tasks import failed_actions as actions

    original = SimpleNamespace(id=str(uuid4()), conversation_id=str(uuid4()),
                               agent_id=str(uuid4()), state='FAILED', settlement_state='FROZEN')
    standard = dict(spec_id=original.agent_id, spec_version='v1', price_version='p1',
                    agent_version='v1', credits=30, input_digest='input', policy_versions={})
    snapshot = SimpleNamespace(
        input_snapshot=dict(product_version='product', product={'name': '原商品'},
                            instruction='原指令', material_versions=[], parameters={}),
        quote=standard | {'credits': 0},
        price_snapshot={'credits': 0, 'standard_quote': standard},
    )
    metadata = dict(root_task_id=str(uuid4()), source_task_id=str(uuid4()),
                    free_regenerations_used=2)
    if with_chain:
        snapshot.price_snapshot['regeneration'] = metadata
    session = Mock()
    session.get.return_value = snapshot
    service = actions.FailedTaskActions(session, Mock())
    service._owned = lambda *a: original
    service._successor = lambda *a: None
    monkeypatch.setattr(actions, 'release_failed_hold', lambda *a: None)

    def admit(principal, key, request, *, free_regeneration=False, regeneration_metadata=None):
        assert request.confirmed_quote.model_dump(mode='json') == standard
        assert free_regeneration is True
        assert regeneration_metadata == (metadata if with_chain else None)
        return 'free-retry-admitted'

    monkeypatch.setattr(actions, 'AdmissionService', lambda *a: SimpleNamespace(admit_task=admit))
    assert service.retry(Mock(), original.id) == 'free-retry-admitted'
