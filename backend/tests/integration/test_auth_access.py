from datetime import datetime, timedelta

import pytest
from sqlalchemy import text
from test_registration import registration


def signup(client):
    body = registration()
    response = client.post("/api/v1/auth/register", json=body)
    assert response.status_code == 201, response.text
    client.headers["X-CSRF-Token"] = client.cookies["csrf_token"]
    return body, response.json()["profile"]["user_id"]


def test_logout_revokes_current_credential(auth_client):
    signup(auth_client)
    saved = auth_client.cookies["session"]
    assert auth_client.get("/api/v1/me").status_code == 200
    assert auth_client.post("/api/v1/auth/logout").status_code == 204
    auth_client.cookies.set("session", saved)
    assert auth_client.get("/api/v1/me").status_code == 401


@pytest.mark.parametrize("change", ["status='disabled'", "auth_version=auth_version+1"])
def test_disabled_and_version_revoked(auth_client, mysql_engine, change):
    body, user = signup(auth_client)
    with mysql_engine.begin() as c:
        c.execute(text(f"UPDATE users SET {change} WHERE id=:u"), {"u": user})
    assert auth_client.get("/api/v1/me").status_code == 401
    if change.startswith("status"):
        assert (
            auth_client.post(
                "/api/v1/auth/login", json={k: body[k] for k in ("account", "password")}
            ).status_code
            == 401
        )


def test_expired_session(auth_client, mysql_engine):
    _, user = signup(auth_client)
    with mysql_engine.begin() as c:
        c.execute(
            text("UPDATE auth_sessions SET expires_at=:d WHERE user_id=:u"),
            {"u": user, "d": datetime.now() - timedelta(days=2)},
        )
    assert auth_client.get("/api/v1/me").status_code == 401


def test_csrf_profile_and_cookie_security(auth_client):
    body, user = signup(auth_client)
    login = auth_client.post(
        "/api/v1/auth/login", json={k: body[k] for k in ("account", "password")}
    )
    assert login.status_code == 200
    cookies = login.headers.get_list("set-cookie")
    assert any("HttpOnly" in c and "Secure" in c and "SameSite=lax" in c for c in cookies)
    assert "password" not in login.text and "hash" not in login.text
    auth_client.headers.pop("X-CSRF-Token", None)
    assert auth_client.patch("/api/v1/me", json={"nickname": "安全"}).status_code == 403
    auth_client.headers["X-CSRF-Token"] = auth_client.cookies["csrf_token"]
    assert (
        auth_client.patch("/api/v1/me", json={"nickname": "测试昵称", "bio": "简介"}).status_code
        == 200
    )
    assert auth_client.get("/api/v1/me").json()["nickname"] == "测试昵称"
    for patch in [
        {"nickname": "x" * 41},
        {"nickname": ""},
        {"nickname": None},
        {"bio": "x" * 301},
        {"role": "admin"},
        {"account": "other"},
        {"available": 999},
    ]:
        assert auth_client.patch("/api/v1/me", json=patch).status_code == 422
    # Edited profiles use the current required-name limits; rejected updates
    # must leave the previously saved profile intact.
    profile = auth_client.get("/api/v1/me").json()
    assert profile["nickname"] == "测试昵称" and profile["bio"] == "简介"
    auth_client.headers["Origin"] = "https://evil.invalid"
    assert (
        auth_client.post(
            "/api/v1/auth/login", json={k: body[k] for k in ("account", "password")}
        ).status_code
        == 403
    )


def test_auth_rate_limit(auth_client):
    statuses = [
        auth_client.post(
            "/api/v1/auth/login", json={"account": "missing", "password": "TEST_ONLY_password"}
        ).status_code
        for _ in range(25)
    ]
    assert 429 in statuses


def test_profile_requires_login_and_csrf_is_session_bound(auth_client):
    assert auth_client.get("/api/v1/me").status_code == 401
    body, _ = signup(auth_client)
    old_csrf = auth_client.cookies["csrf_token"]
    response = auth_client.post(
        "/api/v1/auth/login", json={k: body[k] for k in ("account", "password")}
    )
    assert response.status_code == 200
    auth_client.headers["X-CSRF-Token"] = old_csrf
    assert auth_client.patch("/api/v1/me", json={"nickname": "forged"}).status_code == 403
    auth_client.headers["X-CSRF-Token"] = auth_client.cookies["csrf_token"]
    assert auth_client.patch("/api/v1/me", json={"nickname": "persistent"}).status_code == 200
    assert auth_client.post("/api/v1/auth/logout").status_code == 204
    assert (
        auth_client.post(
            "/api/v1/auth/login", json={k: body[k] for k in ("account", "password")}
        ).status_code
        == 200
    )
    assert auth_client.get("/api/v1/me").json()["nickname"] == "persistent"


def test_redis_unavailable_fails_closed_without_registration(auth_client, mysql_engine):
    body = registration()
    auth_client.app.state.auth_redis = None
    assert auth_client.post("/api/v1/auth/register", json=body).status_code == 503
    with mysql_engine.connect() as c:
        assert (
            c.execute(
                text("SELECT COUNT(*) FROM users WHERE account_normalized=:a"),
                {"a": body["account"]},
            ).scalar_one()
            == 0
        )


def test_login_rejects_wrong_password_and_never_exposes_it(auth_client):
    body, _ = signup(auth_client)
    wrong = "TEST_ONLY_wrong_password"
    response = auth_client.post(
        "/api/v1/auth/login", json={"account": body["account"], "password": wrong}
    )
    assert response.status_code == 401
    assert wrong not in response.text and "password_hash" not in response.text
    auth_client.headers.pop("Origin")
    assert auth_client.post("/api/v1/auth/register", json=registration()).status_code == 403
