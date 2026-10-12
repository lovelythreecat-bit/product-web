"""T19a focused permissions/financial/CAS/cursor checks against isolated MySQL."""

from datetime import UTC, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin.models import ContentAccessGrant
from app.admin.service import list_tasks, list_users
from app.audit.models import AuditEvent
from app.auth.models import AuthSession, User
from app.auth.security import digest
from app.common.types import Principal
from app.config import Settings
from app.conversations.models import Conversation, Message
from app.investigations.models import Investigation
from app.investigations.routes import list_investigations
from app.ledger.models import CreditAccount, CreditLedger
from app.ledger.service import now
from app.policies.schemas import DecisionVersion
from app.policies.service import PolicyService
from app.storage.models import File


def identity(session, role="admin"):
    uid, sid, token, csrf = [str(uuid4()) for _ in range(4)]
    session.add(
        User(
            id=uid,
            account_normalized="t19_" + uuid4().hex,
            password_hash="TEST_ONLY_PASSWORD_HASH",
            role=role,
            created_at=now(),
        )
    )
    session.flush()
    session.add(CreditAccount(user_id=uid))
    session.add(
        AuthSession(
            id=sid,
            user_id=uid,
            token_hash=digest(token),
            csrf_hash=digest(csrf),
            auth_version=0,
            expires_at=now() + timedelta(hours=1),
        )
    )
    session.flush()
    return dict(id=uid, sid=sid, token=token, csrf=csrf, role=role)


def login(client, actor):
    client.cookies.clear()
    client.cookies.set("session", actor["token"])
    client.cookies.set("csrf_token", actor["csrf"])
    client.headers["X-CSRF-Token"] = actor["csrf"]


@pytest.fixture
def desk(auth_client, mysql_engine):
    with Session(mysql_engine) as session, session.begin():
        approver, reader, owner = identity(session), identity(session), identity(session, "user")
        conversation = Conversation(
            id=str(uuid4()),
            user_id=owner["id"],
            title="TEST_ONLY private conversation",
            created_at=now(),
        )
        session.add(conversation)
        session.flush()
        message = Message(
            id=str(uuid4()),
            user_id=owner["id"],
            conversation_id=conversation.id,
            kind="authored",
            role="user",
            content={"text": "TEST_ONLY private body"},
            created_at=now(),
        )
        session.add(message)
        session.flush()
        message_id = message.id
    auth_client.app.state.settings = auth_client.app.state.settings.model_copy(
        update={"test_only_content_approver_ids": [UUID(approver["id"])]}
    )
    login(auth_client, reader)
    return auth_client, approver, reader, owner, message_id


def grant_body(desk):
    _, _, reader, owner, message = desk
    return dict(
        actor_id=reader["id"],
        scope=dict(user_id=owner["id"], resource_type="message", resource_id=message),
        reason="TEST_ONLY customer investigation",
        expires_at=(now() + timedelta(hours=1)).replace(tzinfo=UTC).isoformat(),
    )


def test_admin_grant_same_key_once_and_target_ledger(desk, mysql_engine):
    client, _, reader, owner, _ = desk
    body = dict(
        user_id=owner["id"], business_key=uuid4().hex, amount=31, reason="TEST_ONLY support"
    )
    first = client.post("/api/v1/admin/credit-grants", json=body)
    assert first.status_code == 200, first.text
    replay = client.post("/api/v1/admin/credit-grants", json=body)
    assert replay.json() == first.json()
    assert (
        client.post("/api/v1/admin/credit-grants", json={**body, "amount": 32}).status_code == 409
    )
    assert (
        client.post(
            "/api/v1/admin/credit-grants", json={**body, "user_id": reader["id"]}
        ).status_code
        == 409
    )
    account = client.get(f"/api/v1/admin/users/{owner['id']}/account").json()
    assert account == dict(available=31, frozen=0, consumed=0, credited_total=31)
    entries = client.get(f"/api/v1/admin/users/{owner['id']}/ledger").json()["items"]
    assert len(entries) == 1 and entries[0]["amount"] == 31
    assert (
        client.get(
            f"/api/v1/admin/users/{reader['id']}/ledger", params={"cursor": entries[0]["ledger_id"]}
        ).status_code
        == 404
    )
    with Session(mysql_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(CreditLedger)
                .where(CreditLedger.grant_id == first.json()["id"])
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.action == "admin_credit_grant",
                    AuditEvent.object_id == first.json()["id"],
                )
            )
            == 1
        )
    users = client.get("/api/v1/admin/users", params={"limit": 1}).json()
    assert "password_hash" not in str(users)
    assert (
        client.get("/api/v1/admin/users", params={"cursor": users["next_cursor"]}).status_code
        == 200
    )


def test_non_admin_and_csrf_denied(desk):
    client, _, _, owner, message = desk
    login(client, owner)
    for path in (
        "users",
        f"users/{owner['id']}/account",
        f"users/{owner['id']}/ledger",
        "tasks",
        "statistics",
        "audit",
        "registration-credit-config",
        "content-access-grants",
    ):
        assert client.get("/api/v1/admin/" + path).status_code == 403, path
    assert (
        client.get(
            f"/api/v1/admin/content/message/{message}", params={"reason": "test"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/admin/credit-grants",
            json=dict(user_id=owner["id"], business_key=uuid4().hex, amount=1, reason="test"),
        ).status_code
        == 403
    )
    login(client, desk[2])
    client.headers.pop("X-CSRF-Token")
    assert (
        client.post(
            "/api/v1/admin/credit-grants",
            json=dict(user_id=owner["id"], business_key=uuid4().hex, amount=1, reason="test"),
        ).status_code
        == 403
    )


def test_content_audit_reason_revocation(desk, mysql_engine):
    client, approver, reader, owner, message = desk
    path = f"/api/v1/admin/content/message/{message}"
    assert client.get(path, params={"reason": "test"}).status_code == 403
    body = grant_body(desk)
    assert client.post("/api/v1/admin/content-access-grants", json=body).status_code == 403
    login(client, approver)
    assert (
        client.post(
            "/api/v1/admin/content-access-grants", json={**body, "actor_id": approver["id"]}
        ).status_code
        == 403
    )
    response = client.post("/api/v1/admin/content-access-grants", json=body)
    assert response.status_code == 201, response.text
    grant_id = response.json()["id"]
    login(client, reader)
    assert client.get(path).status_code == 422
    assert client.get(path, params={"reason": "   "}).status_code == 422
    read = client.get(path, params={"reason": "TEST_ONLY approved read"})
    assert read.status_code == 200, read.text
    assert read.json()["content"]["content"]["text"] == "TEST_ONLY private body"
    assert read.headers["cache-control"] == "private, no-store"
    assert (
        client.get(
            f"/api/v1/admin/content/message/{uuid4()}", params={"reason": "test"}
        ).status_code
        == 403
    )
    with Session(mysql_engine) as session:
        audit = session.get(AuditEvent, read.json()["audit_id"])
        assert audit.actor_id == reader["id"] and audit.object_id == message
        assert audit.reason == "TEST_ONLY approved read" and audit.changes["grant_id"] == grant_id
        assert "private body" not in str(audit.changes)
    assert (
        client.post(
            f"/api/v1/admin/content-access-grants/{grant_id}/revoke", json={"reason": "test"}
        ).status_code
        == 403
    )
    login(client, approver)
    assert (
        client.post(
            f"/api/v1/admin/content-access-grants/{grant_id}/revoke",
            json={"reason": "TEST_ONLY revoked"},
        ).status_code
        == 200
    )
    login(client, reader)
    assert client.get(path, params={"reason": "test"}).status_code == 403


def test_expired_grant_and_production_authority_closed(desk, mysql_engine):
    client, approver, reader, _, message = desk
    login(client, approver)
    response = client.post("/api/v1/admin/content-access-grants", json=grant_body(desk))
    assert response.status_code == 201, response.text
    with Session(mysql_engine) as session, session.begin():
        grant = session.get(ContentAccessGrant, response.json()["id"])
        grant.created_at, grant.expires_at = now() - timedelta(hours=2), now() - timedelta(hours=1)
    login(client, reader)
    assert (
        client.get(
            f"/api/v1/admin/content/message/{message}", params={"reason": "test"}
        ).status_code
        == 403
    )
    with pytest.raises(ValidationError):
        Settings(
            mode="production", test_only=False, test_only_content_approver_ids=[approver["id"]]
        )
    login(client, approver)
    client.app.state.settings = client.app.state.settings.model_copy(
        update={"mode": "production", "test_only": False, "test_only_content_approver_ids": []}
    )
    assert (
        client.post("/api/v1/admin/content-access-grants", json=grant_body(desk)).status_code == 403
    )


def test_registration_config_cas_gate_only_new_registrations(desk, mysql_engine):
    client, _, reader, owner, _ = desk
    current = client.get("/api/v1/admin/registration-credit-config").json()
    version = "TEST_ONLY_" + uuid4().hex
    with Session(mysql_engine) as session, session.begin():
        PolicyService(session).add_draft(
            DecisionVersion(
                decision_id="D-05",
                version=version,
                mode="mock",
                test_only=True,
                payload={"registration": {"credits": 17}},
            )
        )
    body = dict(
        expected_version=current["version"],
        amount=17,
        policy_version=version,
        reason="TEST_ONLY new registrations",
    )
    changed = client.patch("/api/v1/admin/registration-credit-config", json=body)
    assert changed.status_code == 200, changed.text
    assert client.patch("/api/v1/admin/registration-credit-config", json=body).status_code == 409
    assert (
        client.patch(
            "/api/v1/admin/registration-credit-config",
            json={**body, "expected_version": changed.json()["version"], "amount": 18},
        ).status_code
        == 403
    )
    assert client.get(f"/api/v1/admin/users/{owner['id']}/account").json()["credited_total"] == 0
    created = client.post(
        "/api/v1/auth/register",
        json={
            "account": "t19_" + uuid4().hex,
            "password": "TEST_ONLY_Long_password9",
            "request_key": uuid4().hex,
        },
    )
    assert created.status_code == 201, created.text
    assert client.get("/api/v1/account").json()["available"] == 17
    login(client, reader)
    audit = client.get(
        "/api/v1/admin/audit", params={"object_id": changed.json()["version"]}
    ).json()
    assert audit["items"][0]["changes"]["amount"] == 17


def test_diagnostics_no_body_without_content_grant(desk, mysql_engine, ledger_task):
    client, _, _, owner, _ = desk
    with Session(mysql_engine) as session, session.begin():
        task = ledger_task(session, owner["id"], uuid4())
        task.investigation_reason = "TEST_ONLY_SECRET_PROVIDER_ERROR"
        task_id = task.id
    response = client.get(f"/api/v1/admin/tasks/{task_id}/diagnostics")
    assert response.status_code == 200, response.text
    assert "TEST_ONLY_SECRET" not in response.text and "input_snapshot" not in response.text
    assert "instruction" not in response.text
    assert client.get("/api/v1/admin/tasks", params={"user_id": owner["id"]}).status_code == 200
    stats = client.get("/api/v1/admin/statistics").json()
    assert stats["supplier_cost_status"] == "unavailable" and stats["supplier_cost"] is None
    assert stats["payment_revenue_status"] == "not_supported"


def test_scoped_download_and_audit_redaction(desk, mysql_engine, ledger_task, tmp_path):
    client, approver, reader, owner, _ = desk
    root = tmp_path / "TEST_ONLY_content"
    root.mkdir()
    key = UUID(owner["id"]).hex + "/" + uuid4().hex
    blob = root / (key + ".blob")
    blob.parent.mkdir()
    blob.write_bytes(b"x")
    file_id = str(uuid4())
    with Session(mysql_engine) as session, session.begin():
        task = ledger_task(session, owner["id"], uuid4())
        session.add(
            File(
                id=file_id,
                user_id=owner["id"],
                version=str(uuid4()),
                internal_path=key,
                actual_mime="text/plain",
                actual_bytes=1,
                sha256=sha256(b"x").hexdigest(),
                display_name="TEST_ONLY.txt",
                reservation_id=task.capacity_reservation_id,
                created_at=now(),
            )
        )
        session.add(
            AuditEvent(
                id=str(uuid4()),
                actor_id=reader["id"],
                action="TEST_ONLY_redaction",
                object_id=file_id,
                reason="TEST_ONLY audit projection",
                changes={
                    "amount": 1,
                    "password_hash": "TEST_ONLY_SECRET",
                    "input_snapshot": {"instruction": "private"},
                },
                created_at=now(),
            )
        )
    client.app.state.settings = client.app.state.settings.model_copy(update={"storage_root": root})
    path = f"/api/v1/admin/content/file/{file_id}/download"
    assert client.get(path, params={"reason": "test"}, headers={"Range": "bad"}).status_code == 403
    body = grant_body(desk)
    body["scope"].update(resource_type="file", resource_id=file_id)
    login(client, approver)
    grant = client.post("/api/v1/admin/content-access-grants", json=body)
    assert grant.status_code == 201, grant.text
    login(client, reader)
    read = client.get(path, params={"reason": "TEST_ONLY download"}, headers={"Range": "bytes=0-0"})
    assert read.status_code == 206 and read.content == b"x"
    assert read.headers["cache-control"] == "private, no-store"
    assert client.get(f"/api/v1/files/{file_id}/content").status_code == 404
    audit = client.get("/api/v1/admin/audit", params={"object_id": file_id})
    assert audit.status_code == 200 and "TEST_ONLY_SECRET" not in audit.text
    assert "input_snapshot" not in audit.text and "private" not in audit.text
    assert any(item["action"] == "content_access_read" for item in audit.json()["items"])
    login(client, approver)
    assert (
        client.post(
            f"/api/v1/admin/content-access-grants/{grant.json()['id']}/revoke",
            json={"reason": "TEST_ONLY stop"},
        ).status_code
        == 200
    )
    login(client, reader)
    assert client.get(path, params={"reason": "test"}).status_code == 403


@pytest.mark.parametrize("change", ["resolved", "transferred"])
def test_investigation_cursor_survives_anchor_change(db_session, ledger_task, change):
    session = db_session
    actor, other = identity(session), identity(session)
    principal = Principal(
        user_id=actor["id"], session_id=actor["sid"], role="admin", auth_version=0
    )
    cases = []
    for offset in range(3):
        task = ledger_task(session, actor["id"], uuid4())
        case = Investigation(
            task_id=task.id,
            owner=actor["id"],
            policy_version="TEST_ONLY_cursor",
            evidence="TEST_ONLY:cursor",
            status="open",
            version=1,
            deadline_at=now() + timedelta(hours=1),
            created_at=now() - timedelta(minutes=offset),
        )
        session.add(case)
        cases.append(case)
    session.flush()
    first = list_investigations(session, principal, owner=UUID(actor["id"]), limit=1)
    assert first["next_cursor"] == cases[0].task_id
    if change == "resolved":
        cases[0].status = "resolved"
    else:
        cases[0].owner = other["id"]
    cases[2].owner = other["id"]
    session.flush()
    second = list_investigations(
        session, principal, cursor=UUID(first["next_cursor"]), owner=UUID(actor["id"]), limit=20
    )
    assert [case.task_id for case in second["items"]] == [cases[1].task_id]
    session.get(User, actor["id"]).role = "user"
    session.flush()
    with pytest.raises(HTTPException) as denied:
        list_investigations(session, principal, cursor=UUID(first["next_cursor"]), limit=20)
    assert denied.value.status_code == 403


def test_admin_state_cursors_keep_scope_and_live_authorization(db_session, ledger_task):
    session = db_session
    actor, owner, other = identity(session), identity(session, "user"), identity(session, "user")
    principal = Principal(
        user_id=actor["id"], session_id=actor["sid"], role="admin", auth_version=0
    )
    created = now()
    first_user, next_user = session.get(User, owner["id"]), session.get(User, other["id"])
    first_user.created_at, next_user.created_at = (
        created + timedelta(minutes=2),
        created + timedelta(minutes=1),
    )
    first_user.status = next_user.status = "disabled"
    session.flush()
    first = list_users(session, principal, None, 1, status="disabled")
    assert str(first.items[0].id) == owner["id"] and first.next_cursor == owner["id"]
    first_user.status = "active"
    session.flush()
    following = list_users(session, principal, first.next_cursor, 1, status="disabled")
    assert [str(item.id) for item in following.items] == [other["id"]]
    next_user.status = "active"  # The following task fixtures require active owners.
    session.flush()

    tasks = []
    for user_id in (owner["id"], owner["id"], other["id"], owner["id"]):
        task = ledger_task(session, user_id, uuid4())
        tasks.append(task)
    tasks.reverse()  # Newest first, preserving the database's immutable admission timestamps.
    tasks[3].state = "RUNNING"
    session.flush()
    first = list_tasks(session, principal, None, 1, state="SUBMITTED", user_id=owner["id"])
    assert str(first.items[0].id) == tasks[0].id and first.next_cursor == tasks[0].id
    tasks[0].state = "RUNNING"
    session.flush()
    following = list_tasks(
        session, principal, first.next_cursor, 20, state="SUBMITTED", user_id=owner["id"]
    )
    assert [str(item.id) for item in following.items] == [tasks[2].id]
    with pytest.raises(HTTPException) as cross_owner:
        list_tasks(session, principal, tasks[1].id, 20, state="SUBMITTED", user_id=owner["id"])
    assert cross_owner.value.status_code == 422

    session.get(User, actor["id"]).role = "user"
    session.flush()
    for read in (
        lambda: list_users(session, principal, owner["id"], 1, status="disabled"),
        lambda: list_tasks(
            session, principal, first.next_cursor, 20, state="SUBMITTED", user_id=owner["id"]
        ),
    ):
        with pytest.raises(HTTPException) as denied:
            read()
        assert denied.value.status_code == 403
