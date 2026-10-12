"""T20a focused public-copy isolation with explicit synthetic database fixtures.

The positive branch fixture is not a real agent/customer case and never leaves TEST_ONLY DB.
"""

import asyncio
from hashlib import sha256
from io import BytesIO
from uuid import uuid4

import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.agents.models import AgentEvent
from app.catalog.models import AgentRecord
from app.conversations.models import Message
from app.ledger.service import now
from app.results.models import ResultManifestRecord
from app.site.models import PublicCase, PublicCaseCopy
from app.storage.local_store import LocalStore
from app.storage.models import File
from app.tasks.models import TaskSnapshot
from app.works.models import Work, WorkItem
from tests.integration.test_admin_access import identity, login
from tests.integration.test_site_content import body, policies


@pytest.fixture
def case_desk(auth_client, mysql_engine, ledger_task):
    store = LocalStore(auth_client.app.state.settings.storage_root)
    payload = b"TEST_ONLY synthetic fixture; not a real public customer example"

    def create(mock=False, approved=True, execution=True):
        with Session(mysql_engine) as session, session.begin():
            admin, owner = identity(session), identity(session, "user")

            def provenance(mapper, connection, target):
                target.agent_snapshot = {
                    **target.agent_snapshot,
                    "mode": "mock" if mock else "production",
                    "test_only": mock,
                }

            event.listen(TaskSnapshot, "before_insert", provenance)
            try:
                task = ledger_task(session, owner["id"], str(uuid4()))
            finally:
                event.remove(TaskSnapshot, "before_insert", provenance)
            task.state = "SUCCEEDED"
            session.add(
                AgentRecord(
                    agent_id=task.agent_id,
                    version=task.agent_version,
                    snapshot=session.get(TaskSnapshot, task.id).agent_snapshot,
                    endpoint="TEST_ONLY_NO_REAL_AGENT",
                )
            )
            receipt = AgentEvent(
                id=str(uuid4()),
                task_id=task.id,
                agent_id=task.agent_id,
                agent_version=task.agent_version,
                source="poll",
                event_id=uuid4().hex,
                raw_digest="a" * 64,
                semantic_digest="b" * 64,
                sequence=2,
                payload={},
                created_at=now(),
            )
            session.add(receipt)
            session.flush()
            manifest = ResultManifestRecord(
                id=str(uuid4()),
                task_id=task.id,
                receipt_id=receipt.id,
                identity={},
                manifest={},
                policy_versions={},
                created_at=now(),
            )
            message = Message(
                id=str(uuid4()),
                user_id=owner["id"],
                conversation_id=task.conversation_id,
                task_id=task.id,
                kind="final",
                role="assistant",
                content={"TEST_ONLY": "fixture"},
                created_at=now(),
            )
            session.add_all([manifest, message])
            session.flush()
            work = Work(
                id=str(uuid4()),
                user_id=owner["id"],
                task_id=task.id,
                conversation_id=task.conversation_id,
                manifest_id=manifest.id,
                message_id=message.id,
                created_at=now(),
            )
            session.add(work)
            session.flush()
            staged = asyncio.run(store.stage(BytesIO(payload), owner["id"], len(payload)))
            store.commit(staged)
            store.acknowledge(staged)
            file = File(
                id=str(uuid4()),
                version=str(uuid4()),
                user_id=owner["id"],
                internal_path=staged.key,
                actual_mime="text/plain",
                actual_bytes=len(payload),
                sha256=sha256(payload).hexdigest(),
                display_name="TEST_ONLY private source",
                state="durable",
                created_at=now(),
                reservation_id=task.capacity_reservation_id,
            )
            session.add(file)
            session.flush()
            session.add(
                WorkItem(
                    id=str(uuid4()),
                    work_id=work.id,
                    user_id=owner["id"],
                    item_key="one",
                    file_id=file.id,
                    file_version=file.version,
                )
            )
            rule = dict(
                source_work_ref=work.id,
                owner_ref=owner["id"],
                authorization_ref="TEST_ONLY_separate_public_consent",
                withdrawal_ref="TEST_ONLY_withdraw",
                public_copy_cleanup_ref="TEST_ONLY_delete_copy",
                is_mock=False,
            )
            if execution:
                rule["execution"] = dict(
                    schema_version="public-copy-v1",
                    storage="persistent_disk",
                    withdrawal="deny_then_delete_copy",
                    max_total_bytes=1024,
                )
            version = policies(
                session, admin, body(0)["content"], confirmed=approved, cases={work.id: rule}
            )
            dto = dict(
                work_id=work.id,
                authorization_ref=rule["authorization_ref"],
                policy_version=version,
                policy_versions={"D-07": version, "D-12": version},
            )
            result = admin, owner, dto, file.id, file.internal_path
        login(auth_client, admin)
        return result

    return auth_client, create, store, payload


@pytest.mark.parametrize(
    "mock,approved,execution", [(True, True, True), (False, False, True), (False, True, False)]
)
def test_mock_unapproved_or_unresolved_cases_cannot_publish(
    case_desk, mysql_engine, mock, approved, execution
):
    client, create, _, _ = case_desk
    admin, _, dto, _, _ = create(mock, approved, execution)
    result = client.post("/api/v1/admin/site/cases", json=dto)
    assert result.status_code == 403, result.text
    with Session(mysql_engine) as session:
        assert session.get(PublicCase, dto["work_id"]) is None
    assert dto["work_id"] not in str(client.get("/api/v1/site/cases").json())


def test_public_copy_private_isolation_and_withdraw_retry(case_desk, mysql_engine, monkeypatch):
    client, create, store, payload = case_desk
    admin, owner, dto, file_id, source_path = create()
    wrong = {**dto, "authorization_ref": "ordinary-admin-access-is-not-public-consent"}
    assert client.post("/api/v1/admin/site/cases", json=wrong).status_code == 403
    response = client.post("/api/v1/admin/site/cases", json=dto)
    assert response.status_code == 200, response.text
    assert client.get(f"/api/v1/files/{file_id}/content").status_code == 404
    listing = client.get("/api/v1/site/cases").json()
    public = next(row for row in listing if row["id"] == dto["work_id"])
    assert (
        source_path not in str(listing)
        and file_id not in str(listing)
        and owner["id"] not in str(listing)
    )
    url = public["items"][0]["url"]
    client.cookies.clear()
    assert client.get(url).content == payload
    with Session(mysql_engine) as session:
        copy_path = session.scalar(
            select(PublicCaseCopy).where(PublicCaseCopy.case_id == dto["work_id"])
        ).internal_path
        assert copy_path != source_path
        assert session.get(File, file_id).user_id == owner["id"]
    login(client, admin)
    original = LocalStore.discard
    monkeypatch.setattr(
        LocalStore,
        "discard",
        lambda *args: (_ for _ in ()).throw(OSError("TEST_ONLY cleanup unavailable")),
    )
    path = f"/api/v1/admin/site/cases/{dto['work_id']}/withdraw"
    withdrawn = client.post(path, json={"policy_version": dto["policy_version"]})
    assert withdrawn.status_code == 200 and withdrawn.json()["state"] == "cleanup_pending"
    assert client.get(url).status_code == 404
    assert store.result_path(copy_path).exists() and store.result_path(source_path).exists()
    monkeypatch.setattr(LocalStore, "discard", original)
    retry = client.post(path, json={"policy_version": dto["policy_version"]})
    assert retry.status_code == 200 and retry.json()["state"] == "withdrawn"
    assert not store.result_path(copy_path).exists()
    assert store.result_path(source_path).read_bytes() == payload
    assert client.get(url).status_code == 404
    with Session(mysql_engine) as session:
        assert session.get(File, file_id).deleted_at is None
        assert session.get(Work, dto["work_id"]).user_id == owner["id"]
