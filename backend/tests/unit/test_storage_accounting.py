"""Storage limits concern real disk/file sizes, never retired account budgets."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.policies.schemas import StoragePolicy, UploadPolicy
from app.storage import capacity
from app.storage.schemas import CapacityPolicy, capacity_policy


def timing():
    return {
        "reservation_seconds": 120,
        "reclamation_ref": "TEST_ONLY_reclaim",
        "alert_ref": "TEST_ONLY_alert",
    }


def generation():
    return timing() | {
        "estimation_ref": "TEST_ONLY_estimate",
        "allowed_download_sources": ["https://example.invalid"],
        "max_download_bytes": 1024,
        "download_timeout_seconds": 10,
        "max_redirects": 0,
        "link_validity_ref": "TEST_ONLY_links",
        "recovery_ref": "TEST_ONLY_recovery",
    }


@pytest.mark.parametrize("legacy", [{}, {"account_quota_bytes": 1, "server_budget_bytes": 2}])
def test_storage_policies_need_no_software_capacity_limits(legacy):
    assert CapacityPolicy.model_validate(timing() | legacy).reservation_seconds == 120
    upload = UploadPolicy.model_validate(
        timing() | {"max_file_bytes": 512, "allowed_types": ["image/png"]} | legacy
    )
    assert upload.max_file_bytes == 512
    assert StoragePolicy.model_validate(generation() | legacy).max_download_bytes == 1024
    assert "account_quota_bytes" not in upload.model_dump()


def test_retired_capacity_keys_do_not_weaken_file_or_download_validation():
    with pytest.raises(ValidationError):
        UploadPolicy.model_validate(
            timing() | {"max_file_bytes": 0, "allowed_types": ["image/png"]}
        )
    with pytest.raises(ValidationError):
        StoragePolicy.model_validate(generation() | {"max_download_bytes": 0})
    with pytest.raises(ValidationError):
        CapacityPolicy.model_validate(timing() | {"unreviewed_flag": True})


def test_upload_accounting_ignores_conflicting_immutable_legacy_limits(monkeypatch):
    record = SimpleNamespace(
        mode="mock",
        status="draft",
        payload={
            "upload": timing() | {"account_quota_bytes": 99},
            "generation": timing() | {"account_quota_bytes": 1, "server_budget_bytes": 2},
        },
    )
    monkeypatch.setattr(
        "app.storage.schemas.PolicyService",
        lambda session: SimpleNamespace(_read=lambda *_: record),
    )
    assert (
        capacity_policy(Mock(), "TEST_ONLY_old", "mock", purpose="upload").reservation_seconds
        == 120
    )


def ledgers():
    # These legacy attributes reproduce values formerly loaded from old records;
    # only byte statistics may affect the actual service after quota retirement.
    return (
        SimpleNamespace(id="mock", budget_bytes=2, reserved_bytes=100, actual_bytes=10),
        SimpleNamespace(quota_bytes=1, reserved_bytes=100, actual_bytes=10),
    )


def test_reserve_accounts_bytes_beyond_old_account_and_server_limits(monkeypatch):
    pool, account = ledgers()
    monkeypatch.setattr(
        capacity, "capacity_policy", lambda *_, **__: SimpleNamespace(reservation_seconds=120)
    )
    monkeypatch.setattr(capacity, "lock_capacity", lambda *_, **__: (pool, account))
    monkeypatch.setattr(capacity, "locked", lambda *_: None)
    reservation = capacity.reserve_capacity(Mock(), "owner", "new-intent", 150, "TEST_ONLY_old")
    assert reservation.estimated_bytes == 150
    assert (pool.reserved_bytes, account.reserved_bytes) == (250, 250)


def test_real_free_disk_is_checked_after_existing_reservations(monkeypatch):
    pool, account = ledgers()
    monkeypatch.setattr(
        capacity, "capacity_policy", lambda *_, **__: SimpleNamespace(reservation_seconds=120)
    )
    monkeypatch.setattr(capacity, "lock_capacity", lambda *_, **__: (pool, account))
    monkeypatch.setattr(capacity, "locked", lambda *_: None)
    with pytest.raises(capacity.StorageError, match="CAPACITY_INSUFFICIENT"):
        capacity.reserve_capacity(
            Mock(), "owner", "new-intent", 150, "TEST_ONLY_old", free_bytes=lambda: 200
        )
    assert pool.reserved_bytes == account.reserved_bytes == 100
    capacity.reserve_capacity(
        Mock(), "owner", "new-intent", 150, "TEST_ONLY_old", free_bytes=lambda: 250
    )
    assert pool.reserved_bytes == account.reserved_bytes == 250


def test_finalize_counts_actual_bytes_above_an_old_quota(monkeypatch):
    pool, account = ledgers()
    reservation = SimpleNamespace(state="reserved", estimated_bytes=100, actual_bytes=0)
    monkeypatch.setattr(capacity, "reservation_locks", lambda *_: (pool, account, reservation))
    capacity.finalize_capacity(Mock(), "reservation", 200)
    assert (pool.reserved_bytes, pool.actual_bytes) == (0, 210)
    assert (account.reserved_bytes, account.actual_bytes) == (0, 210)
    assert (reservation.state, reservation.actual_bytes) == ("finalized", 200)


def test_manual_close_keeps_all_original_bytes_above_retired_limits(monkeypatch):
    pool, account = ledgers()
    reservation = SimpleNamespace(
        id="reservation", state="reserved", estimated_bytes=100, actual_bytes=0
    )
    task = SimpleNamespace(id="task", user_id="owner", capacity_reservation_id="reservation")
    original = SimpleNamespace(file_id="file", file_version="v1", actual_bytes=200)
    session = Mock()
    session.scalars.side_effect = [
        SimpleNamespace(all=lambda: [original]),
        SimpleNamespace(all=lambda: []),
    ]
    monkeypatch.setattr(capacity, "reservation_locks", lambda *_: (pool, account, reservation))
    capacity.retain_original_capacity(session, task)
    assert reservation.estimated_bytes == 200
    assert pool.reserved_bytes == account.reserved_bytes == 200


def test_manifest_capacity_growth_accounts_only_the_missing_bytes_once(monkeypatch):
    pool, account = ledgers()
    reservation = SimpleNamespace(state="reserved", estimated_bytes=100, actual_bytes=0)
    monkeypatch.setattr(capacity, "reservation_locks", lambda *_: (pool, account, reservation))
    free = Mock(return_value=200)
    session = Mock()
    capacity.ensure_reserved_capacity(session, "reservation", 200, free_bytes=free)
    assert (pool.reserved_bytes, account.reserved_bytes, reservation.estimated_bytes) == (
        200,
        200,
        200,
    )
    free.return_value = 0
    capacity.ensure_reserved_capacity(session, "reservation", 200, free_bytes=free)
    capacity.ensure_reserved_capacity(session, "reservation", 150, free_bytes=free)
    assert (pool.reserved_bytes, account.reserved_bytes, reservation.estimated_bytes) == (
        200,
        200,
        200,
    )
    free.assert_called_once_with()


def test_manifest_capacity_growth_cannot_overbook_real_free_disk(monkeypatch):
    pool, account = ledgers()
    reservation = SimpleNamespace(state="reserved", estimated_bytes=100, actual_bytes=0)
    monkeypatch.setattr(capacity, "reservation_locks", lambda *_: (pool, account, reservation))
    with pytest.raises(capacity.StorageError, match="CAPACITY_INSUFFICIENT"):
        capacity.ensure_reserved_capacity(Mock(), "reservation", 200, free_bytes=lambda: 199)
    assert (pool.reserved_bytes, account.reserved_bytes, reservation.estimated_bytes) == (
        100,
        100,
        100,
    )


@pytest.mark.parametrize("state", ["released", "finalized"])
def test_manifest_capacity_growth_rejects_finished_reservations(monkeypatch, state):
    pool, account = ledgers()
    reservation = SimpleNamespace(state=state, estimated_bytes=100, actual_bytes=0)
    monkeypatch.setattr(capacity, "reservation_locks", lambda *_: (pool, account, reservation))
    free = Mock(return_value=1000)
    with pytest.raises(capacity.StorageError, match="IDEMPOTENCY_CONFLICT"):
        capacity.ensure_reserved_capacity(Mock(), "reservation", 200, free_bytes=free)
    free.assert_not_called()
    assert reservation.estimated_bytes == 100
