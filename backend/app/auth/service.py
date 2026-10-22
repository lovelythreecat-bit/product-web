"""Database-authoritative authentication. No service owns transaction commit."""

import secrets
from dataclasses import dataclass
from datetime import UTC, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.models import AuthSession, RegistrationReceipt, User
from app.auth.schemas import ProfileView
from app.auth.security import DUMMY_HASH, HASHER, digest, normalize_account, verify_password
from app.common.types import FileVersionRef, Principal
from app.ledger.models import CreditAccount
from app.ledger.service import LedgerError, grant_credits, now, read_registration_credit_config


@dataclass(repr=False)
class AuthResult:
    profile: ProfileView
    session_token: str
    csrf_token: str
    replayed: bool = False


def profile(user):
    return ProfileView(
        user_id=user.id,
        account=user.account_normalized,
        role=user.role,
        nickname=user.nickname,
        bio=user.bio,
        shop_name=user.shop_name,
        category=user.category,
        email=user.email,
        phone=user.phone,
        avatar=(
            FileVersionRef(file_id=user.avatar_file_id, version=user.avatar_file_version)
            if user.avatar_file_id is not None
            else None
        ),
        status=user.status,
        created_at=user.created_at.replace(tzinfo=UTC),
        last_login_at=user.last_login_at.replace(tzinfo=UTC) if user.last_login_at else None,
    )


class AuthService:
    def __init__(self, session, *, mode="production", session_seconds=86400):
        self.session = session
        self.mode = mode
        self.session_seconds = session_seconds

    def _issue(self, user, replayed=False):
        if user.status != "active":
            raise HTTPException(401)
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.session.add(
            AuthSession(
                id=str(uuid4()),
                user_id=user.id,
                token_hash=digest(token),
                csrf_hash=digest(csrf),
                auth_version=user.auth_version,
                expires_at=now() + timedelta(seconds=self.session_seconds),
            )
        )
        self.session.flush()
        return AuthResult(profile(user), token, csrf, replayed)

    def register_account(self, account, password, request_key, policy_version=None):
        account = normalize_account(account)
        if not 10 <= len(password) <= 128 or not request_key or len(request_key) > 128:
            raise HTTPException(422)
        # The gate also applies to replays: a mock account cannot reopen production signup.
        config = read_registration_credit_config(self.session, self.mode)
        if policy_version is not None and config.policy_version != policy_version:
            raise LedgerError()
        existing = self.session.scalar(select(User).where(User.account_normalized == account))
        if existing is not None:
            return self._replay(account, password, request_key)
        # New user and receipt insertion resolve concurrent races using DB uniqueness.
        # Savepoint rollback does not commit or discard caller-owned work.
        user = User(
            id=str(uuid4()),
            account_normalized=account,
            password_hash=HASHER.hash(password),
            role="user",
            status="active",
            auth_version=0,
            created_at=now(),
        )
        try:
            with self.session.begin_nested():
                self.session.add(user)
                self.session.flush()
                self.session.add(
                    RegistrationReceipt(
                        request_key=request_key,
                        user_id=user.id,
                        account_normalized=account,
                        config_version=config.version,
                    )
                )
                self.session.flush()
        except IntegrityError:
            return self._replay(account, password, request_key)
        self.session.add(
            CreditAccount(user_id=user.id, available=0, frozen=0, consumed=0, credited_total=0)
        )
        self.session.flush()
        grant_credits(
            self.session,
            user.id,
            "signup",
            f"signup:{user.id}",
            config.amount,
            "registration trial credits",
            None,
        )
        return self._issue(user)

    def _replay(self, account, password, request_key):
        user = self.session.scalar(
            select(User)
            .where(User.account_normalized == account)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        receipt = self.session.scalar(
            select(RegistrationReceipt)
            .where(RegistrationReceipt.request_key == request_key)
            .with_for_update()
        )
        if (
            user is None
            or receipt is None
            or receipt.user_id != user.id
            or receipt.account_normalized != account
            or not verify_password(user.password_hash, password)
        ):
            raise LedgerError()
        return self._issue(user, replayed=True)

    def authenticate(self, account, password):
        account = normalize_account(account)
        user = self.session.scalar(
            select(User)
            .where(User.account_normalized == account)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        valid = verify_password(user.password_hash if user else DUMMY_HASH, password)
        if user is None or not valid or user.status != "active":
            raise HTTPException(401)
        # The route commits this with the issued session; failed transactions do
        # not record a login. Registration/replay and profile reads never set it.
        user.last_login_at = now()
        return self._issue(user)

    def require_active_principal(self, cookie, *, lock=None):
        if not cookie or len(cookie) > 128:
            raise HTTPException(401)
        if lock is None:
            lock = not getattr(self.session, "info", {}).get("read_only_request", False)
        # Resolve the opaque credential before checking user and session authority.
        credential = self.session.scalar(
            select(AuthSession).where(AuthSession.token_hash == digest(cookie))
        )
        if credential is None:
            raise HTTPException(401)
        user_query = select(User).where(User.id == credential.user_id)
        credential_query = select(AuthSession).where(AuthSession.id == credential.id)
        # Reads check the database without holding an exclusive account lock across
        # remote service I/O or streaming. Mutations retain user -> session ordering.
        if lock:
            user_query = user_query.with_for_update()
            credential_query = credential_query.with_for_update()
        user = self.session.scalar(user_query.execution_options(populate_existing=True))
        credential = self.session.scalar(
            credential_query.execution_options(populate_existing=True)
        )
        if (
            user is None
            or credential is None
            or user.status != "active"
            or credential.revoked_at is not None
            or credential.expires_at <= now()
            or credential.auth_version != user.auth_version
        ):
            raise HTTPException(401)
        return Principal(
            user_id=UUID(user.id),
            role=user.role,
            session_id=UUID(credential.id),
            auth_version=user.auth_version,
        )

    def revoke_session(self, id):
        credential = self.session.get(AuthSession, str(id))
        if credential is not None:
            self.session.scalar(select(User).where(User.id == credential.user_id).with_for_update())
            credential = self.session.scalar(
                select(AuthSession)
                .where(AuthSession.id == str(id))
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            credential.revoked_at = now()
            self.session.flush()

    def get_profile(self, principal):
        return profile(self.session.get(User, str(principal.user_id)))

    def change_password(self, principal, current_password, new_password):
        from app.catalog.service import CatalogService

        # Lock and recheck live identity before modifying the password/version together.
        CatalogService(self.session)._principal(principal)
        user = self.session.scalar(
            select(User)
            .where(User.id == str(principal.user_id))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not 10 <= len(new_password) <= 128:
            raise HTTPException(422)
        if not verify_password(user.password_hash, current_password):
            # A credential typo must not be confused with an expired login.
            raise HTTPException(400)
        user.password_hash = HASHER.hash(new_password)
        # Every existing session carries the old version and immediately fails authentication.
        user.auth_version += 1
        self.session.flush()

    def update_profile(self, principal, dto):
        from app.auth.avatar import update_avatar
        from app.conversations.service import authenticate

        authenticate(self.session, principal)
        user = self.session.scalar(
            select(User)
            .where(User.id == str(principal.user_id))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        values = dto.model_dump(exclude_unset=True, exclude={"avatar"})
        if "nickname" in values and values["nickname"] is None:
            raise HTTPException(422)
        # Existing long values remain readable and may be preserved exactly.
        # Newly edited values follow the approved prototype input limits.
        for field, limit in (("nickname", 40), ("bio", 300)):
            value = values.get(field)
            if value is not None and value != getattr(user, field) and len(value) > limit:
                raise HTTPException(422)
        if "avatar" in dto.model_fields_set:
            update_avatar(self.session, user, dto.avatar)
        for field, value in values.items():
            setattr(user, field, value)
        self.session.flush()
        return profile(user)

    def set_account_status(self, actor, user_id, status, policy_version, *, expected_auth_version):
        """Live admin authority + exact D-09/D-08 + CAS, in the caller transaction."""
        from pydantic import ValidationError
        from sqlalchemy import update

        from app.catalog.service import CatalogService
        from app.policies.schemas import DisablePolicy, ExceptionPolicy
        from app.policies.service import PolicyGateError, PolicyService
        from app.works.lifecycle import audit

        CatalogService(self.session)._principal(actor, admin=True)
        if status not in ("active", "disabled") or type(expected_auth_version) is not int:
            raise HTTPException(422)
        service = PolicyService(self.session)
        service.require_feature("account_disable", self.mode, {"D-09": policy_version})
        policy = DisablePolicy.model_validate(
            service._read("D-09", policy_version).payload["account_disable"]
        ).execution
        if policy is None or (status == "active" and policy.restoration != "new_login"):
            raise PolicyGateError()
        exception = service._read("D-08", policy.exception_policy_version)
        if (
            exception is None
            or exception.mode != self.mode
            or (self.mode != "mock" and exception.status != "confirmed")
        ):
            raise PolicyGateError()
        try:
            ExceptionPolicy.model_validate(exception.payload["generation"])
        except (KeyError, ValidationError):
            raise PolicyGateError() from None
        user = self.session.scalar(
            select(User)
            .where(User.id == str(user_id))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None:
            raise HTTPException(404)
        if user.auth_version != expected_auth_version:
            raise HTTPException(409)
        previous = user.status
        user.status = status
        user.auth_version += 1
        self.session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now())
        )
        audit(
            self.session,
            actor.user_id,
            "account_status",
            user.id,
            policy_version,
            previous_status=previous,
            status=status,
            auth_version=user.auth_version,
            exception_policy_version=policy.exception_policy_version,
            inflight="continue_original",
            frozen_credits="retain",
        )
        self.session.flush()
        return {
            "user_id": user.id,
            "status": status,
            "auth_version": user.auth_version,
            "policy_version": policy_version,
        }
