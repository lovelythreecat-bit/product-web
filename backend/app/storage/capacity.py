"""Caller-owned MySQL transactions; no service commits, expiry is not failure evidence.

Lock order: user -> pool -> account -> reservation. Callers combining credits must
lock credits before entering this service, and tasks after locking capacity.
Software account quotas and server budgets are retired; disk probes run under
the shared pool lock so concurrent reservations cannot overbook actual free bytes.
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
            reserved_bytes=0,
            actual_bytes=0,
            policy_version=policy_version,
        )
        session.add(account)
        session.flush()
    if account is None or account.pool_id != pool_id:
        raise PolicyGateError()
    return pool, account


def reserve_capacity(
    session, user_id, intent_id, estimated_bytes, policy_version, *, mode="mock", free_bytes=None
):
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
    if free_bytes is not None:
        available = free_bytes()
        valid_bytes(available, zero=True)
        if estimated_bytes > available - pool.reserved_bytes:
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


def ensure_reserved_capacity(session, reservation_id, required_bytes, *, free_bytes):
    """Protect a larger manifest before download under canonical capacity locks.

    Existing reservations share the same disk probe as admission. Repeated or
    smaller manifests retain the original protected bytes without reserving twice.
    Caller owns the transaction and must commit before writing the added bytes.
    """
    valid_bytes(required_bytes, zero=True)
    pool, account, reservation = reservation_locks(session, reservation_id)
    if reservation.state != "reserved":
        raise StorageError("IDEMPOTENCY_CONFLICT")
    delta = max(0, required_bytes - reservation.estimated_bytes)
    if not delta:
        return reservation
    available = free_bytes()
    valid_bytes(available, zero=True)
    if delta > available - pool.reserved_bytes:
        raise StorageError()
    pool.reserved_bytes += delta
    account.reserved_bytes += delta
    reservation.estimated_bytes += delta
    session.flush()
    return reservation


def finalize_capacity(session, reservation_id, actual_bytes):
    valid_bytes(actual_bytes, zero=True)
    pool, account, reservation = reservation_locks(session, reservation_id)
    if reservation.state == "finalized":
        if reservation.actual_bytes != actual_bytes:
            raise StorageError("IDEMPOTENCY_CONFLICT")
        return reservation
    if reservation.state != "reserved":
        raise StorageError("IDEMPOTENCY_CONFLICT")
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


def retain_original_capacity(session, task):
    """Protect every fixed original save identity, including journal/in-flight items.

    Called after user/credits/capacity/task locks. Save identities are committed
    before any T11 disk write; no filesystem probe or upstream I/O is needed here.
    Keep the original reservation and increase it when declared bytes exceeded its
    estimate. Already staged bytes remain accounted independently of retired quotas.
    """
    from app.results.models import ResultManifestRecord, ResultSaveItem
    from app.storage.models import File

    pool, account, reservation = reservation_locks(session, task.capacity_reservation_id)
    jobs = session.scalars(
        select(ResultSaveItem)
        .join(ResultManifestRecord, ResultManifestRecord.id == ResultSaveItem.manifest_id)
        .where(ResultManifestRecord.task_id == task.id)
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    ).all()
    files = session.scalars(
        select(File)
        .where(File.reservation_id == reservation.id, File.user_id == task.user_id)
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    ).all()
    identities = {}
    for row in jobs:
        valid_bytes(row.actual_bytes)
        key = (row.file_id, row.file_version)
        identities[key] = max(identities.get(key, 0), row.actual_bytes)
    for row in files:
        valid_bytes(row.actual_bytes)
        key = (row.id, row.version)
        identities[key] = max(identities.get(key, 0), row.actual_bytes)
    protected_bytes = sum(identities.values())
    valid_bytes(protected_bytes, zero=True)
    if reservation.state == "finalized" and reservation.actual_bytes >= protected_bytes:
        return reservation
    if reservation.state != "reserved":
        raise StorageError("IDEMPOTENCY_CONFLICT")
    delta = max(0, protected_bytes - reservation.estimated_bytes)
    pool.reserved_bytes += delta
    account.reserved_bytes += delta
    reservation.estimated_bytes += delta
    session.flush()
    return reservation
