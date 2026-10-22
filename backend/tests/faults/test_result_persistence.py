"""T11 real HTTP/MySQL/disk recovery. No manually forged durable deliveries."""

import importlib.util
from uuid import uuid4

import pytest
from sqlalchemy import event, select

from app.catalog.schemas import content_digest
from app.policies.models import DecisionVersionRecord
from app.policies.schemas import DecisionVersion
from app.tasks.models import GenerationTask, TaskSnapshot
from tests.faults.test_upstream_recovery import calls, facts, submit
from tests.faults.test_upstream_recovery import upstream as upstream_fixture

upstream = upstream_fixture


def persistence(runtime, root):
    assert importlib.util.find_spec("app.results"), "Original result persistence is missing"
    from app.results.persistence import ResultPersistence
    from app.storage.local_store import LocalStore

    return ResultPersistence(runtime[0], runtime[1], LocalStore(root))


@pytest.fixture
def ready(upstream):
    def create(scenario="normal", count=1, kind="copy", mutate=None, policies=None):
        def stamp(mapper, connection, target):
            spec = dict(target.spec_snapshot, delivery_kind="single" if count == 1 else "multiple")
            if count == 2:
                spec["parameter_schema"] = dict(
                    fields={
                        "test_only_result_count": {
                            "kind": "integer",
                            "required": True,
                            "choices": [2],
                        }
                    },
                    combinations=[{"test_only_result_count": 2}],
                )
                target.input_snapshot = dict(
                    target.input_snapshot, parameters={"test_only_result_count": 2}
                )
            target.spec_snapshot = spec
            rule = dict(
                protocol_version="mock-v1-TEST_ONLY",
                spec_version=spec["version"],
                spec_digest=content_digest(spec),
                expected_item_keys=[f"original-{i + 1}" for i in range(count)],
                media_type={"copy": "text/plain", "image": "image/png", "video": "video/mp4"}[kind],
            )
            payloads = {
                "D-01": {"result_specs": {spec["spec_id"]: rule}},
                "D-04": {"result_specs": {spec["spec_id"]: dict(rule, delivery="complete_only")}},
                "D-10": {
                    "result_download": dict(
                        allowed_download_sources=["TEST_ONLY:bound-mock"],
                        max_download_bytes=10000,
                        max_total_bytes=20000,
                        download_timeout_seconds=10,
                        max_redirects=2,
                    )
                },
            }
            if policies:
                policies(payloads)
            versions = dict(target.policy_versions)
            for key, payload in payloads.items():
                version = "TEST_ONLY_T11_" + uuid4().hex
                row = DecisionVersion(
                    decision_id=key, version=version, mode="mock", test_only=True, payload=payload
                )
                connection.execute(
                    DecisionVersionRecord.__table__.insert().values(**row.model_dump(mode="json"))
                )
                versions[key] = version
            target.policy_versions = versions

        event.listen(TaskSnapshot, "before_insert", stamp)
        try:
            task = upstream[2](scenario, kind)
        finally:
            event.remove(TaskSnapshot, "before_insert", stamp)
        submit(upstream, task)
        result = upstream[3].simulator.result
        if mutate:
            upstream[3].simulator.result = lambda agent, row: mutate(result(agent, row))
        try:
            upstream[1].poll_original_task(task)
        finally:
            upstream[3].simulator.result = result
        return task

    return create


def test_partial_temporary_not_complete(upstream, ready, tmp_path):
    task = ready("partial")
    service = persistence(upstream, tmp_path)
    assert service.save_original(task) is None
    assert list(tmp_path.rglob("*.blob")) == []
    assert calls(upstream, task)["submit"] == 1
    assert facts(upstream[0], task)[-1] == "frozen"


def test_manifest_reserves_declared_bytes_before_retrieval(upstream, ready, tmp_path, monkeypatch):
    from app.results.models import ResultSaveItem
    from app.storage.models import CapacityReservation, StorageAccount, StoragePool

    task_id = ready(count=2)
    service = persistence(upstream, tmp_path)
    # Reproduce an estimate smaller than the returned complete manifest.
    with upstream[0]() as session, session.begin():
        task = session.get(GenerationTask, task_id)
        reservation = session.get(CapacityReservation, task.capacity_reservation_id)
        difference = reservation.estimated_bytes - 1
        session.get(StoragePool, reservation.pool_id).reserved_bytes -= difference
        session.get(StorageAccount, task.user_id).reserved_bytes -= difference
        reservation.estimated_bytes = 1

    def before_retrieval(task_id, manifest_id, *, lease):
        with upstream[0]() as session:
            task = session.get(GenerationTask, task_id)
            reservation = session.get(CapacityReservation, task.capacity_reservation_id)
            required = sum(session.scalars(select(ResultSaveItem.actual_bytes).where(
                ResultSaveItem.manifest_id == manifest_id,
            )))
            assert required > 1
            assert reservation.estimated_bytes >= required
        return None

    monkeypatch.setattr(service, "persist_original_result", before_retrieval)
    assert service.save_original(task_id) is None
    assert calls(upstream, task_id)["retrieve_original"] == 0


def test_disk_complete_db_commit_failure(upstream, ready, tmp_path, monkeypatch):
    task = ready()
    service = persistence(upstream, tmp_path)
    original = facts(upstream[0], task)
    from sqlalchemy.orm import Session

    from app.storage.models import File

    def mark(session, *_):
        if any(isinstance(x, File) for x in session.new):
            session.info["test_save_file"] = True

    def fail(session):
        if session.info.get("test_save_file") or any(isinstance(x, File) for x in session.new):
            raise RuntimeError("TEST_ONLY record commit failed after rename")

    event.listen(Session, "before_flush", mark)
    event.listen(Session, "before_commit", fail)
    try:
        with pytest.raises(RuntimeError, match="record commit failed"):
            service.save_original(task)
    finally:
        event.remove(Session, "before_commit", fail)
        event.remove(Session, "before_flush", mark)
    blobs = list(tmp_path.rglob("*.blob"))
    assert len(blobs) == 1
    assert len(list(tmp_path.rglob("*.journal"))) == 1
    before = calls(upstream, task)
    with upstream[0]() as s:
        assert not s.scalars(
            select(File).where(File.user_id == s.get(GenerationTask, task).user_id)
        ).all()
    delivery = persistence(upstream, tmp_path).save_original(task)
    assert delivery and len(delivery.items) == 1
    assert delivery.items[0].sha256
    assert blobs == list(tmp_path.rglob("*.blob"))
    assert calls(upstream, task) == before
    assert facts(upstream[0], task) == original
    print(
        "T11_COMMIT_RECOVERED",
        task,
        delivery.manifest_id,
        delivery.items[0].file_id,
        calls(upstream, task),
    )


def test_save_failure_expired_link_never_regenerates(upstream, ready, tmp_path):
    task = ready("expired_link")
    service = persistence(upstream, tmp_path)
    assert service.save_original(task) is None
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        assert row.state == "INVESTIGATING"
        assert row.settlement_state == "FROZEN"
    assert calls(upstream, task)["submit"] == 1
    assert calls(upstream, task)["retrieve_original"] == 1


def test_complete_multi_result_uses_one_reserved_capacity(upstream, ready, tmp_path):
    task = ready(count=2)
    with upstream[0]() as s:
        assert s.get(GenerationTask, task).state == "SAVING", "Fixed multi-result rejected"
    service = persistence(upstream, tmp_path)
    delivery = service.save_original(task)
    assert delivery and len(delivery.items) == 2
    from app.storage.models import CapacityReservation, File, FileRef

    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        capacity = s.get(CapacityReservation, row.capacity_reservation_id)
        files = s.scalars(select(File).where(File.reservation_id == capacity.id)).all()
        refs = s.scalars(select(FileRef).where(FileRef.ref_id == task)).all()
        assert len(files) == len(refs) == 2
        assert capacity.state == "reserved" and capacity.actual_bytes == 0
        assert row.state == "SAVING" and row.settlement_state == "FROZEN"
        assert sum(f.actual_bytes for f in files) == delivery.total_bytes
        print(
            "T11_DURABLE", task, delivery.manifest_id, [f.id for f in files], calls(upstream, task)
        )
    assert calls(upstream, task)["submit"] == 1
    assert service.save_original(task) == delivery


def test_staged_file_is_not_delivery_and_retry_only_retrieves_original(
    upstream, ready, tmp_path, monkeypatch
):
    task = ready()
    service = persistence(upstream, tmp_path)
    commit = service.store.commit

    def disk_failure(staged):
        raise OSError("TEST_ONLY disk rename failure")

    monkeypatch.setattr(service.store, "commit", disk_failure)
    assert service.save_original(task) is None
    assert len(list(tmp_path.rglob("*.part"))) == 1
    assert not list(tmp_path.rglob("*.blob"))
    with upstream[0]() as s:
        assert s.get(GenerationTask, task).state == "SAVE_RECOVERY"
    monkeypatch.setattr(service.store, "commit", commit)
    assert service.save_original(task)
    assert calls(upstream, task)["submit"] == 1
    assert calls(upstream, task)["retrieve_original"] == 2


def test_ambiguous_committed_save_preserves_journal_and_identity(upstream, ready, tmp_path):
    from sqlalchemy.orm import Session

    from app.storage.models import File

    task = ready()
    service = persistence(upstream, tmp_path)

    def mark(session, *_):
        if any(isinstance(x, File) for x in session.new):
            session.info["test_file_commit"] = True

    def uncertain(session):
        if session.info.get("test_file_commit"):
            raise RuntimeError("TEST_ONLY commit reply lost")

    event.listen(Session, "before_flush", mark)
    event.listen(Session, "after_commit", uncertain)
    try:
        with pytest.raises(RuntimeError, match="commit reply lost"):
            service.save_original(task)
    finally:
        event.remove(Session, "after_commit", uncertain)
        event.remove(Session, "before_flush", mark)
    assert len(list(tmp_path.rglob("*.blob"))) == 1
    assert len(list(tmp_path.rglob("*.journal"))) == 1
    before = calls(upstream, task)
    delivery = persistence(upstream, tmp_path).save_original(task)
    assert len(delivery.items) == 1
    assert calls(upstream, task) == before
    assert not list(tmp_path.rglob("*.journal"))


def test_expired_worker_cannot_record_delivery_successor_recovers_blob(
    upstream, ready, tmp_path, monkeypatch
):
    from sqlalchemy import text, update

    from app.storage.models import File
    from app.tasks.state_machine import TransitionError

    task = ready()
    service = persistence(upstream, tmp_path)
    commit = service.store.commit

    def expire(staged):
        key = commit(staged)
        with upstream[0]() as s, s.begin():
            s.execute(
                update(GenerationTask)
                .where(GenerationTask.id == task)
                .values(lease_expires_at=text("UTC_TIMESTAMP(6) - INTERVAL 1 SECOND"))
            )
        return key

    monkeypatch.setattr(service.store, "commit", expire)
    with pytest.raises(TransitionError, match="LEASE_LOST"):
        service.save_original(task)
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        assert not s.scalars(select(File).where(File.user_id == row.user_id)).all()
    before = calls(upstream, task)
    assert persistence(upstream, tmp_path).save_original(task)
    assert calls(upstream, task) == before


@pytest.mark.parametrize("kind", ["image", "video"])
def test_complete_media_decodes_outside_database_locks(
    upstream, ready, tmp_path, monkeypatch, kind
):
    task = ready(kind=kind)
    service = persistence(upstream, tmp_path)
    validate = service._validate
    seen = []

    def unlocked(path, job):
        with upstream[0]() as s, s.begin():
            assert s.scalar(
                select(GenerationTask).where(GenerationTask.id == task).with_for_update(nowait=True)
            )
            seen.append(job.media_type)
        return validate(path, job)

    monkeypatch.setattr(service, "_validate", unlocked)
    delivery = service.save_original(task)
    assert delivery and len(delivery.items) == 1
    assert seen == [{"image": "image/png", "video": "video/mp4"}[kind]]
    assert calls(upstream, task)["submit"] == 1


def test_actual_composed_worker_saves_original(upstream, ready, tmp_path, redis_namespace):
    from app.results.models import ResultDeliveryRecord, ResultManifestRecord
    from app.storage.local_store import LocalStore
    from worker.main import compose_worker

    task = ready(count=2)
    redis, prefix = redis_namespace
    worker = compose_worker(
        upstream[0],
        redis,
        prefix + "result-worker",
        "workers",
        "t11",
        registry=upstream[1].registry,
        task_ids=[task],
        store=LocalStore(tmp_path),
    )
    worker.tick()
    with upstream[0]() as s:
        manifest = s.scalar(
            select(ResultManifestRecord).where(ResultManifestRecord.task_id == task)
        )
        assert manifest and s.get(ResultDeliveryRecord, manifest.id)
        assert s.get(GenerationTask, task).state == "SUCCEEDED"
        assert s.get(GenerationTask, task).settlement_state == "CONSUMED"
        delivery = persistence(upstream, tmp_path).verified_delivery(
            s, s.get(GenerationTask, task), manifest.id
        )
        assert delivery and len(delivery.items) == 2
        assert all(len(item.sha256) == 64 for item in delivery.items)
        from app.ledger.models import CreditLedger

        settlements = s.scalars(
            select(CreditLedger).where(CreditLedger.task_id == task, CreditLedger.kind == "consume")
        ).all()
        assert len(settlements) == 1 and settlements[0].amount == 30
    assert calls(upstream, task)["submit"] == 1


def test_tampered_blob_is_preserved_and_never_delivered(upstream, ready, tmp_path):
    task = ready()
    service = persistence(upstream, tmp_path)
    assert service.save_original(task)
    blob = next(tmp_path.rglob("*.blob"))
    blob.write_bytes(b"TEST_ONLY corruption")
    before = calls(upstream, task)
    assert service.save_original(task) is None
    assert blob.read_bytes() == b"TEST_ONLY corruption"
    assert calls(upstream, task) == before
    with upstream[0]() as s:
        assert s.get(GenerationTask, task).state == "SAVE_RECOVERY"


def test_persisted_manifest_recovers_even_when_later_query_unavailable(
    upstream, ready, tmp_path, redis_namespace
):
    from app.results.models import ResultDeliveryRecord, ResultManifestRecord
    from app.storage.local_store import LocalStore
    from worker.main import compose_worker

    task = ready("expired_link")
    assert persistence(upstream, tmp_path).save_original(task) is None
    with upstream[0]() as s:
        row = s.get(GenerationTask, task)
        upstream[3].simulator.records["copy", row.external_submission_id]["scenario"] = (
            "query_unavailable"
        )
    before = calls(upstream, task)
    redis, prefix = redis_namespace
    worker = compose_worker(
        upstream[0],
        redis,
        prefix + "recover",
        "workers",
        "t11",
        registry=upstream[1].registry,
        task_ids=[task],
        store=LocalStore(tmp_path),
    )
    worker.tick()
    with upstream[0]() as s:
        manifest = s.scalar(
            select(ResultManifestRecord).where(ResultManifestRecord.task_id == task)
        )
        assert manifest and s.get(ResultDeliveryRecord, manifest.id), (
            "Durable manifest recovery lost to query failure"
        )
    assert calls(upstream, task)["query_id"] == before["query_id"]
    assert calls(upstream, task)["submit"] == 1


def test_existing_blob_guard_blocks_second_writer(upstream, ready, tmp_path):
    from app.results.models import ResultSaveItem

    task = ready()
    service = persistence(upstream, tmp_path)
    lease = service.leases.claim_task(task, "guard-owner")
    try:
        mid = service.prepare_manifest(task, upstream[1].original_result(task), lease=lease)
    finally:
        service.leases.release(lease)
    with upstream[0]() as s:
        job = s.scalar(select(ResultSaveItem).where(ResultSaveItem.manifest_id == mid))
    with service.store.result_guard(job.internal_path):
        assert service.save_original(task) is None
        assert not list(tmp_path.rglob("*.part"))
        assert not list(tmp_path.rglob("*.blob"))
    assert service.save_original(task)
    assert calls(upstream, task)["retrieve_original"] == 1


@pytest.mark.parametrize(
    "defect", ["missing", "duplicate", "foreign_locator", "count", "unknown_spec", "missing_d04"]
)
def test_fixed_multi_protocol_rejects_bad_manifest(upstream, ready, tmp_path, defect):
    def mutate(manifest):
        if defect == "missing":
            manifest["items"] = manifest["items"][:1]
            manifest["complete"] = False
        elif defect == "duplicate":
            manifest["items"][1] = dict(manifest["items"][0])
        elif defect == "foreign_locator":
            manifest["items"][1]["locator"] = "/v1/copy/results/other-task/original-2"
        elif defect == "count":
            manifest["expected_items"] = 3
        return manifest

    def policies(payload):
        if defect == "unknown_spec":
            payload["D-01"]["result_specs"] = {}
        if defect == "missing_d04":
            payload["D-04"]["result_specs"] = {}

    task = ready(count=2, mutate=mutate, policies=policies)
    assert upstream[1].original_result(task) is None
    assert persistence(upstream, tmp_path).save_original(task) is None
    assert not list(tmp_path.rglob("*.blob"))
    assert calls(upstream, task)["submit"] == 1
    assert facts(upstream[0], task)[-1] == "frozen"


@pytest.mark.parametrize("defect", ["hash", "bytes", "mime", "partial", "identity"])
def test_retrieval_must_match_the_fixed_original(upstream, ready, tmp_path, monkeypatch, defect):
    from app.agents.mock import MockAgentAdapter

    task = ready()
    original = MockAgentAdapter.retrieve_original

    def corrupt(self, locator):
        source = original(self, locator)
        updates = {
            "hash": {"content": b"x" * source.byte_length},
            "bytes": {"content": source.content + b"x"},
            "mime": {"media_type": "image/png"},
            "partial": {"complete": False},
            "identity": {"locator": "/v1/copy/results/foreign"},
        }
        return source.model_copy(update=updates[defect])

    monkeypatch.setattr(MockAgentAdapter, "retrieve_original", corrupt)
    assert persistence(upstream, tmp_path).save_original(task) is None
    assert not list(tmp_path.rglob("*.blob"))
    assert calls(upstream, task)["submit"] == 1
    with upstream[0]() as s:
        assert s.get(GenerationTask, task).state == "SAVE_RECOVERY"


def test_no_policy_version_fallback(upstream, ready, tmp_path):
    from app.tasks.state_machine import TransitionError

    task = ready(policies=lambda payload: payload["D-01"].update(result_specs={}))
    with pytest.raises(TransitionError, match="RESULT_POLICY_UNAVAILABLE"):
        persistence(upstream, tmp_path).save_original(task)
    assert calls(upstream, task)["retrieve_original"] == 0
    assert facts(upstream[0], task)[-1] == "frozen"
