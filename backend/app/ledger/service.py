"""All operations participate in the caller transaction; lock users before balances."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.audit.service import audit_credit_config
from app.auth.models import User
from app.ledger.models import (
    CreditAccount,
    CreditGrant,
    CreditLedger,
    CreditReservation,
    RegistrationCreditConfig,
    RegistrationCreditHead,
)
from app.policies.service import PolicyGateError, PolicyService


def now():
    return datetime.now(UTC).replace(tzinfo=None)


class LedgerError(Exception):
    def __init__(self, code="IDEMPOTENCY_CONFLICT", status_code=409):
        self.code = code
        self.status_code = status_code
        super().__init__(code)


def amount_valid(amount):
    if type(amount) is not int or not 0 <= amount <= 2**63 - 1:
        raise HTTPException(422)


def locked_account(session, user_id):
    user_id = str(user_id)
    user = session.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None:
        raise HTTPException(404)
    account = session.scalar(
        select(CreditAccount)
        .where(CreditAccount.user_id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if account is None:
        raise HTTPException(404)
    return account


def balances(account):
    return {name: getattr(account, name) for name in ("available", "frozen", "consumed")}


def grant_credits(session, user_id, kind, business_key, amount, reason, actor):
    amount_valid(amount)
    if (
        kind not in ("signup", "admin")
        or not business_key
        or len(business_key) > 128
        or not reason.strip()
        or len(reason) > 500
    ):
        raise HTTPException(422)
    user_id = str(user_id)
    actor_id = str(actor.user_id) if actor is not None else None
    if kind == "signup" and business_key != f"signup:{user_id}":
        raise HTTPException(422)
    if kind == "admin" and actor_id is None:
        raise HTTPException(422)
    account = locked_account(session, user_id)
    query = (
        select(CreditGrant)
        .where(CreditGrant.kind == kind, CreditGrant.business_key == business_key)
        .with_for_update()
    )
    existing = session.scalar(query)
    if existing is not None:
        if (existing.user_id, existing.amount, existing.reason, existing.actor_id) != (
            user_id,
            amount,
            reason,
            actor_id,
        ):
            raise LedgerError()
        return existing
    if account.credited_total + amount > 2**63 - 1:
        raise HTTPException(422)
    before = balances(account)
    grant = CreditGrant(
        id=str(uuid4()),
        user_id=user_id,
        kind=kind,
        business_key=business_key,
        amount=amount,
        reason=reason,
        actor_id=actor_id,
        created_at=now(),
    )
    # A cross-account collision is a conflict, never a second credit.
    try:
        with session.begin_nested():
            session.add(grant)
            session.flush()
    except IntegrityError:
        raise LedgerError() from None
    account.available += amount
    account.credited_total += amount
    session.add(
        CreditLedger(
            id=str(uuid4()),
            operation_key=f"grant:{grant.id}",
            user_id=user_id,
            grant_id=grant.id,
            kind=kind,
            amount=amount,
            balances_before=before,
            balances_after=balances(account),
            reason=reason,
            created_at=now(),
        )
    )
    session.flush()
    return grant


def freeze_credits(session, user_id, task_id, amount):
    from app.tasks.models import GenerationTask

    amount_valid(amount)
    user_id, task_id = str(user_id), str(task_id)
    account = locked_account(session, user_id)
    task = session.scalar(
        select(GenerationTask)
        .where(GenerationTask.id == task_id, GenerationTask.user_id == user_id)
        .with_for_update()
    )
    if task is None:
        raise HTTPException(404)
    reservation = session.scalar(
        select(CreditReservation).where(CreditReservation.task_id == task_id).with_for_update()
    )
    if reservation is not None:
        if (reservation.user_id, reservation.amount) != (user_id, amount):
            raise LedgerError()
        return reservation
    if account.available < amount:
        raise LedgerError("INSUFFICIENT_CREDITS", 402)
    before = balances(account)
    reservation = CreditReservation(
        id=str(uuid4()),
        user_id=user_id,
        task_id=task_id,
        amount=amount,
        state="frozen",
        version=1,
        created_at=now(),
    )
    try:
        with session.begin_nested():
            session.add(reservation)
            session.flush()
    except IntegrityError:
        raise LedgerError() from None
    account.available -= amount
    account.frozen += amount
    session.add(
        CreditLedger(
            id=str(uuid4()),
            operation_key=f"freeze:{task_id}",
            user_id=user_id,
            reservation_id=reservation.id,
            task_id=task_id,
            kind="freeze",
            amount=amount,
            balances_before=before,
            balances_after=balances(account),
            reason="generation reservation",
            created_at=now(),
        )
    )
    session.flush()
    return reservation


def read_registration_credit_config(session, mode):
    head = session.get(RegistrationCreditHead, mode)
    if head is None:
        raise PolicyGateError()
    config = session.get(RegistrationCreditConfig, head.version)
    if config is None or config.mode != mode:
        raise PolicyGateError()
    PolicyService(session).require_feature("registration", mode, {"D-05": config.policy_version})
    return config


def set_registration_credit_config(
    session, *, mode, expected_version, amount, policy_version, reason, actor=None
):
    """Internal repository operation; T19 must authorize its management caller."""
    amount_valid(amount)
    if not reason.strip() or len(reason) > 500:
        raise HTTPException(422)
    policies = PolicyService(session)
    policies.require_feature("registration", mode, {"D-05": policy_version})
    policy = policies._read("D-05", policy_version)
    if policy.payload["registration"]["credits"] != amount:
        raise PolicyGateError()
    head = session.scalar(
        select(RegistrationCreditHead)
        .where(RegistrationCreditHead.mode == mode)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (head.version if head else None) != expected_version:
        raise LedgerError()
    config = RegistrationCreditConfig(
        version=str(uuid4()),
        mode=mode,
        test_only=mode == "mock",
        amount=amount,
        policy_version=policy_version,
        reason=reason,
        created_at=now(),
    )
    session.add(config)
    session.flush()
    if head is None:
        session.add(RegistrationCreditHead(mode=mode, version=config.version))
    else:
        head.version = config.version
    audit_credit_config(
        session, actor.user_id if actor else None, config.version, reason, amount, policy_version
    )
    session.flush()
    return config
