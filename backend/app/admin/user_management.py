"""Audited account administration without deleting historical business records."""

import hashlib
import json
from typing import Annotated, Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, SecretStr, field_validator
from sqlalchemy import exists, func, select, update
from sqlalchemy.exc import IntegrityError

from app.admin.permissions import authorize_admin
from app.admin.queries import search_terms
from app.admin.schemas import AdminUserView, CreditGrantRequest
from app.admin.service import _admin_page_rows, admin_credit_grant
from app.audit.models import AuditEvent
from app.audit.service import audit_admin
from app.auth.models import AuthSession, User
from app.auth.routes import DB, PrincipalDep, require_csrf
from app.auth.schemas import ProfileUpdate
from app.auth.security import HASHER, normalize_account
from app.common.errors import ErrorCode, ErrorResponse, error_response
from app.common.pagination import numbered_page_rows
from app.common.types import DTO, NumberedPage
from app.ledger.models import CreditAccount, CreditGrant, CreditLedger
from app.ledger.service import LedgerError, balances, locked_account, now
from app.tasks.models import GenerationTask

router = APIRouter(
    prefix="/api/v1/admin",
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422)},
)
Version = Annotated[int, Field(strict=True, ge=0)]
Reason = Annotated[str, Field(min_length=1, max_length=500, pattern=r"\S")]
MAX_AMOUNT = 2**53 - 1


class AdjustmentTargetDeleted(Exception):
    pass


class ManagedUserView(AdminUserView):
    profile_version: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ManagedUserUpdate(ProfileUpdate):
    expected_auth_version: Version
    expected_profile_version: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    account: Annotated[str, Field(min_length=3, max_length=64)]
    role: Literal["user", "admin"]
    status: Literal["active", "disabled"]
    reason: Reason

    @field_validator("account")
    @classmethod
    def normalized(cls, value):
        return normalize_account(value)


class ManagedPasswordReset(DTO):
    expected_auth_version: Version
    new_password: SecretStr = Field(min_length=10, max_length=128)
    reason: Reason


class ManagedUserDelete(DTO):
    expected_auth_version: Version
    reason: Reason


class CreditAdjustment(DTO):
    business_key: UUID
    delta: Annotated[int, Field(strict=True, ge=-MAX_AMOUNT, le=MAX_AMOUNT)]
    reason: Reason

    @field_validator("delta")
    @classmethod
    def nonzero(cls, value):
        if value == 0:
            raise ValueError("Adjustment must not be zero")
        return value


class CreditAdjustmentReceipt(DTO):
    ledger_id: UUID
    user_id: UUID
    actor_id: UUID
    business_key: UUID
    delta: int
    reason: str


def deleted_user(user_id=None):
    predicates = [AuditEvent.action == "admin_user_delete"]
    predicates.append(AuditEvent.object_id == (User.id if user_id is None else str(user_id)))
    return exists(select(AuditEvent.id).where(*predicates))


def _target(session, actor, user_id, expected=None, *, allow_deleted=False):
    authorize_admin(session, actor, user_ids=[user_id])
    user = session.scalar(
        select(User)
        .where(User.id == str(user_id))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None or (not allow_deleted and session.scalar(select(deleted_user(user_id)))):
        raise HTTPException(404)
    if expected is not None and user.auth_version != expected:
        raise HTTPException(409)
    return user


def _revoke(session, user):
    user.auth_version += 1
    session.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now())
    )


def profile_version(user):
    fields = (
        "account_normalized",
        "role",
        "status",
        "nickname",
        "bio",
        "shop_name",
        "category",
        "email",
        "phone",
        "avatar_file_id",
        "avatar_file_version",
    )
    payload = {field: getattr(user, field) for field in fields}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _view(session, user):
    account = session.get(CreditAccount, user.id)
    count = session.scalar(
        select(func.count()).select_from(GenerationTask).where(GenerationTask.user_id == user.id)
    )
    return ManagedUserView(
        **AdminUserView.model_validate(user).model_dump(), profile_version=profile_version(user)
    ).model_copy(
        update={
            "task_count": int(count or 0),
            **{
                key: int(getattr(account, key)) if account else 0
                for key in ("available", "frozen", "consumed")
            },
        }
    )


def managed_users(session, actor, cursor=None, limit=20, status=None, q=None, *, page=None):
    authorize_admin(session, actor)
    filters = [User.status == status] if status else []
    filters += search_terms(q, [User.account_normalized, User.nickname, User.id, User.shop_name])
    scope = [~deleted_user()]
    rows, next_cursor, metadata = numbered_page_rows(
        session,
        User,
        [*scope, *filters],
        cursor,
        limit,
        page=page,
        cursor_reader=lambda: _admin_page_rows(session, User, scope, filters, cursor, limit),
    )
    return NumberedPage[ManagedUserView](
        **metadata, items=[_view(session, row) for row in rows], next_cursor=next_cursor
    )


def update_user(session, actor, user_id, dto):
    user = _target(session, actor, user_id, dto.expected_auth_version)
    if profile_version(user) != dto.expected_profile_version:
        raise HTTPException(409)
    # Administrators cannot remove their own live access or demote another admin.
    if user.role == "admin" and (dto.role != "admin" or dto.status != "active"):
        raise HTTPException(403)
    collision = session.scalar(
        select(User.id).where(User.account_normalized == dto.account, User.id != user.id)
    )
    if collision:
        raise HTTPException(409)
    tracked = (
        "account_normalized",
        "nickname",
        "bio",
        "shop_name",
        "category",
        "email",
        "phone",
        "role",
        "status",
    )
    previous = {key: getattr(user, key) for key in tracked}
    before_version = user.auth_version
    user.account_normalized = dto.account
    for field in ("nickname", "bio", "shop_name", "category", "email", "phone"):
        if field in dto.model_fields_set:
            setattr(user, field, getattr(dto, field))
    user.role, user.status = dto.role, dto.status
    _revoke(session, user)
    audit_admin(
        session,
        actor.user_id,
        "admin_user_update",
        user.id,
        dto.reason,
        {
            "before_version": before_version,
            "auth_version": user.auth_version,
            "status": user.status,
            "user_id": user.id,
            "before": {
                key: value for key, value in previous.items() if value != getattr(user, key)
            },
            "after": {
                key: getattr(user, key)
                for key, value in previous.items()
                if value != getattr(user, key)
            },
        },
    )
    session.flush()
    return _view(session, user)


def reset_password(session, actor, user_id, dto):
    user = _target(session, actor, user_id, dto.expected_auth_version)
    user.password_hash = HASHER.hash(dto.new_password.get_secret_value())
    _revoke(session, user)
    audit_admin(
        session,
        actor.user_id,
        "admin_password_reset",
        user.id,
        dto.reason,
        {"user_id": user.id, "auth_version": user.auth_version},
    )
    session.flush()
    return _view(session, user)


def delete_user(session, actor, user_id, dto):
    authorize_admin(session, actor, user_ids=[user_id])
    user = session.get(User, str(user_id))
    if user is None:
        raise HTTPException(404)
    if user.role == "admin":
        raise HTTPException(403)
    # The immutable audit tombstone hides the account without a schema migration.
    # Existing tasks, reservations, files, grants and audit references retain their owner.
    if session.scalar(select(deleted_user(user_id))):
        return
    if user.auth_version != dto.expected_auth_version:
        raise HTTPException(409)
    user.status = "disabled"
    user.password_hash = HASHER.hash(str(uuid4()) + str(uuid4()))
    _revoke(session, user)
    audit_admin(
        session,
        actor.user_id,
        "admin_user_delete",
        user.id,
        dto.reason,
        {"user_id": user.id, "status": user.status, "auth_version": user.auth_version},
    )
    session.flush()


def adjust_credits(session, actor, user_id, dto):
    _target(session, actor, user_id, allow_deleted=True)
    account = locked_account(session, user_id)
    business_key = f"adjust:{dto.business_key}"
    # Inspect both signs before accepting a replay. Existing ledger records remain
    # immutable: positive grants retain the original grant:<id> operation identity.
    grant = session.scalar(
        select(CreditGrant)
        .where(
            CreditGrant.business_key == business_key,
            CreditGrant.kind.in_(("admin", "admin_deduct")),
        )
        .with_for_update()
    )
    if grant is not None:
        expected_kind = "admin" if dto.delta > 0 else "admin_deduct"
        if (grant.user_id, grant.kind, grant.amount, grant.reason, grant.actor_id) != (
            str(user_id),
            expected_kind,
            abs(dto.delta),
            dto.reason,
            str(actor.user_id),
        ):
            raise LedgerError()
        existing = session.scalar(
            select(CreditLedger).where(CreditLedger.grant_id == grant.id).with_for_update()
        )
        if existing is None or (
            existing.user_id,
            existing.kind,
            existing.amount,
            existing.reason,
        ) != (grant.user_id, grant.kind, grant.amount, grant.reason):
            raise LedgerError()
        return CreditAdjustmentReceipt(
            ledger_id=existing.id,
            user_id=user_id,
            actor_id=actor.user_id,
            business_key=dto.business_key,
            delta=dto.delta,
            reason=dto.reason,
        )
    if session.scalar(select(deleted_user(user_id))):
        # Only reached after proving there is no committed receipt for this key.
        raise AdjustmentTargetDeleted()
    if dto.delta > 0:
        grant = admin_credit_grant(
            session,
            actor,
            CreditGrantRequest(
                user_id=user_id,
                business_key=business_key,
                amount=dto.delta,
                reason=dto.reason,
            ),
        )
        entry = session.scalar(select(CreditLedger).where(CreditLedger.grant_id == grant.id))
    else:
        amount = -dto.delta
        if amount > account.available:
            raise LedgerError("INSUFFICIENT_CREDITS", 402)
        before = balances(account)
        grant = CreditGrant(
            id=str(uuid4()),
            user_id=str(user_id),
            kind="admin_deduct",
            business_key=business_key,
            amount=amount,
            reason=dto.reason,
            actor_id=str(actor.user_id),
            created_at=now(),
        )
        session.add(grant)
        session.flush()
        account.available -= amount
        account.credited_total -= amount
        entry = CreditLedger(
            id=str(uuid4()),
            operation_key=f"admin-adjust:{dto.business_key}",
            user_id=str(user_id),
            grant_id=grant.id,
            kind="admin_deduct",
            amount=amount,
            balances_before=before,
            balances_after=balances(account),
            reason=dto.reason,
            created_at=now(),
        )
        session.add(entry)
    audit = audit_admin(
        session,
        actor.user_id,
        "admin_credit_adjustment",
        entry.id,
        dto.reason,
        {"user_id": str(user_id), "amount": dto.delta, "actor_id": str(actor.user_id)},
    )
    # A shared immutable audit primary key serializes opposite-sign requests
    # across different accounts; a collision rolls back the entire transaction.
    audit.id = str(uuid5(NAMESPACE_URL, f"admin-credit-adjustment:{dto.business_key}"))
    session.flush()
    return CreditAdjustmentReceipt(
        ledger_id=entry.id,
        user_id=user_id,
        actor_id=actor.user_id,
        business_key=dto.business_key,
        delta=dto.delta,
        reason=dto.reason,
    )


@router.get(
    "/managed-users",
    response_model=NumberedPage[ManagedUserView],
    operation_id="admin_list_managed_users",
)
def users(
    session: DB,
    principal: PrincipalDep,
    cursor: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Literal["active", "disabled"] | None = None,
    q: Annotated[str | None, Query(max_length=128)] = None,
    page: Annotated[int | None, Query(ge=1)] = None,
):
    return managed_users(session, principal, cursor, limit, status, q, page=page)


@router.get(
    "/managed-users/{id}", response_model=ManagedUserView, operation_id="admin_managed_user"
)
def detail(id: UUID, session: DB, principal: PrincipalDep):
    return _view(session, _target(session, principal, id))


def _mutate(session, fn):
    session.rollback()
    try:
        result = fn()
        session.commit()
        return result
    except AdjustmentTargetDeleted:
        session.rollback()
        return error_response(
            409, ErrorCode.ADJUSTMENT_TARGET_DELETED, "目标用户已删除，本次积分未调整。"
        )
    except IntegrityError:
        session.rollback()
        raise HTTPException(409) from None
    except Exception:
        session.rollback()
        raise


@router.patch(
    "/managed-users/{id}",
    response_model=ManagedUserView,
    operation_id="admin_update_managed_user",
    dependencies=[Depends(require_csrf)],
)
def save(id: UUID, dto: ManagedUserUpdate, session: DB, principal: PrincipalDep):
    return _mutate(session, lambda: update_user(session, principal, id, dto))


@router.post(
    "/managed-users/{id}/password-reset",
    response_model=ManagedUserView,
    operation_id="admin_reset_managed_password",
    dependencies=[Depends(require_csrf)],
)
def reset(id: UUID, dto: ManagedPasswordReset, session: DB, principal: PrincipalDep):
    return _mutate(session, lambda: reset_password(session, principal, id, dto))


@router.delete(
    "/managed-users/{id}",
    status_code=204,
    operation_id="admin_delete_managed_user",
    dependencies=[Depends(require_csrf)],
)
def remove(id: UUID, dto: ManagedUserDelete, session: DB, principal: PrincipalDep):
    _mutate(session, lambda: delete_user(session, principal, id, dto))


@router.post(
    "/managed-users/{id}/credit-adjustments",
    response_model=CreditAdjustmentReceipt,
    operation_id="admin_adjust_managed_credits",
    dependencies=[Depends(require_csrf)],
)
def adjustment(id: UUID, dto: CreditAdjustment, session: DB, principal: PrincipalDep):
    return _mutate(session, lambda: adjust_credits(session, principal, id, dto))
