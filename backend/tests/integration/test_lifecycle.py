"""T17 uses real MySQL/API/storage; policy samples are TEST_ONLY, never defaults."""

from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.auth.models import AuthSession, User
from app.ledger.models import CreditAccount, CreditLedger
from app.policies.schemas import DecisionVersion
from app.policies.service import PolicyService
from app.storage.models import File, FileRef, StorageAccount
from app.tasks.models import GenerationTask
from tests.integration.test_works_history import (
    base_upstream as base_upstream_fixture,
)
from tests.integration.test_works_history import (
    current_catalog_for_source,
    token_for,
)
from tests.integration.test_works_history import (
    published as published_fixture,
)
from tests.integration.test_works_history import (
    ready as ready_fixture,
)
from tests.integration.test_works_history import (
    upstream as upstream_fixture,
)
from tests.integration.test_works_history import (
    works_task as works_task_fixture,
)

base_upstream = base_upstream_fixture
published = published_fixture
ready = ready_fixture
upstream = upstream_fixture
works_task = works_task_fixture


@pytest.fixture
def policy(upstream):
    version = "TEST_ONLY_" + uuid4().hex
    payload = {
        "delete": {
            k: "TEST_ONLY"
            for k in (
                "list_history_ref",
                "old_links_ref",
                "restoration_ref",
                "retention_reclamation_ref",
                "capacity_ref",
                "inflight_protection_ref",
            )
        },
        "account_disable": {
            k: "TEST_ONLY"
            for k in (
                "tasks_ref",
                "frozen_credits_ref",
                "works_access_ref",
                "restoration_ref",
                "exception_handoff_ref",
            )
        },
    }
    payload["delete"]["execution"] = {
        "schema_version": "lifecycle-delete-v1",
        "list": "hide",
        "history": "tombstone",
        "old_links": "deny",
        "restoration": "disabled",
        "references": "retain_all",
        "capacity": "until_physical_removal",
        "retention_seconds": 0,
        "unreferenced_cleanup": True,
    }
    payload["account_disable"]["execution"] = {
        "schema_version": "lifecycle-disable-v1",
        "inflight": "continue_original",
        "frozen_credits": "retain",
        "works_access": "deny",
        "restoration": "new_login",
        "exception_policy_version": version,
    }
    with upstream[0]() as s, s.begin():
        service = PolicyService(s)
        service.add_draft(
            DecisionVersion(
                decision_id="D-09", version=version, mode="mock", test_only=True, payload=payload
            )
        )
        service.add_draft(
            DecisionVersion(
                decision_id="D-08",
                version=version,
                mode="mock",
                test_only=True,
                payload={
                    "generation": {
                        "investigation_deadline_seconds": 60,
                        "responsible_party_ref": "TEST_ONLY",
                        "settlement_evidence_ref": "TEST_ONLY",
                        "late_delivery_ref": "TEST_ONLY",
                        "save_failure_ref": "TEST_ONLY",
                        "deadline_is_failure": False,
                        "requires_complete_delivery": True,
                    }
                },
            )
        )
    print("T17_POLICY", version)
    return version


def delete(client, kind, id, policy):
    return client.request("DELETE", f"/api/v1/{kind}/{id}", json={"policy_version": policy})


def test_deleted_history_links_by_policy(published, upstream, policy):
    client, create, login = published
    original = create()
    login(original["user_id"])
    detail = client.get("/api/v1/works/" + original["work_id"]).json()
    before = client.get("/api/v1/account").json()
    with upstream[0]() as s:
        capacity = s.get(StorageAccount, original["user_id"]).actual_bytes
    response = delete(client, "works", original["work_id"], policy)
    assert response.status_code == 200, response.text
    assert delete(client, "works", original["work_id"], policy).status_code == 200
    assert client.get("/api/v1/works").json()["items"] == []
    assert client.get("/api/v1/works/" + original["work_id"]).status_code == 404
    for headers in ({}, {"Range": "bytes=0-3"}):
        assert client.get(detail["items"][0]["content_url"], headers=headers).status_code == 404
    history = client.get("/api/v1/conversations/" + original["conversation_id"]).json()
    final = next(m for m in history["messages"]["items"] if m["kind"] == "final")
    assert final["content"] == {"deleted": True, "policy_version": policy}
    assert history["tasks"]["items"][0]["task_id"] == original["task_id"]
    assert client.get("/api/v1/account").json() == before
    with upstream[0]() as s:
        assert s.get(StorageAccount, original["user_id"]).actual_bytes == capacity
    other = create(owner="b")
    login(other["user_id"])
    assert delete(client, "works", original["work_id"], policy).status_code == 404
    assert delete(client, "files", detail["items"][0]["file_id"], policy).status_code == 404


def test_inflight_material_protected(published, upstream, policy):
    client, create, login = published
    material_work = create("image")
    login(material_work["user_id"])
    item = client.get("/api/v1/works/" + material_work["work_id"]).json()["items"][0]
    upstream[2].materials = [{"file_id": item["file_id"], "version": item["file_version"]}]
    pending = create(publish=False)
    assert delete(client, "files", item["file_id"], policy).status_code == 409
    assert delete(client, "works", material_work["work_id"], policy).status_code == 409
    with upstream[0]() as s:
        assert s.get(File, item["file_id"]).deleted_at is None
        assert s.get(GenerationTask, pending["task_id"]).settlement_state == "FROZEN"


def test_kept_ref_no_physical_cleanup(published, upstream, policy, tmp_path):
    client, create, login = published
    original = create()
    login(original["user_id"])
    item = client.get("/api/v1/works/" + original["work_id"]).json()["items"][0]
    assert delete(client, "works", original["work_id"], policy).status_code == 200
    from app.works.lifecycle import FileCollector

    assert (
        FileCollector(upstream[0], tmp_path, mode="mock").collect_unreferenced_file(
            item["file_id"], policy
        )
        == "protected"
    )
    with upstream[0]() as s:
        file = s.get(File, item["file_id"])
        assert (tmp_path / (file.internal_path + ".blob")).exists()
        assert s.scalars(select(FileRef).where(FileRef.file_id == file.id)).all()


def test_missing_material_reupload(published, upstream, policy):
    from tests.integration.test_task_admission import submit

    client, create, login = published
    material_work = create("image")
    login(material_work["user_id"])
    item = client.get("/api/v1/works/" + material_work["work_id"]).json()["items"][0]
    data = client.get(item["content_url"]).content
    upstream[2].materials = [{"file_id": item["file_id"], "version": item["file_version"]}]
    original = create()
    source = client.get("/api/v1/works/" + original["work_id"]).json()["source"]
    c = current_catalog_for_source(client, upstream[0].kw["bind"], original["user_id"], source)
    assert delete(client, "files", item["file_id"], policy).status_code == 200
    detail = client.get("/api/v1/works/" + original["work_id"]).json()
    assert detail["source"]["materials"][0]["action"] == "upload_again"
    body = {
        "conversation_id": original["conversation_id"],
        "agent_id": source["agent_id"],
        "input": source["input"],
        "confirmed_quote": c.quote().json(),
    }
    before = client.get("/api/v1/account").json()
    assert submit(c, body).status_code == 404
    assert client.get("/api/v1/account").json() == before
    replacement = client.post(
        "/api/v1/files",
        params={"display_name": "again.png"},
        content=data,
        headers={"Content-Type": "image/png"},
    )
    assert replacement.status_code == 201
    body = deepcopy(body)
    body["input"]["material_versions"] = [replacement.json()]
    assert submit(c, body).status_code == 409
    c.input = body["input"]
    body["confirmed_quote"] = c.quote().json()
    assert submit(c, body).status_code == 201
    assert client.get("/api/v1/works/" + original["work_id"]).json() == detail


def test_disable_revokes_preserves_task_ledger(published, upstream, policy, tmp_path):
    from fastapi import HTTPException

    from app.auth.security import HASHER
    from app.auth.service import AuthService
    from app.events.routes import read_next

    client, create, login = published
    original = create()
    pending = create(publish=False)
    admin = create(owner="admin")
    with upstream[0]() as s, s.begin():
        s.get(User, admin["user_id"]).role = "admin"
        s.get(User, original["user_id"]).password_hash = HASHER.hash("TEST_ONLY_password")
    old_token, _, old_sid = token_for(upstream[0], original["user_id"])
    with upstream[0]() as s:
        old_principal = AuthService(s).require_active_principal(old_token)
        before = [
            (r.id, r.kind, r.amount)
            for r in s.scalars(
                select(CreditLedger).where(CreditLedger.user_id == original["user_id"])
            )
        ]
        frozen = s.get(CreditAccount, original["user_id"]).frozen
    login(admin["user_id"])
    url = "/api/v1/admin/users/" + original["user_id"] + "/status"
    body = {"status": "disabled", "policy_version": policy, "expected_auth_version": 0}
    response = client.patch(url, json=body)
    assert response.status_code == 200, response.text
    assert client.patch(url, json=body).status_code == 409
    with upstream[0]() as s:
        assert s.get(AuthSession, old_sid).revoked_at is not None
        assert s.get(CreditAccount, original["user_id"]).frozen == frozen
        assert s.get(GenerationTask, pending["task_id"]).settlement_state == "FROZEN"
        assert [
            (r.id, r.kind, r.amount)
            for r in s.scalars(
                select(CreditLedger).where(CreditLedger.user_id == original["user_id"])
            )
        ] == before
        account = s.get(User, original["user_id"]).account_normalized
        with pytest.raises(HTTPException):
            AuthService(s).authenticate(account, "TEST_ONLY_password")
    with pytest.raises(HTTPException):
        read_next(upstream[0].kw["bind"], old_token, old_principal, None, 3600, None, None)
    admin_token = client.cookies.get("session")
    client.cookies.set("session", old_token)
    assert client.get("/api/v1/works").status_code == 401
    assert client.post("/api/v1/tasks", json={}).status_code == 401
    from tests.integration.test_settlement import publisher

    assert publisher(upstream, tmp_path).run(pending["task_id"]).state == "SUCCEEDED"
    with upstream[0]() as s:
        assert s.get(GenerationTask, pending["task_id"]).settlement_state == "CONSUMED"
    client.cookies.set("session", admin_token)
    response = client.patch(url, json=dict(body, status="active", expected_auth_version=1))
    assert response.status_code == 200, response.text
    with upstream[0]() as s, s.begin():
        with pytest.raises(HTTPException):
            AuthService(s).require_active_principal(old_token)
        assert AuthService(s).authenticate(account, "TEST_ONLY_password").profile.user_id
    login(original["user_id"])
    assert client.get("/api/v1/works/" + original["work_id"]).status_code == 200


@pytest.mark.parametrize("execution", [None, {"schema_version": "unknown"}])
def test_reference_only_or_unknown_policy_is_closed(published, upstream, policy, execution):
    from app.policies.models import DecisionVersionRecord

    client, create, login = published
    original = create()
    login(original["user_id"])
    version = "TEST_ONLY_" + uuid4().hex
    with upstream[0]() as s, s.begin():
        payload = deepcopy(s.get(DecisionVersionRecord, ("D-09", policy)).payload)
        payload["delete"]["execution"] = execution
        PolicyService(s).add_draft(
            DecisionVersion(
                decision_id="D-09", version=version, mode="mock", test_only=True, payload=payload
            )
        )
    assert delete(client, "works", original["work_id"], version).status_code == 403
    assert client.get("/api/v1/works/" + original["work_id"]).status_code == 200
    settings = client.app.state.settings
    client.app.state.settings = settings.model_copy(
        update={"mode": "production", "test_only": False}
    )
    assert delete(client, "works", original["work_id"], policy).status_code == 403


@pytest.fixture
def loose_file(published, upstream):
    client, create, login = published
    original = create("image")
    login(original["user_id"])
    detail = client.get("/api/v1/works/" + original["work_id"]).json()
    data = client.get(detail["items"][0]["content_url"]).content
    current_catalog_for_source(
        client, upstream[0].kw["bind"], original["user_id"], detail["source"]
    )
    uploaded = client.post(
        "/api/v1/files",
        params={"display_name": "loose.png"},
        content=data,
        headers={"Content-Type": "image/png"},
    )
    assert uploaded.status_code == 201, uploaded.text
    return client, uploaded.json(), original["user_id"]


@pytest.mark.parametrize("commit_event", ["before_commit", "after_commit"])
def test_cleanup_recovers_unlink_and_commit_uncertainty(
    loose_file, upstream, policy, tmp_path, commit_event
):
    from sqlalchemy import event
    from sqlalchemy.orm import Session

    from app.storage.models import FileCleanup
    from app.works.lifecycle import FileCollector

    client, ref, uid = loose_file
    assert delete(client, "files", ref["file_id"], policy).status_code == 200
    with upstream[0]() as s:
        file = s.get(File, ref["file_id"])
        path = tmp_path / (file.internal_path + ".blob")
        amount = file.actual_bytes
        before = s.get(StorageAccount, uid).actual_bytes
    collector = FileCollector(upstream[0], tmp_path, mode="mock")

    def fail_commit(session):
        if any(
            isinstance(row, FileCleanup) and row.state == "completed"
            for row in session.identity_map.values()
        ):
            raise RuntimeError("TEST_ONLY completion commit lost")

    event.listen(Session, commit_event, fail_commit)
    try:
        with pytest.raises(RuntimeError, match="TEST_ONLY"):
            collector.collect_unreferenced_file(ref["file_id"], policy)
    finally:
        event.remove(Session, commit_event, fail_commit)
    assert not path.exists()
    for headers in ({}, {"Range": "bytes=0-3"}):
        assert (
            client.get("/api/v1/files/" + ref["file_id"] + "/content", headers=headers).status_code
            == 404
        )
    assert delete(client, "files", ref["file_id"], policy).status_code == 200
    with upstream[0]() as s:
        assert s.get(FileCleanup, ref["file_id"]).state == (
            "pending" if commit_event == "before_commit" else "completed"
        )
        assert s.get(StorageAccount, uid).actual_bytes == (
            before if commit_event == "before_commit" else before - amount
        )
        print(
            "T17_CLEANUP_UNCERTAIN",
            {
                "file_id": ref["file_id"],
                "policy": policy,
                "commit_event": commit_event,
                "claim": s.get(FileCleanup, ref["file_id"]).state,
                "account_before": before,
                "account_now": s.get(StorageAccount, uid).actual_bytes,
                "file_bytes": amount,
                "file_state": s.get(File, ref["file_id"]).state,
                "blob_exists": path.exists(),
                "content": 404,
                "range": 404,
            },
        )
    assert collector.collect_unreferenced_file(ref["file_id"], policy) == "completed"
    assert collector.collect_unreferenced_file(ref["file_id"], policy) == "completed"
    with upstream[0]() as s:
        assert s.get(StorageAccount, uid).actual_bytes == before - amount
        assert s.get(FileCleanup, ref["file_id"]).state == "completed"
        print(
            "T17_CLEANUP_RECOVERED",
            {
                "file_id": ref["file_id"],
                "claim": "completed",
                "account_after": s.get(StorageAccount, uid).actual_bytes,
                "reclaimed": amount,
            },
        )
    assert client.get("/api/v1/files/" + ref["file_id"] + "/content").status_code == 404


def test_journal_and_retained_reference_block_cleanup(loose_file, upstream, policy, tmp_path):
    from app.works.lifecycle import FileCollector

    client, ref, uid = loose_file
    assert delete(client, "files", ref["file_id"], policy).status_code == 200
    with upstream[0]() as s:
        file = s.get(File, ref["file_id"])
        key = file.internal_path
        before = s.get(StorageAccount, uid).actual_bytes
    journal = tmp_path / (key + ".journal")
    journal.write_text('{"state":"publishing"}', encoding="utf-8")
    collector = FileCollector(upstream[0], tmp_path, mode="mock")
    assert collector.collect_unreferenced_file(ref["file_id"], policy) == "protected"
    assert (tmp_path / (key + ".blob")).exists()
    with upstream[0]() as s:
        assert s.get(StorageAccount, uid).actual_bytes == before
    journal.unlink()  # Only this test's artificial journal; simulates confirmed save recovery.
    with upstream[0]() as s, s.begin():
        s.add(
            FileRef(
                id=str(uuid4()),
                file_id=ref["file_id"],
                version=ref["version"],
                user_id=uid,
                ref_type="message",
                ref_id=str(uuid4()),
                created_at=__import__("app.ledger.service", fromlist=["now"]).now(),
            )
        )
    assert collector.collect_unreferenced_file(ref["file_id"], policy) == "protected"


def test_missing_material_is_explicit_but_foreign_is_404(published, upstream, policy):
    from tests.integration.test_task_admission import submit

    client, create, login = published
    original = create("image")
    login(original["user_id"])
    source = client.get("/api/v1/works/" + original["work_id"]).json()
    c = current_catalog_for_source(
        client, upstream[0].kw["bind"], original["user_id"], source["source"]
    )
    item = source["items"][0]
    c.input["material_versions"] = [{"file_id": item["file_id"], "version": item["file_version"]}]
    assert delete(client, "files", item["file_id"], policy).status_code == 200
    body = {
        "conversation_id": original["conversation_id"],
        "agent_id": source["source"]["agent_id"],
        "input": c.input,
        "confirmed_quote": c.quote().json(),
    }
    response = submit(c, body)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MATERIAL_UNAVAILABLE"
    body["input"]["material_versions"][0]["file_id"] = str(uuid4())
    c.input = body["input"]
    body["confirmed_quote"] = c.quote().json()
    assert submit(c, body).json()["error"]["code"] == "NOT_FOUND"


def test_manual_close_preserves_all_original_save_identities(
    upstream, ready, policy, tmp_path, auth_client, monkeypatch
):
    from app.results.models import ResultManifestRecord, ResultSaveItem
    from app.storage.models import CapacityReservation
    from app.works.lifecycle import FileCollector
    from tests.integration.test_investigations import desk as desk_fixture
    from tests.integration.test_investigations import existing_case, resolve
    from tests.integration.test_settlement import publisher

    desk = desk_fixture.__wrapped__(upstream, auth_client, tmp_path)
    root = desk[0].app.state.settings.storage_root
    task_id = ready(count=2)
    pub = publisher(upstream, root)
    commit, count = pub.persistence.store.commit, [0]

    def partial(staged):
        count[0] += 1
        if count[0] == 2:
            raise OSError("TEST_ONLY partial result")
        return commit(staged)

    monkeypatch.setattr(pub.persistence.store, "commit", partial)
    assert pub.run(task_id) is None
    case = existing_case(desk, task_id)
    assert resolve(desk, task_id, case, "manual_close").status_code == 200
    with upstream[0]() as s:
        task = s.get(GenerationTask, task_id)
        uid = task.user_id
        files = s.scalars(
            select(File).where(File.reservation_id == task.capacity_reservation_id)
        ).all()
        jobs = s.scalars(
            select(ResultSaveItem)
            .join(ResultManifestRecord, ResultManifestRecord.id == ResultSaveItem.manifest_id)
            .where(ResultManifestRecord.task_id == task_id)
        ).all()
        assert len(files) == 1 and len(jobs) == 2
        assert task.state == "MANUALLY_CLOSED" and task.settlement_state == "RELEASED"
        capacity = s.get(CapacityReservation, task.capacity_reservation_id)
        before = capacity.estimated_bytes
        assert before >= sum(job.actual_bytes for job in jobs)
        identities = [(j.file_id, j.file_version, j.internal_path) for j in jobs]
    token, csrf, _ = token_for(upstream[0], uid)
    auth_client.cookies.set("session", token)
    auth_client.cookies.set("csrf_token", csrf)
    auth_client.headers["X-CSRF-Token"] = csrf
    assert delete(auth_client, "files", files[0].id, policy).status_code == 200
    assert (
        FileCollector(upstream[0], root, mode="mock").collect_unreferenced_file(files[0].id, policy)
        == "protected"
    )
    with upstream[0]() as s:
        assert s.get(CapacityReservation, task.capacity_reservation_id).estimated_bytes == before
        assert s.get(StorageAccount, uid).reserved_bytes >= before
        assert [
            (
                s.get(ResultSaveItem, j.id).file_id,
                s.get(ResultSaveItem, j.id).file_version,
                s.get(ResultSaveItem, j.id).internal_path,
            )
            for j in jobs
        ] == identities
    assert (root / (files[0].internal_path + ".blob")).exists()


def test_delete_audit_failure_rolls_back(published, upstream, policy):
    from sqlalchemy import event

    from app.audit.models import AuditEvent

    client, create, login = published
    original = create()
    login(original["user_id"])

    def fail(mapper, connection, target):
        if target.action == "delete_work" and target.object_id == original["work_id"]:
            raise RuntimeError("TEST_ONLY audit failed")

    event.listen(AuditEvent, "before_insert", fail)
    try:
        assert delete(client, "works", original["work_id"], policy).status_code == 500
    finally:
        event.remove(AuditEvent, "before_insert", fail)
    assert client.get("/api/v1/works/" + original["work_id"]).status_code == 200


def test_physical_failure_keeps_claim_and_capacity(
    loose_file, upstream, policy, tmp_path, monkeypatch
):
    from pathlib import Path

    from app.storage.models import FileCleanup
    from app.works.lifecycle import FileCollector

    client, ref, uid = loose_file
    assert delete(client, "files", ref["file_id"], policy).status_code == 200
    with upstream[0]() as s:
        file = s.get(File, ref["file_id"])
        path = tmp_path / (file.internal_path + ".blob")
        before = s.get(StorageAccount, uid).actual_bytes
    unlink = Path.unlink

    def fail_unlink(target, **kwargs):
        if target == path:
            raise OSError("TEST_ONLY unlink failed")
        return unlink(target, **kwargs)

    collector = FileCollector(upstream[0], tmp_path, mode="mock")
    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", fail_unlink)
        with pytest.raises(OSError, match="TEST_ONLY"):
            collector.collect_unreferenced_file(ref["file_id"], policy)
    assert path.exists()
    assert client.get("/api/v1/files/" + ref["file_id"] + "/content").status_code == 404
    with upstream[0]() as s:
        assert s.get(FileCleanup, ref["file_id"]).state == "pending"
        assert s.get(StorageAccount, uid).actual_bytes == before
    assert collector.collect_unreferenced_file(ref["file_id"], policy) == "completed"


def test_status_authority_and_audit_rollback(published, upstream, policy):
    from sqlalchemy import event

    from app.audit.models import AuditEvent

    client, create, login = published
    original = create()
    sid = login(original["user_id"])
    url = "/api/v1/admin/users/" + original["user_id"] + "/status"
    body = {"status": "disabled", "policy_version": policy, "expected_auth_version": 0}
    assert client.patch(url, json=body).status_code == 403
    admin = create(owner="admin")
    with upstream[0]() as s, s.begin():
        s.get(User, admin["user_id"]).role = "admin"
    login(admin["user_id"])
    assert client.patch(url, json=dict(body, policy_version="absent")).status_code == 403

    def fail(mapper, connection, target):
        if target.action == "account_status" and target.object_id == original["user_id"]:
            raise RuntimeError("TEST_ONLY audit failure")

    event.listen(AuditEvent, "before_insert", fail)
    try:
        assert client.patch(url, json=body).status_code == 500
    finally:
        event.remove(AuditEvent, "before_insert", fail)
    with upstream[0]() as s:
        user = s.get(User, original["user_id"])
        assert (user.status, user.auth_version) == ("active", 0)
        assert s.get(AuthSession, sid).revoked_at is None


class SegmentedFileStream:
    """Real ASGI app with a slow send boundary; no DB/auth/file stand-ins."""

    def __init__(self, app, path, token, range_header):
        import asyncio

        self.app, self.path, self.token = app, path, token
        self.range_header = range_header
        self.output, self.input = asyncio.Queue(), asyncio.Queue()
        self.release = asyncio.Event()
        self.first = True

    async def send(self, message):
        await self.output.put(message)
        if self.first and message.get("body"):
            self.first = False
            await self.release.wait()

    async def __aenter__(self):
        import asyncio

        headers = {"host": "testserver", "cookie": "session=" + self.token}
        if self.range_header:
            headers["range"] = self.range_header
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": self.path,
            "raw_path": self.path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
            "client": ("127.0.0.1", 32101),
            "server": ("testserver", 443),
        }
        await self.input.put({"type": "http.request", "body": b"", "more_body": False})
        self.runner = asyncio.create_task(self.app(scope, self.input.get, self.send))
        response = await asyncio.wait_for(self.output.get(), 5)
        self.status, self.headers = response["status"], dict(response["headers"])
        return self

    async def chunk(self):
        import asyncio

        response = await asyncio.wait_for(self.output.get(), 5)
        return response.get("body", b""), response.get("more_body", False)

    async def __aexit__(self, *_):
        import asyncio

        self.release.set()
        await self.input.put({"type": "http.disconnect"})
        await asyncio.wait_for(self.runner, 5)


@pytest.fixture
def stream_work(published, upstream, ready, tmp_path, monkeypatch):
    """Real HTTP simulator -> original persistence -> published PNG over four blocks."""
    import io
    import random

    from PIL import Image

    from app.agents import mock as mock_adapter
    from app.agents.mock_server import MEDIA_FIXTURES
    from app.works.models import Work
    from tests.integration.test_settlement import publisher

    output = io.BytesIO()
    pixels = random.Random(17).randbytes(320 * 320 * 3)
    Image.frombytes("RGB", (320, 320), pixels).save(output, "PNG")
    data = output.getvalue()
    monkeypatch.setitem(MEDIA_FIXTURES, "image", ("image/png", data))
    # The TEST_ONLY adapter normally caps its base64 JSON response at 64 KiB.
    # Raise only this test transport limit, keeping real HTTP/validation/persistence.
    monkeypatch.setattr(mock_adapter, "MAX_BODY", 1000000)
    pending = ready()

    def policy_limits(payload):
        payload["D-10"]["result_download"].update(max_download_bytes=600000, max_total_bytes=600000)

    task_id = ready(kind="image", policies=policy_limits)
    with upstream[0]() as s, s.begin():
        uid = s.get(GenerationTask, task_id).user_id
        # Only this fixture's newly created account, not a historical fixture/policy.
        s.get(StorageAccount, uid).quota_bytes = 1000000
    assert publisher(upstream, tmp_path).run(task_id).state == "SUCCEEDED"
    client, _, login = published
    login(uid)
    with upstream[0]() as s:
        work_id = s.scalar(select(Work.id).where(Work.task_id == task_id))
    item = client.get("/api/v1/works/" + work_id).json()["items"][0]
    assert client.get(item["content_url"]).content == data
    return client, uid, work_id, item, data, (task_id, pending), login


def download_facts(factory, uid, task_ids):
    from app.storage.models import CapacityReservation

    with factory() as s:
        account = s.get(CreditAccount, uid)
        storage = s.get(StorageAccount, uid)
        return {
            "credit": (account.available, account.frozen, account.consumed, account.credited_total),
            "capacity": (storage.actual_bytes, storage.reserved_bytes),
            "tasks": [
                (id, s.get(GenerationTask, id).state, s.get(GenerationTask, id).settlement_state)
                for id in task_ids
            ],
            "ledger": sorted(
                (r.id, r.kind, r.amount)
                for r in s.scalars(select(CreditLedger).where(CreditLedger.user_id == uid))
            ),
            "reservations": sorted(
                (r.id, r.state, r.estimated_bytes, r.actual_bytes)
                for r in s.scalars(
                    select(CapacityReservation).where(CapacityReservation.user_id == uid)
                )
            ),
        }


@pytest.mark.parametrize("action", ["disable", "file_delete", "work_delete", "logout"])
@pytest.mark.parametrize("range_header", [None, "bytes=37-200036"])
def test_existing_download_reauthorizes_each_block(
    stream_work, upstream, policy, action, range_header, monkeypatch
):
    import asyncio

    from app.storage.local_store import LocalStore

    client, uid, work_id, item, data, tasks, login = stream_work
    if action == "disable":
        with upstream[0]() as s, s.begin():
            s.get(User, uid).role = "admin"
        login(uid)
    token = client.cookies.get("session")
    before = download_facts(upstream[0], uid, tasks)
    assert before["credit"][1] == 30
    opened = []
    read = LocalStore.read

    def track(store, key):
        handle = read(store, key)
        opened.append(handle)
        return handle

    monkeypatch.setattr(LocalStore, "read", track)

    def revoke():
        if action == "disable":
            return client.patch(
                "/api/v1/admin/users/" + uid + "/status",
                json={"status": "disabled", "policy_version": policy, "expected_auth_version": 0},
            )
        if action == "logout":
            return client.post("/api/v1/auth/logout")
        return delete(
            client,
            "files" if action == "file_delete" else "works",
            item["file_id"] if action == "file_delete" else work_id,
            policy,
        )

    async def scenario():
        async with SegmentedFileStream(
            client.app, item["content_url"], token, range_header
        ) as stream:
            assert stream.status == (206 if range_header else 200)
            expected = data[37:200037] if range_header else data
            assert int(stream.headers[b"content-length"]) == len(expected)
            first, more = await stream.chunk()
            assert more and first == expected[:65536]
            response = await asyncio.wait_for(asyncio.to_thread(revoke), 5)
            assert response.status_code == (204 if action == "logout" else 200), response.text
            stream.release.set()
            after = b""
            while more:
                chunk, more = await stream.chunk()
                after += chunk
            # Middleware can already hold one authorized chunk in its send buffer.
            assert len(after) <= 65536, (action, range_header, len(after))
            assert len(first) + len(after) < len(expected)
            assert first + after == expected[: len(first) + len(after)]
            return len(first), len(after)

    first, after = asyncio.run(scenario())
    assert opened and all(handle.closed for handle in opened)
    assert download_facts(upstream[0], uid, tasks) == before
    denied = client.get(item["content_url"], headers={"Range": "bytes=0-3"})
    assert denied.status_code == (401 if action in ("disable", "logout") else 404)
    print(
        "T17_FIX1_STREAM",
        {
            "action": action,
            "range": range_header,
            "user": uid,
            "file": item["file_id"],
            "work": work_id,
            "tasks": tasks,
            "sent_first": first,
            "already_buffered_after": after,
            "facts_unchanged": before,
        },
    )


@pytest.mark.parametrize("range_header", [None, "bytes=37-200036"])
def test_existing_download_stops_on_database_failure(
    stream_work, upstream, range_header, monkeypatch
):
    import asyncio

    from sqlalchemy import event
    from sqlalchemy.exc import OperationalError

    from app.storage.local_store import LocalStore

    client, uid, _, item, data, tasks, _ = stream_work
    before = download_facts(upstream[0], uid, tasks)
    opened = []
    original_read = LocalStore.read

    def track(store, key):
        handle = original_read(store, key)
        opened.append(handle)
        return handle

    monkeypatch.setattr(LocalStore, "read", track)
    failures = []

    def unavailable(conn, cursor, statement, parameters, context, executemany):
        failures.append(True)
        raise OperationalError("TEST_ONLY database unavailable", {}, Exception("TEST_ONLY"))

    async def scenario():
        async with SegmentedFileStream(
            client.app, item["content_url"], client.cookies.get("session"), range_header
        ) as stream:
            assert stream.status == (206 if range_header else 200)
            first, more = await stream.chunk()
            assert more and len(first) == 65536
            event.listen(client.app.state.engine, "before_cursor_execute", unavailable)
            try:
                stream.release.set()
                after = b""
                while more:
                    chunk, more = await stream.chunk()
                    after += chunk
                assert len(after) <= 65536, len(after)
                assert failures, "The next block did not attempt a database authorization check"
            finally:
                event.remove(client.app.state.engine, "before_cursor_execute", unavailable)

    asyncio.run(scenario())
    assert opened and all(handle.closed for handle in opened)
    assert download_facts(upstream[0], uid, tasks) == before
    assert client.get(item["content_url"]).content == data
