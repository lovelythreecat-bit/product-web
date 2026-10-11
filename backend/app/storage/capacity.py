"""Caller-owned MySQL transactions; no service commits, expiry is not failure evidence.

Lock order: user -> pool -> account -> reservation. Callers combining credits must
lock credits before entering this service, and tasks after locking capacity.
Existing pool/account limits are never silently reconfigured by a new version.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert

from app.auth.models import User
from app.policies.service import PolicyGateError
from app.storage.models import CapacityReservation, StorageAccount, StoragePool
from app.storage.schemas import capacity_policy


class StorageError(Exception):
    def __init__(self, code="CAPACITY_INSUFFICIENT", status_code=409):
        self.code, self.status_code = code, status_code
        super().__init__(code)


def valid_bytes(value, *, zero=False):
    if type(value) is not int or not (0 if zero else 1) <= value <= 2**63 - 1:
        raise HTTPException(422)


def locked(session, model, *where):
    return session.scalar(
        select(model).where(*where).with_for_update().execution_options(populate_existing=True)
    )


def lock_capacity(session, user_id, pool_id, policy=None, policy_version=None):
    user_id = str(user_id)
    user = locked(session, User, User.id == user_id)
    if user is None:
        raise HTTPException(404)
    if policy is not None:
        if user.status != "active":
            raise HTTPException(403)
        session.execute(
            insert(StoragePool)
            .values(
                id=pool_id,
                budget_bytes=policy.server_budget_bytes,
                reserved_bytes=0,
                actual_bytes=0,
                policy_version=policy_version,
            )
            .on_duplicate_key_update(id=StoragePool.id)
        )
    pool = locked(session, StoragePool, StoragePool.id == pool_id)
    if pool is None:
        raise PolicyGateError()
    account = locked(session, StorageAccount, StorageAccount.user_id == user_id)
    if account is None and policy is not None:
        account = StorageAccount(
            user_id=user_id,
            pool_id=pool_id,
            quota_bytes=policy.account_quota_bytes,
            reserved_bytes=0,
            actual_bytes=0,
            policy_version=policy_version,
        )
        session.add(account)
        session.flush()
    if account is None or account.pool_id != pool_id:
        raise PolicyGateError()
    if policy is not None and (
        pool.budget_bytes != policy.server_budget_bytes
        or account.quota_bytes != policy.account_quota_bytes
    ):
        raise PolicyGateError()
    return pool, account


def reserve_capacity(session, user_id, intent_id, estimated_bytes, policy_version, *, mode="mock"):
    valid_bytes(estimated_bytes)
    if not isinstance(intent_id, str) or not 1 <= len(intent_id) <= 128:
        raise HTTPException(422)
    policy = capacity_policy(
        session,
        policy_version,
        mode,
        purpose="upload" if intent_id.startswith("upload:") else "generation",
    )
    pool, account = lock_capacity(session, user_id, mode, policy, policy_version)
    existing = locked(
        session,
        CapacityReservation,
        CapacityReservation.user_id == str(user_id),
        CapacityReservation.intent_id == intent_id,
    )
    if existing:
        if (existing.estimated_bytes, existing.policy_version) != (estimated_bytes, policy_version):
            raise StorageError("IDEMPOTENCY_CONFLICT")
        return existing
    if (
        estimated_bytes > pool.budget_bytes - pool.actual_bytes - pool.reserved_bytes
        or estimated_bytes > account.quota_bytes - account.actual_bytes - account.reserved_bytes
    ):
        raise StorageError()
    pool.reserved_bytes += estimated_bytes
    account.reserved_bytes += estimated_bytes
    reservation = CapacityReservation(
        id=str(uuid4()),
        user_id=str(user_id),
        pool_id=pool.id,
        intent_id=intent_id,
        estimated_bytes=estimated_bytes,
        actual_bytes=0,
        state="reserved",
        policy_version=policy_version,
        expires_at=datetime.now(UTC).replace(tzinfo=None)
        + timedelta(seconds=policy.reservation_seconds),
    )
    session.add(reservation)
    session.flush()
    return reservation


def reservation_locks(session, reservation_id):
    # Identity read is nonlocking; re-read state only after canonical lock ordering.
    identity = session.execute(
        select(CapacityReservation.user_id, CapacityReservation.pool_id).where(
            CapacityReservation.id == str(reservation_id)
        )
    ).one_or_none()
    if identity is None:
        raise HTTPException(404)
    pool, account = lock_capacity(session, identity.user_id, identity.pool_id)
    reservation = locked(
        session, CapacityReservation, CapacityReservation.id == str(reservation_id)
    )
    return pool, account, reservation


def finalize_capacity(session, reservation_id, actual_bytes):
    valid_bytes(actual_bytes, zero=True)
    pool, account, reservation = reservation_locks(session, reservation_id)
    if reservation.state == "finalized":
        if reservation.actual_bytes != actual_bytes:
            raise StorageError("IDEMPOTENCY_CONFLICT")
        return reservation
    if reservation.state != "reserved":
        raise StorageError("IDEMPOTENCY_CONFLICT")
    delta = actual_bytes - reservation.estimated_bytes
    if (
        delta > pool.budget_bytes - pool.actual_bytes - pool.reserved_bytes
        or delta > account.quota_bytes - account.actual_bytes - account.reserved_bytes
    ):
        raise StorageError()
    for ledger in (pool, account):
        ledger.reserved_bytes -= reservation.estimated_bytes
        ledger.actual_bytes += actual_bytes
    reservation.actual_bytes = actual_bytes
    reservation.state = "finalized"
    session.flush()
    return reservation


def release_capacity(session, reservation_id):
    pool, account, reservation = reservation_locks(session, reservation_id)
    if reservation.state == "reserved":
        pool.reserved_bytes -= reservation.estimated_bytes
        account.reserved_bytes -= reservation.estimated_bytes
        reservation.state = "released"
        session.flush()
    return reservation
