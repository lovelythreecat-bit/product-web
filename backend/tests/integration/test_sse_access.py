"""Real MySQL + incremental ASGI transport; no buffered TestClient SSE shortcut."""

import asyncio
import json
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.auth.models import AuthSession, User
from app.auth.security import digest
from app.events.models import DurableEvent
from app.events.service import append_durable_event
from app.ledger.models import CreditAccount, CreditLedger, CreditReservation
from app.ledger.service import freeze_credits, now
from app.main import create_app
from app.tasks.models import GenerationTask
from tests.faults.test_upstream_recovery import calls, submit
from tests.t12_fixtures import upstream as upstream_fixture

upstream = upstream_fixture


@pytest.fixture
def stream_context(mysql_engine, mysql_settings, ledger_task):
    app = create_app(
        mysql_settings.model_copy(
            update={
                "auth_origins": ["https://testserver"],
                "event_retention_seconds": 9 * 86400,
            }
        )
    )
    identities = []
    for _ in range(2):
        uid, token, sid, task = [str(uuid4()) for _ in range(4)]
        with Session(mysql_engine) as s, s.begin():
            s.add(
                User(
                    id=uid,
                    account_normalized="t14_" + uuid4().hex,
                    password_hash="TEST_ONLY",
                    role="user",
                    created_at=now(),
                )
            )
            s.flush()
            s.add(
                CreditAccount(user_id=uid, available=100, frozen=0, consumed=0, credited_total=100)
            )
            s.add(
                AuthSession(
                    id=sid,
                    user_id=uid,
                    token_hash=digest(token),
                    csrf_hash=digest(uuid4().hex),
                    auth_version=0,
                    expires_at=now() + timedelta(hours=1),
                )
            )
            s.flush()
            ledger_task(s, uid, task)
            freeze_credits(s, uid, task, 30)
            # The fixture creates old records once; append-only historical rows stay untouched.
            with patch("app.events.service.now", return_value=now() - timedelta(days=8)):
                append_durable_event(
                    s,
                    uid,
                    "task.updated",
                    {
                        "task_id": task,
                        "state": "SUBMITTED",
                        "state_version": 1,
                    },
                    event_key="TEST_ONLY_initial",
                )
        identities.append((uid, token, sid, task))
    yield app, mysql_engine, identities
    app.state.engine.dispose()


class LiveStream:
    def __init__(self, app, token, query="", headers=None, pause_send=False):
        self.app, self.token, self.query = app, token, query
        self.headers = headers or {}
        self.output = asyncio.Queue()
        self.input = asyncio.Queue()
        self.pause_send = pause_send
        self.blocked = asyncio.Event()
        self.release = asyncio.Event()

    async def send(self, message):
        if self.pause_send and b"event:" in message.get("body", b""):
            self.blocked.set()
            await self.release.wait()
            self.pause_send = False
        await self.output.put(message)

    async def __aenter__(self):
        hdrs = {
            "host": "testserver",
            "cookie": "session=" + self.token,
            "sec-fetch-site": "same-origin",
            **self.headers,
        }
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/api/v1/events",
            "raw_path": b"/api/v1/events",
            "query_string": self.query.encode(),
            "root_path": "",
            "headers": [(k.encode(), v.encode()) for k, v in hdrs.items()],
            "client": ("127.0.0.1", 32100),
            "server": ("testserver", 443),
        }
        await self.input.put({"type": "http.request", "body": b"", "more_body": False})
        self.runner = asyncio.create_task(self.app(scope, self.input.get, self.send))
        start = await asyncio.wait_for(self.output.get(), 5)
        self.status = start["status"]
        self.response_headers = dict(start["headers"])
        return self

    async def event(self):
        while True:
            message = await asyncio.wait_for(self.output.get(), 5)
            body = message.get("body", b"").decode()
            if "event:" in body:
                fields = dict(line.split(": ", 1) for line in body.strip().splitlines())
                fields["data"] = json.loads(fields["data"])
                return fields
            if not message.get("more_body", False):
                return None

    async def __aexit__(self, *_):
        await self.input.put({"type": "http.disconnect"})
        await asyncio.wait_for(self.runner, 5)


def run(coroutine):
    return asyncio.run(coroutine)


def snapshot(engine, uid, task):
    with Session(engine) as s:
        row = s.get(GenerationTask, task)
        account = s.get(CreditAccount, uid)
        reservation = s.scalar(select(CreditReservation).where(CreditReservation.task_id == task))
        counts = tuple(
            s.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE task_id=:t"), {"t": task}
            ).scalar_one()
            for table in (
                "upstream_attempts",
                "dispatch_outbox",
                "works",
                "task_state_events",
            )
        )
        return (
            row.state,
            row.state_version,
            row.settlement_state,
            row.external_submission_id,
            row.upstream_id,
            row.fencing_token,
            account.available,
            account.frozen,
            account.consumed,
            reservation.state,
            s.scalar(
                select(func.count())
                .select_from(GenerationTask)
                .where(GenerationTask.user_id == uid)
            ),
            s.scalar(
                select(func.count()).select_from(CreditLedger).where(CreditLedger.user_id == uid)
            ),
            counts,
        )


@pytest.mark.parametrize("revoke", ["session", "disabled", "version", "expiry"])
def test_sse_cross_user_and_revoked_session(stream_context, revoke):
    app, engine, identities = stream_context
    uid, token, sid, task = identities[0]
    foreign = identities[1]
    before = snapshot(engine, uid, task)

    async def scenario():
        async with LiveStream(app, token) as stream:
            assert stream.status == 200
            event = await stream.event()
            assert event["event"] == "task.updated"
            assert event["data"]["payload"]["task_id"] == task
            assert foreign[3] not in json.dumps(event)
            with engine.begin() as c:
                if revoke == "session":
                    c.execute(
                        text("UPDATE auth_sessions SET revoked_at=UTC_TIMESTAMP(6) WHERE id=:id"),
                        {"id": sid},
                    )
                elif revoke == "expiry":
                    c.execute(
                        text("UPDATE auth_sessions SET expires_at=UTC_TIMESTAMP(6) WHERE id=:id"),
                        {"id": sid},
                    )
                else:
                    change = "status='disabled'" if revoke == "disabled" else "auth_version=1"
                    c.execute(text(f"UPDATE users SET {change} WHERE id=:id"), {"id": uid})
            assert await stream.event() is None
        async with LiveStream(app, token) as stream:
            assert stream.status == 401

    run(scenario())
    assert snapshot(engine, uid, task) == before


def test_reconnect_durable_cursor(stream_context):
    app, engine, identities = stream_context
    uid, token, _, task = identities[0]

    async def scenario():
        async with LiveStream(app, token) as stream:
            assert stream.status == 200
            first = await stream.event()
        with Session(engine) as s, s.begin():
            row = s.get(GenerationTask, task)
            row.state, row.state_version = "QUEUED", 2
            append_durable_event(
                s,
                uid,
                "task.updated",
                {
                    "task_id": task,
                    "state": "QUEUED",
                    "state_version": 2,
                },
                event_key="TEST_ONLY_second",
            )
        # Native EventSource prefers its most recent Last-Event-ID over original URL.
        async with LiveStream(
            app, token, "after=invalid", {"last-event-id": first["id"]}
        ) as stream:
            assert stream.status == 200
            second = await stream.event()
            assert second["data"]["event_seq"] == 2
            assert second["data"]["payload"]["state"] == "QUEUED"
            assert second["data"]["created_at"].endswith("Z")

    run(scenario())


@pytest.mark.parametrize("cursor", ["invalid", "foreign", "ahead", "expired"])
def test_expired_cursor_reset_get_not_post(stream_context, cursor):
    from fastapi.testclient import TestClient

    app, engine, identities = stream_context
    uid, token, _, task = identities[0]
    before = snapshot(engine, uid, task)

    async def scenario():
        async with LiveStream(app, identities[1][1] if cursor == "foreign" else token) as stream:
            assert stream.status == 200
            event = await stream.event()
        after = event["id"]
        if cursor == "invalid":
            after = "garbage"
        elif cursor == "ahead":
            after = uid + ":999999999"
        elif cursor == "expired":
            app.state.settings.event_retention_seconds = 7 * 86400
            after = uid + ":0"
        async with LiveStream(app, token, "after=" + after) as stream:
            assert stream.status == 200
            reset = await stream.event()
            assert reset["event"] == "reset"
            assert reset["data"]["recovery_method"] == "GET"
            assert identities[1][0] not in json.dumps(reset)
            assert identities[1][3] not in json.dumps(reset)
            assert await stream.event() is None
        with TestClient(app, base_url="https://testserver") as client:
            client.cookies.set("session", token)
            response = client.get("/api/v1/tasks/" + task)
            assert response.status_code == 200, response.text
            assert response.json()["task"]["task_id"] == task

    run(scenario())
    assert snapshot(engine, uid, task) == before


def test_retention_keeps_sequence_and_old_key_receipt(stream_context):
    app, engine, identities = stream_context
    uid, token, _, task = identities[0]
    payload = {"task_id": task, "state": "SUBMITTED", "state_version": 1}
    app.state.settings.event_retention_seconds = 7 * 86400

    async def expire():
        async with LiveStream(app, token, "after=" + uid + ":0") as stream:
            assert stream.status == 200
            assert (await stream.event())["event"] == "reset"

    run(expire())
    with Session(engine) as s, s.begin():
        assert (
            s.scalar(
                select(func.count()).select_from(DurableEvent).where(DurableEvent.user_id == uid)
            )
            == 0
        )
        replay = append_durable_event(
            s, uid, "task.updated", payload, event_key="TEST_ONLY_initial"
        )
        assert replay.event_seq == 1
        new = append_durable_event(s, uid, "task.updated", payload, event_key="TEST_ONLY_new")
        assert new.event_seq == 2
        print(
            "T14_RETENTION",
            {
                "user": uid,
                "replayed_seq": replay.event_seq,
                "next_seq": new.event_seq,
                "retained_rows": 1,
            },
        )
        assert (
            s.scalar(
                select(func.count()).select_from(DurableEvent).where(DurableEvent.user_id == uid)
            )
            == 1
        )


def test_fragment_disconnect_no_settle_cancel(stream_context):
    app, engine, identities = stream_context
    uid, token, _, task = identities[0]
    before = snapshot(engine, uid, task)

    async def scenario():
        async with LiveStream(app, token) as stream:
            assert stream.status == 200
            cursor = (await stream.event())["id"]
            with Session(engine) as s:
                app.state.event_fragments.publish(s, uid, task, "TEST_ONLY temporary text")
            fragment = await stream.event()
            assert fragment["event"] == "transient_fragment"
            assert "id" not in fragment
            assert fragment["data"]["test_only"] is True
        # Unstored fragments cannot be replayed. A fresh connection receives a heartbeat.
        async with LiveStream(app, token, "after=" + cursor) as stream:
            assert stream.status == 200
            body = await asyncio.wait_for(stream.output.get(), 5)
            assert b"transient_fragment" not in body.get("body", b"")

    run(scenario())
    assert snapshot(engine, uid, task) == before


@pytest.mark.parametrize(
    "headers,status",
    [
        ({"sec-fetch-site": "cross-site", "origin": "https://evil.invalid"}, 403),
        ({"sec-fetch-site": "same-site"}, 403),
        ({"sec-fetch-site": "", "origin": "https://testserver"}, 200),
        ({"sec-fetch-site": "", "origin": "https://evil.invalid"}, 403),
        ({"sec-fetch-site": ""}, 403),
    ],
)
def test_native_eventsource_same_origin(stream_context, headers, status):
    app, _, identities = stream_context

    async def scenario():
        async with LiveStream(app, identities[0][1], headers=headers) as stream:
            assert stream.status == status

    run(scenario())


def test_backpressure_has_no_connection_and_next_batch_reauthorizes(stream_context):
    app, engine, identities = stream_context
    uid, token, sid, task = identities[0]

    async def scenario():
        async with LiveStream(app, token, pause_send=True) as stream:
            assert stream.status == 200
            await asyncio.wait_for(stream.blocked.wait(), 5)
            assert app.state.engine.pool.checkedout() == 0
            with Session(engine) as s, s.begin():
                row = s.get(GenerationTask, task)
                row.state, row.state_version = "QUEUED", 2
                append_durable_event(
                    s,
                    uid,
                    "task.updated",
                    {
                        "task_id": task,
                        "state": "QUEUED",
                        "state_version": 2,
                    },
                    event_key="TEST_ONLY_queued_while_network_blocked",
                )
                s.get(AuthSession, sid).revoked_at = now()
            stream.release.set()
            first = await stream.event()  # Already handed to ASGI before the revocation.
            assert first["data"]["event_seq"] == 1
            assert await stream.event() is None  # No newly queued batch leaks after revocation.

    run(scenario())


def test_database_lock_wait_does_not_block_event_loop(stream_context):
    app, engine, identities = stream_context
    uid, token, _, _ = identities[0]

    async def scenario():
        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(text("SELECT id FROM users WHERE id=:u FOR UPDATE"), {"u": uid})
            stream = LiveStream(app, token)
            entering = asyncio.create_task(stream.__aenter__())
            try:
                for _ in range(100):
                    if app.state.engine.pool.checkedout():
                        break
                    await asyncio.sleep(0.01)
                assert app.state.engine.pool.checkedout() == 1
                await asyncio.sleep(0.05)  # This executes while authentication waits on a DB lock.
                assert not entering.done()
            finally:
                transaction.rollback()
            await entering
            assert stream.status == 200
            assert (await stream.event())["data"]["event_seq"] == 1
            await stream.__aexit__()

    run(scenario())


def test_permanent_receipts_and_head_are_database_protected(stream_context):
    from sqlalchemy.exc import DBAPIError

    _, engine, identities = stream_context
    uid = identities[0][0]
    statements = [
        "DELETE FROM event_receipts WHERE user_id=:u",
        "UPDATE event_receipts SET event_seq=88 WHERE user_id=:u",
        "DELETE FROM event_heads WHERE user_id=:u",
        "UPDATE event_heads SET last_seq=0 WHERE user_id=:u",
        "DELETE FROM durable_events WHERE user_id=:u",
    ]
    for statement in statements:
        with engine.begin() as c, pytest.raises(DBAPIError):
            c.execute(text(statement), {"u": uid})


def test_fragment_owner_check_and_production_has_no_hub(stream_context):
    from fastapi import HTTPException

    from app.config import Settings

    app, engine, identities = stream_context
    with Session(engine) as s, pytest.raises(HTTPException) as exc:
        app.state.event_fragments.publish(s, identities[0][0], identities[1][3], "secret")
    assert exc.value.status_code == 404
    production = create_app(
        Settings(mode="production", test_only=False, database_url=None, redis_url=None)
    )
    assert production.state.event_fragments is None


@pytest.mark.parametrize(
    "token,query,expected",
    [
        ("", "", 401),
        ("invalid", "", 401),
        ("valid", "token=forbidden", 422),
    ],
)
def test_credentials_cookie_only(stream_context, token, query, expected):
    app, _, identities = stream_context

    async def scenario():
        async with LiveStream(
            app, identities[0][1] if token == "valid" else token, query=query
        ) as stream:
            assert stream.status == expected

    run(scenario())


def test_running_original_survives_disconnect_refresh_and_redis_absence(
    upstream,
    mysql_settings,
    mysql_engine,
):
    task = upstream[2]()
    assert submit(upstream, task).state == "RUNNING"
    token, sid = uuid4().hex, str(uuid4())
    with Session(mysql_engine) as s, s.begin():
        row = s.get(GenerationTask, task)
        uid = row.user_id
        s.add(
            AuthSession(
                id=sid,
                user_id=uid,
                token_hash=digest(token),
                csrf_hash=digest(uuid4().hex),
                auth_version=0,
                expires_at=now() + timedelta(hours=1),
            )
        )
        running_event = append_durable_event(
            s,
            uid,
            "task.updated",
            {
                "task_id": task,
                "state": row.state,
                "state_version": row.state_version,
            },
            event_key="TEST_ONLY_running_stream",
        )
        running_seq = running_event.event_seq
    app = create_app(mysql_settings.model_copy(update={"auth_origins": ["https://testserver"]}))
    assert app.state.auth_redis is None
    before = snapshot(mysql_engine, uid, task)
    upstream_before = calls(upstream, task)
    assert upstream_before["submit"] == upstream_before["generation_intents"] == 1

    async def scenario():
        async with LiveStream(app, token) as stream:
            assert stream.status == 200
            event = await stream.event()
            while event["data"]["event_seq"] < running_seq:
                event = await stream.event()
            assert event["data"]["payload"]["state"] == "RUNNING"
            with Session(mysql_engine) as s:
                app.state.event_fragments.publish(s, uid, task, "TEST_ONLY incomplete")
            assert (await stream.event())["event"] == "transient_fragment"
        async with LiveStream(app, token, "after=" + event["id"]) as stream:
            assert stream.status == 200
        from fastapi.testclient import TestClient

        with TestClient(app, base_url="https://testserver") as client:
            client.cookies.set("session", token)
            response = client.get("/api/v1/tasks/" + task)
            assert response.status_code == 200
            assert response.json()["task"]["state"] == "RUNNING"

    try:
        run(scenario())
        assert snapshot(mysql_engine, uid, task) == before
        assert calls(upstream, task) == upstream_before
        print(
            "T14_RUNNING_DISCONNECT",
            {
                "task": task,
                "before": before,
                "after": snapshot(mysql_engine, uid, task),
                "upstream_before": upstream_before,
                "upstream_after": calls(upstream, task),
            },
        )
    finally:
        app.state.engine.dispose()
