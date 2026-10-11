from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import text


def registration():
    return {
        "account": "test_" + uuid4().hex,
        "password": "TEST_ONLY_Long_password9",
        "request_key": uuid4().hex,
    }


def test_registration_grant_exactly_once(auth_client, mysql_engine):
    body = registration()
    response = auth_client.post("/api/v1/auth/register", json=body)
    assert response.status_code == 201, response.text
    user_id = response.json()["profile"]["user_id"]
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(
            pool.map(lambda _: auth_client.post("/api/v1/auth/register", json=body), range(3))
        )
    assert all(r.status_code == 200 for r in responses)
    assert all(r.json()["profile"]["user_id"] == user_id for r in responses)
    with mysql_engine.connect() as c:
        assert (
            c.execute(
                text("SELECT COUNT(*) FROM credit_grants WHERE user_id=:u"), {"u": user_id}
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text("SELECT COUNT(*) FROM credit_ledger WHERE user_id=:u"), {"u": user_id}
            ).scalar_one()
            == 1
        )
    assert (
        auth_client.post(
            "/api/v1/auth/register", json={**body, "password": "different_password"}
        ).status_code
        == 409
    )
    assert (
        auth_client.post(
            "/api/v1/auth/register",
            json={**body, "account": body["account"].upper(), "request_key": uuid4().hex},
        ).status_code
        == 409
    )


def test_registration_interrupt_rolls_back(auth_client, mysql_engine):
    from sqlalchemy import event

    body = registration()

    def interrupt(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO credit_ledger"):
            raise RuntimeError("TEST_ONLY interruption")

    engine = auth_client.app.state.engine
    event.listen(engine, "before_cursor_execute", interrupt)
    try:
        assert auth_client.post("/api/v1/auth/register", json=body).status_code == 500
    finally:
        event.remove(engine, "before_cursor_execute", interrupt)
    with mysql_engine.connect() as c:
        assert (
            c.execute(
                text("SELECT COUNT(*) FROM users WHERE account_normalized=:a"),
                {"a": body["account"]},
            ).scalar_one()
            == 0
        )
    assert auth_client.post("/api/v1/auth/register", json=body).status_code == 201


def test_concurrent_first_registration(auth_client, mysql_engine):
    body = registration()
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(
            pool.map(lambda _: auth_client.post("/api/v1/auth/register", json=body), range(3))
        )
    assert sorted(r.status_code for r in responses) == [200, 200, 201], [
        (r.status_code, r.text) for r in responses
    ]
    user = responses[0].json()["profile"]["user_id"]
    with mysql_engine.connect() as c:
        assert (
            c.execute(
                text("SELECT COUNT(*) FROM credit_grants WHERE user_id=:u"), {"u": user}
            ).scalar_one()
            == 1
        )


def test_grant_freeze_idempotency_conservation_rollback(auth_client, mysql_engine):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.auth.service import AuthService
    from app.ledger.models import CreditAccount, CreditLedger
    from app.ledger.service import LedgerError, freeze_credits, grant_credits

    response = auth_client.post("/api/v1/auth/register", json=registration())
    assert response.status_code == 201
    user = response.json()["profile"]["user_id"]
    with Session(mysql_engine) as s:
        principal = AuthService(s).require_active_principal(auth_client.cookies["session"])
        key, task = uuid4().hex, uuid4()
        grant = grant_credits(s, user, "admin", key, 20, "TEST_ONLY extra", principal)
        assert grant_credits(s, user, "admin", key, 20, "TEST_ONLY extra", principal).id == grant.id
        with pytest.raises(LedgerError):
            grant_credits(s, user, "admin", key, 21, "TEST_ONLY extra", principal)
        reserved = freeze_credits(s, user, task, 30)
        assert freeze_credits(s, user, task, 30).id == reserved.id
        with pytest.raises(LedgerError):
            freeze_credits(s, user, task, 31)
        with pytest.raises(LedgerError) as exc:
            freeze_credits(s, user, uuid4(), 1000)
        assert exc.value.code == "INSUFFICIENT_CREDITS"
        account = s.get(CreditAccount, user)
        assert (account.available, account.frozen, account.consumed, account.credited_total) == (
            90,
            30,
            0,
            120,
        )
        row = s.scalar(select(CreditLedger).where(CreditLedger.reservation_id == reserved.id))
        assert row.balances_before == {"available": 120, "frozen": 0, "consumed": 0}
        assert row.balances_after == {"available": 90, "frozen": 30, "consumed": 0}
        s.rollback()
    with Session(mysql_engine) as s:
        account = s.get(CreditAccount, user)
        assert (account.available, account.frozen, account.consumed, account.credited_total) == (
            100,
            0,
            0,
            100,
        )
        assert (
            s.scalar(select(CreditLedger).where(CreditLedger.reservation_id == reserved.id)) is None
        )


def test_registration_policy_gate_production(auth_client):
    auth_client.app.state.settings.mode = "production"
    response = auth_client.post("/api/v1/auth/register", json=registration())
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FEATURE_NOT_ENABLED"


def test_signup_configuration_changes_only_new_accounts(auth_client, mysql_engine):
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.orm import Session

    from app.ledger.models import RegistrationCreditHead
    from app.ledger.service import set_registration_credit_config
    from app.policies.schemas import DecisionVersion
    from app.policies.service import PolicyService

    body = registration()
    old = auth_client.post("/api/v1/auth/register", json=body)
    assert old.status_code == 201
    old_user = old.json()["profile"]["user_id"]
    with Session(mysql_engine) as s, s.begin():
        policy = "TEST_ONLY_" + uuid4().hex
        PolicyService(s).add_draft(
            DecisionVersion(
                decision_id="D-05",
                version=policy,
                mode="mock",
                test_only=True,
                payload={"registration": {"credits": 45}},
            )
        )
        previous = s.get(RegistrationCreditHead, "mock").version
        config = set_registration_credit_config(
            s,
            mode="mock",
            expected_version=previous,
            amount=45,
            policy_version=policy,
            reason="TEST_ONLY adjustment",
        )
        version = config.version
    new = auth_client.post("/api/v1/auth/register", json=registration())
    assert new.status_code == 201
    assert auth_client.post("/api/v1/auth/register", json=body).status_code == 200
    with mysql_engine.connect() as c:
        assert (
            c.execute(
                text("SELECT available FROM credit_accounts WHERE user_id=:u"), {"u": old_user}
            ).scalar_one()
            == 100
        )
        assert (
            c.execute(
                text("SELECT available FROM credit_accounts WHERE user_id=:u"),
                {"u": new.json()["profile"]["user_id"]},
            ).scalar_one()
            == 45
        )
        assert (
            c.execute(
                text("SELECT config_version FROM registration_receipts WHERE user_id=:u"),
                {"u": old_user},
            ).scalar_one()
            == previous
        )
        with pytest.raises(DBAPIError):
            c.execute(
                text("UPDATE registration_credit_configs SET amount=999 WHERE version=:v"),
                {"v": version},
            )
        c.rollback()


def test_database_rejects_balance_corruption(auth_client, mysql_engine):
    from sqlalchemy.exc import DBAPIError

    response = auth_client.post("/api/v1/auth/register", json=registration())
    assert response.status_code == 201
    with mysql_engine.connect() as c:
        with pytest.raises(DBAPIError):
            c.execute(
                text("UPDATE credit_accounts SET available=available+1 WHERE user_id=:u"),
                {"u": response.json()["profile"]["user_id"]},
            )
        c.rollback()


def test_same_key_different_account_never_creates_second_user(auth_client, mysql_engine):
    body = registration()
    assert auth_client.post("/api/v1/auth/register", json=body).status_code == 201
    other = {**body, "account": "test_" + uuid4().hex}
    assert auth_client.post("/api/v1/auth/register", json=other).status_code == 409
    with mysql_engine.connect() as c:
        assert (
            c.execute(
                text("SELECT COUNT(*) FROM users WHERE account_normalized=:a"),
                {"a": other["account"]},
            ).scalar_one()
            == 0
        )


def test_concurrent_grants_and_freezes_serialize(auth_client, mysql_engine):
    from sqlalchemy.orm import Session

    from app.auth.service import AuthService
    from app.ledger.service import freeze_credits, grant_credits

    response = auth_client.post("/api/v1/auth/register", json=registration())
    assert response.status_code == 201
    user = response.json()["profile"]["user_id"]
    with Session(mysql_engine) as s:
        actor = AuthService(s).require_active_principal(auth_client.cookies["session"])
    key, task = uuid4().hex, uuid4()

    def apply(_):
        with Session(mysql_engine) as s, s.begin():
            grant = grant_credits(s, user, "admin", key, 20, "TEST_ONLY concurrent", actor)
            frozen = freeze_credits(s, user, task, 30)
            return grant.id, frozen.id

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(apply, range(3)))
    assert len(set(results)) == 1
    with mysql_engine.connect() as c:
        assert tuple(
            c.execute(
                text(
                    "SELECT available,frozen,consumed,credited_total "
                    "FROM credit_accounts WHERE user_id=:u"
                ),
                {"u": user},
            ).one()
        ) == (90, 30, 0, 120)
        assert (
            c.execute(
                text("SELECT COUNT(*) FROM credit_ledger WHERE user_id=:u"), {"u": user}
            ).scalar_one()
            == 3
        )


def test_freeze_interrupt_rolls_back_caller_transaction(auth_client, mysql_engine):
    from sqlalchemy import event
    from sqlalchemy.orm import Session

    from app.ledger.service import freeze_credits

    body = registration()
    response = auth_client.post("/api/v1/auth/register", json=body)
    assert response.status_code == 201
    user, task = response.json()["profile"]["user_id"], uuid4()

    def interrupt(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO credit_ledger"):
            raise RuntimeError("TEST_ONLY ledger interruption")

    event.listen(mysql_engine, "before_cursor_execute", interrupt)
    try:
        with pytest.raises(RuntimeError):
            with Session(mysql_engine) as s, s.begin():
                freeze_credits(s, user, task, 30)
    finally:
        event.remove(mysql_engine, "before_cursor_execute", interrupt)
    with mysql_engine.connect() as c:
        assert tuple(
            c.execute(
                text(
                    "SELECT available,frozen,consumed,credited_total "
                    "FROM credit_accounts WHERE user_id=:u"
                ),
                {"u": user},
            ).one()
        ) == (100, 0, 0, 100)
        assert (
            c.execute(
                text("SELECT COUNT(*) FROM credit_reservations WHERE task_id=:t"), {"t": str(task)}
            ).scalar_one()
            == 0
        )


def test_password_argon2_and_audit_no_secrets(auth_client, mysql_engine):
    body = registration()
    response = auth_client.post("/api/v1/auth/register", json=body)
    assert response.status_code == 201
    with mysql_engine.connect() as c:
        encoded = c.execute(
            text("SELECT password_hash FROM users WHERE id=:u"),
            {"u": response.json()["profile"]["user_id"]},
        ).scalar_one()
        assert encoded.startswith("$argon2id$")
        assert body["password"] not in encoded
        assert encoded not in response.text and body["password"] not in response.text
        assert (
            c.execute(
                text("SELECT COUNT(*) FROM audit_events WHERE CAST(changes AS CHAR) LIKE :v"),
                {"v": "%" + body["password"] + "%"},
            ).scalar_one()
            == 0
        )


def test_registration_replay_cannot_bypass_production_gate(auth_client):
    body = registration()
    assert auth_client.post("/api/v1/auth/register", json=body).status_code == 201
    auth_client.app.state.settings.mode = "production"
    response = auth_client.post("/api/v1/auth/register", json=body)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FEATURE_NOT_ENABLED"
