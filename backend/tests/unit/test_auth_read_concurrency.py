"""Read requests must not serialize on an account's authentication rows."""

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.admin.permissions import authorize_admin
from app.auth.models import AuthSession, User
from app.auth.service import AuthService
from app.catalog.service import CatalogService
from app.db import get_session
from app.ledger.service import now


class AuthReadSession:
    def __init__(self, *, read_only=True):
        self.info = {"read_only_request": read_only}
        self.user = SimpleNamespace(id=str(uuid4()), role="admin", status="active", auth_version=1)
        self.credential = SimpleNamespace(
            id=str(uuid4()), user_id=self.user.id, auth_version=1, revoked_at=None,
            expires_at=now() + timedelta(hours=1),
        )
        self.locks = []

    def scalar(self, statement):
        model = statement.column_descriptions[0]["entity"]
        if statement._for_update_arg is not None:
            self.locks.append(model)
            if self.info["read_only_request"]:
                raise AssertionError("Read request waits for an unrelated account write")
        return self.user if model is User else self.credential if model is AuthSession else None


def test_read_authentication_and_service_rechecks_do_not_wait_for_account_writes():
    session = AuthReadSession()
    principal = AuthService(session).require_active_principal("TEST_ONLY_session")
    CatalogService(session)._principal(principal)
    authorize_admin(session, principal)
    assert session.locks == []


def test_stream_can_explicitly_authenticate_without_locking_account():
    session = AuthReadSession(read_only=False)
    AuthService(session).require_active_principal("TEST_ONLY_session", lock=False)
    assert session.locks == []


def test_mutations_keep_user_then_credential_lock_order():
    session = AuthReadSession(read_only=False)
    principal = AuthService(session).require_active_principal("TEST_ONLY_session")
    assert session.locks == [User, AuthSession]
    session.locks.clear()
    CatalogService(session)._principal(principal)
    assert session.locks == [User, AuthSession]


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS", "POST", "PATCH", "DELETE"])
def test_request_session_only_disables_auth_locks_for_read_methods(method):
    # No SQL is executed: the actual Session only acquires a connection on use.
    request = SimpleNamespace(
        method=method, app=SimpleNamespace(state=SimpleNamespace(engine=object()))
    )
    dependency = get_session(request)
    with next(dependency) as session:
        assert session.info["read_only_request"] is (method in {"GET", "HEAD", "OPTIONS"})
    dependency.close()


def test_read_admin_access_uses_live_database_role():
    session = AuthReadSession()
    principal = AuthService(session).require_active_principal("TEST_ONLY_session")
    session.user.role = "user"
    with pytest.raises(HTTPException) as error:
        authorize_admin(session, principal)
    assert error.value.status_code == 403


@pytest.mark.parametrize("state", ["disabled", "revoked", "expired", "stale", "missing"])
def test_nonlocking_reads_still_reject_invalid_credentials(state):
    session = AuthReadSession()
    if state == "disabled":
        session.user.status = "disabled"
    elif state == "revoked":
        session.credential.revoked_at = now()
    elif state == "expired":
        session.credential.expires_at = now() - timedelta(seconds=1)
    elif state == "stale":
        session.user.auth_version += 1
    else:
        session.credential = None
    with pytest.raises(HTTPException) as error:
        AuthService(session).require_active_principal("TEST_ONLY_session")
    assert error.value.status_code == 401
