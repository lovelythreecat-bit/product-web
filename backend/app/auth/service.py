"""Database-authoritative authentication. No service owns transaction commit."""

import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.models import AuthSession, RegistrationReceipt, User
from app.auth.schemas import ProfileView
from app.auth.security import DUMMY_HASH, HASHER, digest, normalize_account, verify_password
from app.common.types import Principal
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
        return self._issue(user)

    def require_active_principal(self, cookie):
        if not cookie or len(cookie) > 128:
            raise HTTPException(401)
        # First resolve opaque credential, then lock user before the session row.
        credential = self.session.scalar(
            select(AuthSession).where(AuthSession.token_hash == digest(cookie))
        )
        if credential is None:
            raise HTTPException(401)
        user = self.session.scalar(
            select(User)
            .where(User.id == credential.user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        credential = self.session.scalar(
            select(AuthSession)
            .where(AuthSession.id == credential.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            user is None
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

    def update_profile(self, principal, dto):
        user = self.session.get(User, str(principal.user_id))
        for field, value in dto.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        self.session.flush()
        return profile(user)
