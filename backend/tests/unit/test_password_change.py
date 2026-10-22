"""Password changes use real hashing and authentication without database operations."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.auth import routes, schemas
from app.auth.models import AuthSession, User
from app.auth.security import HASHER, digest, verify_password
from app.auth.service import AuthService
from app.common.errors import register_error_handlers
from app.common.types import Principal
from app.db import get_session

OLD_PASSWORD = "TEST_ONLY_old_password"
NEW_PASSWORD = "TEST_ONLY_new_password"


class MemorySession:
    def __init__(self):
        self.user = User(
            id=str(uuid4()), account_normalized="password-test", role="user",
            status="active", auth_version=0, password_hash=HASHER.hash(OLD_PASSWORD),
        )
        self.credentials = [AuthSession(
            id=str(uuid4()), user_id=self.user.id, token_hash=digest(token),
            csrf_hash=digest("TEST_ONLY_csrf"), auth_version=0, revoked_at=None,
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        ) for token in ("TEST_ONLY_first", "TEST_ONLY_second")]
        self.committed = False

    def scalar(self, statement):
        model = statement.column_descriptions[0]["entity"]
        if model is User:
            return self.user
        if model is AuthSession:
            values = statement.compile().params.values()
            return next((row for row in self.credentials
                         if row.id in values or row.token_hash in values), None)
        raise AssertionError(f"Unexpected query for {model}")

    def get(self, model, identity):
        if model is User and identity == self.user.id:
            return self.user
        if model is AuthSession:
            return next((row for row in self.credentials if row.id == identity), None)
        raise AssertionError(f"Unexpected get for {model}")

    def flush(self):
        pass

    def commit(self):
        self.committed = True


def principal(session):
    return Principal(user_id=session.user.id, session_id=session.credentials[0].id,
                     role="user", auth_version=0)


def test_password_change_invalidates_every_existing_session():
    session = MemorySession()
    auth = AuthService(session)
    actor = auth.require_active_principal("TEST_ONLY_first")
    auth.require_active_principal("TEST_ONLY_second")
    auth.change_password(actor, OLD_PASSWORD, NEW_PASSWORD)
    assert verify_password(session.user.password_hash, NEW_PASSWORD)
    assert not verify_password(session.user.password_hash, OLD_PASSWORD)
    assert session.user.auth_version == 1
    for token in ("TEST_ONLY_first", "TEST_ONLY_second"):
        with pytest.raises(HTTPException) as caught:
            auth.require_active_principal(token)
        assert caught.value.status_code == 401
    assert not session.committed


def test_wrong_current_password_preserves_credentials_and_login():
    session = MemorySession()
    old_hash = session.user.password_hash
    with pytest.raises(HTTPException) as caught:
        AuthService(session).change_password(principal(session), "TEST_ONLY_wrong", NEW_PASSWORD)
    assert caught.value.status_code == 400
    assert session.user.password_hash == old_hash
    assert session.user.auth_version == 0
    AuthService(session).require_active_principal("TEST_ONLY_first")


@pytest.mark.parametrize("new_password", ["x" * 9, "x" * 129])
def test_invalid_new_password_never_changes_credentials(new_password):
    session = MemorySession()
    with pytest.raises(HTTPException) as caught:
        AuthService(session).change_password(principal(session), OLD_PASSWORD, new_password)
    assert caught.value.status_code == 422
    assert verify_password(session.user.password_hash, OLD_PASSWORD)
    assert session.user.auth_version == 0


@pytest.mark.parametrize("state", ["disabled", "revoked", "stale"])
def test_password_change_rechecks_live_identity(state):
    session = MemorySession()
    if state == "disabled":
        session.user.status = "disabled"
    elif state == "revoked":
        session.credentials[0].revoked_at = datetime.now(UTC).replace(tzinfo=None)
    else:
        session.user.auth_version = 1
    with pytest.raises(HTTPException) as caught:
        AuthService(session).change_password(principal(session), OLD_PASSWORD, NEW_PASSWORD)
    assert caught.value.status_code == 401
    assert verify_password(session.user.password_hash, OLD_PASSWORD)


def test_password_http_requires_csrf_validates_input_and_clears_cookies():
    session = MemorySession()
    app = FastAPI()
    app.include_router(routes.router)
    register_error_handlers(app)
    app.state.settings = SimpleNamespace(auth_origins=["https://testserver"], mode="mock")
    app.state.auth_rate_prefix = "TEST_ONLY_password:"
    app.state.auth_redis = SimpleNamespace(eval=lambda *args: 1)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[routes.require_active_principal] = lambda: principal(session)
    with TestClient(app, base_url="https://testserver") as client:
        client.cookies.set("csrf_token", "TEST_ONLY_csrf")
        headers = {"Origin": "https://testserver", "X-Requested-With": "platform"}
        body = {"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD}
        response = client.post("/api/v1/auth/password", json=body, headers=headers)
        assert response.status_code == 403
        assert verify_password(session.user.password_hash, OLD_PASSWORD)
        headers["X-CSRF-Token"] = "TEST_ONLY_csrf"
        invalid = client.post("/api/v1/auth/password", json=body | {"new_password": "short"},
                              headers=headers)
        assert invalid.status_code == 422
        assert OLD_PASSWORD not in invalid.text and "short" not in invalid.text
        wrong = client.post("/api/v1/auth/password",
                            json=body | {"current_password": "TEST_ONLY_wrong"}, headers=headers)
        assert wrong.status_code == 400
        response = client.post("/api/v1/auth/password", json=body, headers=headers)
    assert response.status_code == 204 and not response.content
    assert session.committed
    cookies = response.headers.get_list("set-cookie")
    assert any(cookie.startswith("session=") and "Max-Age=0" in cookie for cookie in cookies)
    assert any(cookie.startswith("csrf_token=") and "Max-Age=0" in cookie for cookie in cookies)
    dto = schemas.PasswordChangeRequest(**body)
    assert OLD_PASSWORD not in repr(dto) and NEW_PASSWORD not in repr(dto)
