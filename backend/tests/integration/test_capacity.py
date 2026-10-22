"""Real MySQL storage acceptance: bytes cannot be allocated twice."""

from concurrent.futures import ThreadPoolExecutor
from importlib.util import find_spec
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.policies.schemas import DecisionVersion
from app.policies.service import PolicyService

PNG = Path(__file__).resolve().parents[3] / "contracts/fixtures/agents/TEST_ONLY-orange.png"


@pytest.fixture
def storage(auth_client, mysql_engine):
    r = auth_client.post(
        "/api/v1/auth/register",
        json={
            "account": "sto_" + uuid4().hex,
            "password": "TEST_ONLY_password",
            "request_key": uuid4().hex,
        },
    )
    assert r.status_code == 201
    auth_client.headers["X-CSRF-Token"] = auth_client.cookies["csrf_token"]
    user = r.json()["profile"]["user_id"]
    version = "TEST_ONLY_" + uuid4().hex
    payload = {
        "upload": {
            "max_file_bytes": 180,
            "account_quota_bytes": 200,
            "allowed_types": ["image/png"],
            "reservation_seconds": 120,
            "reclamation_ref": "TEST_ONLY_manual",
            "alert_ref": "TEST_ONLY_monitor",
        },
        "generation": {
            "account_quota_bytes": 200,
            "server_budget_bytes": 100000000,
            "reservation_seconds": 120,
            "reclamation_ref": "TEST_ONLY_manual",
            "alert_ref": "TEST_ONLY_monitor",
        },
    }
    with Session(mysql_engine) as s, s.begin():
        PolicyService(s).add_draft(
            DecisionVersion(
                decision_id="D-10", version=version, mode="mock", test_only=True, payload=payload
            )
        )
    auth_client.app.state.settings = auth_client.app.state.settings.model_copy(
        update={"storage_policy_version": version}
    )
    return auth_client, mysql_engine, user, version


def upload(client, data=None, name="orange.png", mime="image/png"):
    return client.post(
        "/api/v1/files",
        params={"display_name": name},
        headers={"Content-Type": mime},
        content=PNG.read_bytes() if data is None else data,
    )


def test_upload_persists_actual_bytes_and_private_range(storage):
    c, engine, user, version = storage
    r = upload(c)
    assert r.status_code == 201, r.text
    ref = r.json()
    route = "/api/v1/files/" + ref["file_id"] + "/content"
    full = c.get(route)
    assert full.status_code == 200 and full.content == PNG.read_bytes()
    assert full.headers["content-type"] == "image/png"
    assert full.headers["content-length"] == "138"
    part = c.get(route, headers={"Range": "bytes=2-9"})
    assert part.status_code == 206 and part.content == PNG.read_bytes()[2:10]
    assert part.headers["content-range"] == "bytes 2-9/138"
    assert c.get(route, headers={"Range": "bytes=900-"}).status_code == 416
    c.post(
        "/api/v1/auth/register",
        json={
            "account": "sto_" + uuid4().hex,
            "password": "TEST_ONLY_password",
            "request_key": uuid4().hex,
        },
    )
    for range_value in ("bytes=2-9", "invalid", "bytes=900-"):
        assert c.get(route, headers={"Range": range_value}).status_code == 404


def capacity_api():
    assert find_spec("app.storage") is not None, "capacity transaction service is not implemented"
    from app.storage import capacity

    return capacity


def test_concurrent_reservations_can_exceed_retired_account_quota(storage):
    _, engine, user, version = storage
    api = capacity_api()
    barrier = Barrier(2)

    def claim(_):
        with Session(engine) as s:
            barrier.wait()
            try:
                api.reserve_capacity(s, user, uuid4().hex, 150, version)
                s.commit()
                return "reserved"
            except api.StorageError as exc:
                s.rollback()
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(claim, range(2))) == ["reserved", "reserved"]
    from app.storage.models import StorageAccount

    with Session(engine) as session:
        assert session.get(StorageAccount, user).reserved_bytes == 300


def test_rollback_idempotent_reclaim(storage):
    _, engine, user, version = storage
    api = capacity_api()
    from app.storage.models import StorageAccount

    intent = uuid4().hex
    with Session(engine) as s:
        r = api.reserve_capacity(s, user, intent, 180, version)
        assert api.reserve_capacity(s, user, intent, 180, version).id == r.id
        with pytest.raises(api.StorageError, match="IDEMPOTENCY_CONFLICT"):
            api.reserve_capacity(s, user, intent, 179, version)
        s.rollback()
    with Session(engine) as s, s.begin():
        r = api.reserve_capacity(s, user, intent, 180, version)
        api.release_capacity(s, r.id)
        api.release_capacity(s, r.id)
        account = s.scalar(select(StorageAccount).where(StorageAccount.user_id == user))
        assert account.reserved_bytes == account.actual_bytes == 0
    with Session(engine) as s, s.begin():
        r = api.reserve_capacity(s, user, uuid4().hex, 180, version)
        api.finalize_capacity(s, r.id, 138)
        api.finalize_capacity(s, r.id, 138)
        api.release_capacity(s, r.id)
        account = s.scalar(select(StorageAccount).where(StorageAccount.user_id == user))
        assert (account.reserved_bytes, account.actual_bytes) == (0, 138)


def test_magic_mime_path_size(storage):
    c, _, _, _ = storage
    for data, name, mime in [
        (b"fake", "a.png", "image/png"),
        (PNG.read_bytes()[:30], "a.png", "image/png"),
        (PNG.read_bytes(), "../outside.png", "image/png"),
        (PNG.read_bytes(), "a.jpg", "image/png"),
        (PNG.read_bytes(), "a.png", "video/mp4"),
        (PNG.read_bytes() * 2, "a.png", "image/png"),
    ]:
        assert upload(c, data, name, mime).status_code == 422
    assert upload(c).status_code == 201


def set_policy(storage, *, changes=None, mode="mock", status="draft"):
    c, engine, _, old = storage
    with Session(engine) as s, s.begin():
        original = PolicyService(s)._read("D-10", old)
        payload = original.payload
        if changes:
            changes(payload)
        version = ("TEST_ONLY_" if mode == "mock" else "pending_") + uuid4().hex
        PolicyService(s).add_draft(
            DecisionVersion(
                decision_id="D-10",
                version=version,
                mode=mode,
                test_only=mode == "mock",
                status=status,
                payload=payload,
            )
        )
    c.app.state.settings = c.app.state.settings.model_copy(
        update={"storage_policy_version": version, "mode": mode, "test_only": mode == "mock"}
    )
    return version


def test_upload_ignores_retired_budget_and_conflicting_legacy_quota(storage):
    c, _, _, _ = storage
    # Fixture generation section intentionally has no download/source/agent fields.
    assert upload(c).status_code == 201
    for change in (
        lambda p: p["generation"].pop("server_budget_bytes"),
        lambda p: p["generation"].update(account_quota_bytes=999),
        lambda p: p["generation"].update(server_budget_bytes=True),
    ):
        set_policy(storage, changes=change)
        r = upload(c)
        assert r.status_code == 201, r.text


def test_unconfirmed_production_d10_is_closed(storage):
    c, _, _, _ = storage
    set_policy(storage, mode="production")
    assert upload(c).status_code == 403


def test_policy_change_cannot_overwrite_existing_bytes(storage):
    c, engine, user, _ = storage
    assert upload(c).status_code == 201

    def change(p):
        p["upload"]["account_quota_bytes"] = 500
        p["generation"]["account_quota_bytes"] = 500

    set_policy(storage, changes=change)
    assert upload(c).status_code == 201
    from app.storage.models import StorageAccount

    with Session(engine) as s:
        account = s.get(StorageAccount, user)
        assert (account.actual_bytes, account.reserved_bytes) == (276, 0)


def test_failed_upload_rolls_back_all_capacity(storage):
    c, engine, user, _ = storage
    assert upload(c, b"bad").status_code == 422
    from app.storage.models import CapacityReservation, File, StorageAccount

    with Session(engine) as s:
        account = s.get(StorageAccount, user)
        assert (account.actual_bytes, account.reserved_bytes) == (0, 0)
        reservations = s.scalars(
            select(CapacityReservation).where(CapacityReservation.user_id == user)
        ).all()
        assert len(reservations) == 1 and reservations[0].state == "released"
        assert not s.scalars(select(File).where(File.user_id == user)).all()
    assert not list(c.app.state.settings.storage_root.rglob("*.part"))
    assert upload(c).status_code == 201


def test_shared_session_rollback_and_over_actual_capacity(storage):
    _, engine, user, version = storage
    api = capacity_api()
    from app.storage.models import StorageAccount

    with Session(engine) as s:
        r = api.reserve_capacity(s, user, uuid4().hex, 180, version)
        api.finalize_capacity(s, r.id, 201)
        assert r.state == "finalized"
        assert s.get(StorageAccount, user).actual_bytes == 201
        s.rollback()
    with Session(engine) as s:
        assert s.get(StorageAccount, user) is None


def test_download_integrity_and_security_headers(storage):
    c, engine, _, _ = storage
    r = upload(c)
    assert r.status_code == 201
    route = "/api/v1/files/" + r.json()["file_id"] + "/content"
    suffix = c.get(route, headers={"Range": "bytes=-5"})
    assert suffix.status_code == 206 and suffix.content == PNG.read_bytes()[-5:]
    assert suffix.headers["x-content-type-options"] == "nosniff"
    assert suffix.headers["cache-control"] == "private, no-store"
    for value in ("bytes=0-1,4-5", "bytes=-0", "bytes=5-2", "bytes=-", "bad"):
        assert c.get(route, headers={"Range": value}).status_code == 416
    from app.storage.models import File

    with Session(engine) as s:
        file = s.get(File, r.json()["file_id"])
        path = c.app.state.settings.storage_root / (file.internal_path + ".blob")
        path.write_bytes(b"corrupted")
    assert c.get(route).status_code == 404


def test_upload_csrf_and_logout_recheck(storage):
    c, _, _, _ = storage
    c.headers.pop("X-CSRF-Token")
    assert upload(c).status_code == 403
    c.headers["X-CSRF-Token"] = c.cookies["csrf_token"]
    r = upload(c)
    assert r.status_code == 201
    assert c.post("/api/v1/auth/logout").status_code == 204
    assert c.get("/api/v1/files/" + r.json()["file_id"] + "/content").status_code == 401


def test_file_metadata_and_reference_owner_are_database_protected(storage):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    c, engine, user, _ = storage
    r = upload(c)
    assert r.status_code == 201
    with Session(engine) as s:
        with pytest.raises(DBAPIError):
            s.execute(
                text("UPDATE files SET actual_bytes=actual_bytes+1 WHERE id=:id"),
                {"id": r.json()["file_id"]},
            )
        s.rollback()


def test_two_accounts_cannot_overbook_actual_free_disk(storage):
    c, engine, first, _ = storage
    second = c.post(
        "/api/v1/auth/register",
        json={
            "account": "sto_" + uuid4().hex,
            "password": "TEST_ONLY_password",
            "request_key": uuid4().hex,
        },
    ).json()["profile"]["user_id"]

    version = storage[3]
    api = capacity_api()
    barrier = Barrier(2)
    from app.storage.models import StoragePool

    with Session(engine) as s:
        pool = s.get(StoragePool, "mock")
        prior_reserved = pool.reserved_bytes if pool is not None else 0
    # Deterministic real-disk probe, independent of the retired policy budgets.
    # Existing fixture reservations remain protected; two new claims cannot fit.
    free_disk_bytes = prior_reserved + 100000000
    claim_bytes = 50000001

    def claim(user):
        with Session(engine) as s:
            barrier.wait()
            try:
                r = api.reserve_capacity(s, user, uuid4().hex, claim_bytes, version,
                                         free_bytes=lambda: free_disk_bytes)
                s.commit()
                return r.id
            except api.StorageError as exc:
                s.rollback()
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, (first, second)))
    try:
        assert results.count("CAPACITY_INSUFFICIENT") == 1
    finally:
        with Session(engine) as s, s.begin():
            for value in results:
                if value != "CAPACITY_INSUFFICIENT":
                    api.release_capacity(s, value)


def test_two_reservations_cannot_concurrently_expand_beyond_real_free_disk(storage):
    _, engine, user, version = storage
    api = capacity_api()
    from app.storage.models import CapacityReservation, StoragePool

    with Session(engine) as session, session.begin():
        reservations = [api.reserve_capacity(session, user, uuid4().hex, 100, version)
                        for _ in range(2)]
        reservation_ids = [reservation.id for reservation in reservations]
        reserved_before_growth = session.get(StoragePool, "mock").reserved_bytes
    # One additional 100-byte manifest fits, but the two together need 200.
    free_disk_bytes = reserved_before_growth + 150
    barrier = Barrier(2)

    def expand(reservation_id):
        with Session(engine) as session:
            barrier.wait()
            try:
                api.ensure_reserved_capacity(session, reservation_id, 200,
                                             free_bytes=lambda: free_disk_bytes)
                session.commit()
                return "expanded"
            except api.StorageError as error:
                session.rollback()
                return error.code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            assert sorted(executor.map(expand, reservation_ids)) == [
                "CAPACITY_INSUFFICIENT", "expanded"
            ]
        with Session(engine) as session:
            assert sorted(session.get(CapacityReservation, identity).estimated_bytes
                          for identity in reservation_ids) == [100, 200]
            assert session.get(StoragePool, "mock").reserved_bytes == reserved_before_growth + 100
    finally:
        with Session(engine) as session, session.begin():
            for identity in reservation_ids:
                api.release_capacity(session, identity)


def test_commit_failure_retains_recoverable_file_without_visible_record(storage, monkeypatch):
    c, engine, user, _ = storage
    from app.storage.models import File, StorageAccount

    original = Session.commit
    commits = 0

    def fail_commit(session):
        nonlocal commits
        commits += 1
        if commits == 2:
            raise OSError("TEST_ONLY ambiguous completion transport failure")
        original(session)

    monkeypatch.setattr(Session, "commit", fail_commit)
    response = upload(c)
    assert response.status_code == 500
    assert "TEST_ONLY" not in response.text
    monkeypatch.undo()
    with Session(engine) as s:
        assert not s.scalars(select(File).where(File.user_id == user)).all()
        account = s.get(StorageAccount, user)
        assert (account.actual_bytes, account.reserved_bytes) == (0, 180)
    root = c.app.state.settings.storage_root / user.replace("-", "")
    assert len(list(root.glob("*.blob"))) == len(list(root.glob("*.journal"))) == 1


def test_upload_reservation_lifetime_is_independent_from_generation(storage):
    c, engine, _, _ = storage
    set_policy(
        storage,
        changes=lambda p: p["upload"].update(
            reservation_seconds=30, reclamation_ref="TEST_ONLY_upload_manual"
        ),
    )
    assert upload(c).status_code == 201


def test_sql_committed_but_response_failed_preserves_file_and_capacity(storage, monkeypatch):
    c, engine, user, _ = storage
    from app.storage.models import File, StorageAccount

    original = Session.commit

    commits = 0

    def committed_but_disconnected(session):
        nonlocal commits
        commits += 1
        original(session)
        if commits == 2:
            raise OSError("TEST_ONLY connection lost after durable completion commit")

    monkeypatch.setattr(Session, "commit", committed_but_disconnected)
    response = upload(c)
    assert response.status_code == 500 and "TEST_ONLY" not in response.text
    monkeypatch.undo()
    with Session(engine) as s:
        file = s.scalar(select(File).where(File.user_id == user))
        assert file is not None
        file_id = file.id
        account = s.get(StorageAccount, user)
        assert (account.actual_bytes, account.reserved_bytes) == (138, 0)
    root = c.app.state.settings.storage_root / user.replace("-", "")
    assert len(list(root.glob("*.blob"))) == len(list(root.glob("*.journal"))) == 1
    assert c.get("/api/v1/files/" + file_id + "/content").content == PNG.read_bytes()


def test_upload_does_not_require_generation_reservation_rules(storage):
    c, _, _, _ = storage

    def only_upload_reservation(p):
        for key in ("reservation_seconds", "reclamation_ref", "alert_ref"):
            p["generation"].pop(key)

    set_policy(storage, changes=only_upload_reservation)
    assert upload(c).status_code == 201


def test_interleaved_uploads_share_asgi_loop_without_blocking(storage):
    import asyncio
    import time

    import httpx

    c, _, _, _ = storage

    def credentials():
        return {
            "Cookie": "; ".join(f"{k}={v}" for k, v in c.cookies.items()),
            "X-CSRF-Token": c.cookies["csrf_token"],
            "Origin": "https://testserver",
            "X-Requested-With": "platform",
            "Content-Type": "image/png",
        }

    first = credentials()
    r = c.post(
        "/api/v1/auth/register",
        json={
            "account": "sto_" + uuid4().hex,
            "password": "TEST_ONLY_password",
            "request_key": uuid4().hex,
        },
    )
    assert r.status_code == 201
    second = credentials()

    async def scenario():
        started = asyncio.Event()
        times = {}

        async def slow_body():
            started.set()
            before = time.monotonic()
            await asyncio.sleep(0.15)
            times["resume_delay"] = time.monotonic() - before
            yield PNG.read_bytes()

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=c.app), base_url="https://testserver"
        ) as client:

            async def slow():
                return await client.post(
                    "/api/v1/files?display_name=slow.png", headers=first, content=slow_body()
                )

            async def fast():
                await started.wait()
                return await client.post(
                    "/api/v1/files?display_name=fast.png", headers=second, content=PNG.read_bytes()
                )

            async def independent():
                await started.wait()
                before = time.monotonic()
                await asyncio.sleep(0.03)
                r = await client.get("/api/v1/health/live")
                times["independent_delay"] = time.monotonic() - before
                return r

            responses = await asyncio.wait_for(asyncio.gather(slow(), fast(), independent()), 15)
        return responses, times

    responses, times = asyncio.run(scenario())
    print({"interleaved_statuses": [r.status_code for r in responses], "seconds": times})
    assert [r.status_code for r in responses] == [201, 201, 200], [r.text for r in responses]
    assert times["resume_delay"] < 1.0, times
    assert times["independent_delay"] < 1.0, times


def test_one_reservation_accepts_two_files_and_finalizes_aggregate_once(storage):
    from datetime import UTC, datetime

    from app.storage.models import File, StorageAccount

    api = capacity_api()
    _, engine, user, version = storage
    with Session(engine) as s:
        reservation = api.reserve_capacity(s, user, "task:" + uuid4().hex, 180, version)
        for actual in (70, 60):
            s.add(
                File(
                    id=str(uuid4()),
                    version=str(uuid4()),
                    user_id=user,
                    internal_path=uuid4().hex + "/" + uuid4().hex,
                    actual_mime="image/png",
                    actual_bytes=actual,
                    sha256="a" * 64,
                    display_name="result.png",
                    state="durable",
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                    reservation_id=reservation.id,
                )
            )
        s.flush()
        api.finalize_capacity(s, reservation.id, 130)
        api.finalize_capacity(s, reservation.id, 130)
        api.release_capacity(s, reservation.id)
        account = s.get(StorageAccount, user)
        assert (account.actual_bytes, account.reserved_bytes) == (130, 0)
        assert len(s.scalars(select(File).where(File.reservation_id == reservation.id)).all()) == 2
        with pytest.raises(api.StorageError, match="IDEMPOTENCY_CONFLICT"):
            api.finalize_capacity(s, reservation.id, 260)
        s.rollback()


@pytest.mark.parametrize("server_committed", [False, True])
def test_reservation_commit_uncertainty_reclaims_only_unused_upload(
    storage, monkeypatch, server_committed
):
    from app.storage.models import CapacityReservation, File, StorageAccount

    c, engine, user, _ = storage
    original, commits = Session.commit, 0

    def fail_first(session):
        nonlocal commits
        commits += 1
        if commits == 1:
            if server_committed:
                original(session)
            raise OSError("TEST_ONLY reservation commit uncertain")
        original(session)

    monkeypatch.setattr(Session, "commit", fail_first)
    assert upload(c).status_code == 500
    monkeypatch.undo()
    with Session(engine) as s:
        account = s.get(StorageAccount, user)
        if server_committed:
            assert (account.actual_bytes, account.reserved_bytes) == (0, 0)
            r = s.scalar(select(CapacityReservation).where(CapacityReservation.user_id == user))
            assert r.state == "released"
        else:
            assert account is None
        assert not s.scalars(select(File).where(File.user_id == user)).all()
    root = c.app.state.settings.storage_root / user.replace("-", "")
    assert not [p for p in root.glob("*") if p.is_file()]


@pytest.mark.parametrize("server_committed", [False, True])
def test_release_commit_uncertainty_preserves_abort_journal(storage, monkeypatch, server_committed):
    import json

    from app.storage.models import CapacityReservation, File, StorageAccount

    c, engine, user, _ = storage
    original, commits = Session.commit, 0

    def fail_release(session):
        nonlocal commits
        commits += 1
        if commits == 2:
            if server_committed:
                original(session)
            raise OSError("TEST_ONLY release commit uncertain")
        original(session)

    monkeypatch.setattr(Session, "commit", fail_release)
    assert upload(c, b"invalid").status_code == 422
    monkeypatch.undo()
    with Session(engine) as s:
        r = s.scalar(select(CapacityReservation).where(CapacityReservation.user_id == user))
        account = s.get(StorageAccount, user)
        assert r.state == ("released" if server_committed else "reserved")
        assert (account.actual_bytes, account.reserved_bytes) == (0, 0 if server_committed else 180)
        assert not s.scalars(select(File).where(File.user_id == user)).all()
        reservation_id = r.id
    root = c.app.state.settings.storage_root / user.replace("-", "")
    journals = list(root.glob("*.journal"))
    assert len(journals) == 1
    evidence = json.loads(journals[0].read_text())
    assert evidence["state"] == "aborted_before_completion"
    assert evidence["reservation_id"] == reservation_id
    # Recovering this explicitly aborted operation is repeat-safe.
    from app.storage.capacity import release_capacity

    with Session(engine) as s, s.begin():
        release_capacity(s, reservation_id)
        release_capacity(s, reservation_id)


def test_file_cannot_bind_another_users_reservation(storage):
    from datetime import UTC, datetime

    from sqlalchemy.exc import IntegrityError

    from app.storage.models import File

    c, engine, user, version = storage
    other = c.post(
        "/api/v1/auth/register",
        json={
            "account": "sto_" + uuid4().hex,
            "password": "TEST_ONLY_password",
            "request_key": uuid4().hex,
        },
    ).json()["profile"]["user_id"]
    api = capacity_api()
    with Session(engine) as s:
        r = api.reserve_capacity(s, user, "task:" + uuid4().hex, 180, version)
        s.add(
            File(
                id=str(uuid4()),
                version=str(uuid4()),
                user_id=other,
                internal_path=uuid4().hex + "/" + uuid4().hex,
                actual_mime="image/png",
                actual_bytes=70,
                sha256="b" * 64,
                display_name="result.png",
                state="durable",
                created_at=datetime.now(UTC).replace(tzinfo=None),
                reservation_id=r.id,
            )
        )
        with pytest.raises(IntegrityError) as error:
            s.flush()
        assert error.value.orig.args[0] == 1452
        assert "fk_file_reservation_owner" in str(error.value.orig)
        s.rollback()


def test_publish_failure_releases_persisted_reservation(storage, monkeypatch):
    from app.storage.local_store import LocalStore
    from app.storage.models import CapacityReservation, File, StorageAccount

    c, engine, user, _ = storage

    def fail_publish(self, staged):
        raise OSError("TEST_ONLY disk publish failure")

    monkeypatch.setattr(LocalStore, "commit", fail_publish)
    assert upload(c).status_code == 500
    with Session(engine) as s:
        r = s.scalar(select(CapacityReservation).where(CapacityReservation.user_id == user))
        account = s.get(StorageAccount, user)
        assert r.state == "released"
        assert (account.actual_bytes, account.reserved_bytes) == (0, 0)
        assert not s.scalars(select(File).where(File.user_id == user)).all()
    root = c.app.state.settings.storage_root / user.replace("-", "")
    assert not [p for p in root.glob("*") if p.is_file()]


def test_cancellation_never_rolls_back_while_completion_thread_is_running(storage, monkeypatch):
    import asyncio
    import threading
    import time

    import httpx

    from app.storage.models import File, StorageAccount

    c, engine, user, _ = storage
    headers = {
        "Cookie": "; ".join(f"{k}={v}" for k, v in c.cookies.items()),
        "X-CSRF-Token": c.cookies["csrf_token"],
        "Origin": "https://testserver",
        "X-Requested-With": "platform",
        "Content-Type": "image/png",
    }
    original_commit, original_rollback = Session.commit, Session.rollback
    entered, finished = threading.Event(), threading.Event()
    state = {"commits": 0, "overlap": False, "target": None}

    def delayed_completion(session):
        state["commits"] += 1
        if state["commits"] != 2:
            return original_commit(session)
        state["target"] = session
        entered.set()
        time.sleep(0.15)
        try:
            return original_commit(session)
        finally:
            finished.set()

    def checked_rollback(session):
        if session is state["target"] and not finished.is_set():
            state["overlap"] = True
        return original_rollback(session)

    monkeypatch.setattr(Session, "commit", delayed_completion)
    monkeypatch.setattr(Session, "rollback", checked_rollback)

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=c.app), base_url="https://testserver"
        ) as client:
            pending = asyncio.create_task(
                client.post(
                    "/api/v1/files?display_name=cancel.png",
                    headers=headers,
                    content=PNG.read_bytes(),
                )
            )
            while not entered.is_set():
                if pending.done():
                    raise AssertionError("Upload ended before completion commit")
                await asyncio.sleep(0.01)
            pending.cancel()
            try:
                await pending
            except asyncio.CancelledError:
                pass
            while not finished.is_set():
                await asyncio.sleep(0.01)

    asyncio.run(scenario())
    assert state["overlap"] is False
    monkeypatch.undo()
    with Session(engine) as s:
        assert s.scalar(select(File).where(File.user_id == user)) is not None
        account = s.get(StorageAccount, user)
        assert (account.actual_bytes, account.reserved_bytes) == (138, 0)


def test_stream_failure_releases_capacity_and_keeps_no_available_file(storage):
    import asyncio

    import httpx

    from app.storage.models import CapacityReservation, File, StorageAccount

    c, engine, user, _ = storage
    headers = {
        "Cookie": "; ".join(f"{k}={v}" for k, v in c.cookies.items()),
        "X-CSRF-Token": c.cookies["csrf_token"],
        "Origin": "https://testserver",
        "X-Requested-With": "platform",
        "Content-Type": "image/png",
    }

    async def broken_body():
        yield PNG.read_bytes()[:20]
        await asyncio.sleep(0.01)
        raise RuntimeError("TEST_ONLY client stream lost")

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=c.app), base_url="https://testserver"
        ) as client:
            return await client.post(
                "/api/v1/files?display_name=broken.png", headers=headers, content=broken_body()
            )

    response = asyncio.run(scenario())
    assert response.status_code == 500 and "TEST_ONLY" not in response.text
    with Session(engine) as s:
        r = s.scalar(select(CapacityReservation).where(CapacityReservation.user_id == user))
        account = s.get(StorageAccount, user)
        assert r.state == "released"
        assert (account.actual_bytes, account.reserved_bytes) == (0, 0)
        assert not s.scalars(select(File).where(File.user_id == user)).all()
    root = c.app.state.settings.storage_root / user.replace("-", "")
    assert not [p for p in root.glob("*") if p.is_file()]
