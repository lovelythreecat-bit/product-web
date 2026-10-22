"""Actual HTTP/SQL/disk/ledger pipeline against a controlled text API, no model calls."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.agents.registry import AgentRegistry
from app.agents.text import DOWNLOAD_SOURCE, PROTOCOL, TextAgentProfile
from app.agents.upstream import UpstreamService
from app.auth.models import User
from app.catalog.schemas import content_digest
from app.dispatch.consumer import LeaseManager
from app.ledger.models import CreditAccount, CreditLedger
from app.policies.models import DecisionVersionRecord
from app.policies.schemas import DecisionVersion
from app.results.persistence import ResultPersistence
from app.results.publisher import ResultPublisher
from app.storage.local_store import LocalStore
from app.tasks.models import GenerationTask
from app.works.models import Work
from tests.t12_fixtures import upstream as upstream_fixture

upstream = upstream_fixture


@pytest.fixture(params=["legacy", "database"])
def text_runtime(upstream, tmp_path, request):
    state = {"posts": [], "records": {}, "scenario": "success", "gets": [], "release": Event()}
    config_id = str(uuid4())

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, body):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            assert self.path == "/v1/copy/generate"
            assert self.headers["Authorization"] == "Bearer TEST_ONLY_service_key"
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["posts"].append((self.headers["Idempotency-Key"], body))
            if state["scenario"] == "limited":
                self.reply(429, {"record_id": None, "error": {"code": "concurrency_limit"}})
                return
            if state["scenario"] == "slow":
                assert state["release"].wait(timeout=3), "Lease was not renewed during generation"
            record_id = str(uuid4())
            state["records"][record_id] = dict(
                id=record_id,
                model_config_id=config_id,
                content_expired=False,
                status="failed" if state["scenario"] == "failure" else "succeeded",
                result_json={"text": "测试商品的完整文案",
                             "warnings": state.get("warnings", ["材质信息尚待核实"])},
                error_code="model_output",
            )
            if state["scenario"] == "lost_reply":
                self.connection.close()
                return
            if state["scenario"] == "failure":
                self.reply(502, {"record_id": record_id, "error": {"code": "model_output"}})
                return
            self.reply(200, {"record_id": record_id, "result": {
                "text": "测试商品的完整文案",
                "warnings": state.get("warnings", ["材质信息尚待核实"]),
            }})

        def do_GET(self):
            state["gets"].append(self.path)
            record_id = self.path.rsplit("/", 1)[-1]
            self.reply(200, state["records"][record_id])

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    profile = TextAgentProfile(
        base_url=f"http://127.0.0.1:{server.server_port}",
        service_key="TEST_ONLY_service_key",
        model_config_id=config_id,
    )
    factory = upstream[0]
    registry = AgentRegistry(mode="mock", test_only=True, text_profiles={"text-v1": profile})
    profile_ref = "text-v1"
    if request.param == "database":
        from cryptography.fernet import Fernet

        from app.admin.models import TextServiceConnection
        from app.agents.service_connection import (
            TextServiceConnectionUpdate,
            update_service_connection,
        )
        from app.agents.text_runtime import DATABASE_PROFILE
        from app.config import Settings
        settings = Settings(text_service_encryption_key=Fernet.generate_key().decode())
        with factory.begin() as session:
            row = session.get(TextServiceConnection, "text")
            update_service_connection(session, settings, TextServiceConnectionUpdate(
                expected_revision=row.revision,base_url=profile.base_url,
                service_key="TEST_ONLY_service_key",reason="TEST_ONLY pipeline"),
                session.scalar(select(User.id).limit(1)))
            row.default_model_id = str(uuid4())  # Deliberately differs from the original task.
        registry = AgentRegistry.from_settings(settings)
        profile_ref = DATABASE_PROFILE

    service = UpstreamService(factory, registry)
    publisher = ResultPublisher(ResultPersistence(factory, service, LocalStore(tmp_path)))

    def stamp(connection, snapshot):
        snapshot.agent_snapshot = dict(snapshot.agent_snapshot, protocol_version=PROTOCOL)
        snapshot.routing_snapshot = dict(
            protocol_version=PROTOCOL,
            profile=profile_ref,
            base_url=profile.base_url,
            model_config_id=str(profile.model_config_id),
            supports_images=False,
        )
        spec = dict(snapshot.spec_snapshot, delivery_kind="single")
        snapshot.spec_snapshot = spec
        payloads = {
            "D-01": {
                "result_specs": {
                    spec["spec_id"]: dict(
                        protocol_version=PROTOCOL,
                        spec_version=spec["version"],
                        spec_digest=content_digest(spec),
                        expected_item_keys=["original-1"],
                        media_type="text/plain",
                    )
                }
            },
            "D-10": {
                "result_download": dict(
                    allowed_download_sources=[DOWNLOAD_SOURCE],
                    max_download_bytes=10000,
                    max_total_bytes=20000,
                    download_timeout_seconds=10,
                    max_redirects=0,
                )
            },
        }
        versions = dict(snapshot.policy_versions)
        for decision, payload in payloads.items():
            version = "TEST_ONLY_text_" + uuid4().hex
            policy = DecisionVersion(
                decision_id=decision,
                version=version,
                mode="mock",
                test_only=True,
                payload=payload,
            )
            connection.execute(
                DecisionVersionRecord.__table__.insert().values(**policy.model_dump(mode="json"))
            )
            versions[decision] = version
        snapshot.policy_versions = versions

    def create(*, parameters=None):
        def configure(connection, snapshot):
            stamp(connection, snapshot)
            if parameters is not None:
                from app.catalog.schemas import AgentVersion, single_spec

                agent = AgentVersion.model_validate(snapshot.agent_snapshot)
                snapshot.input_snapshot = dict(snapshot.input_snapshot, parameters=parameters)
                snapshot.spec_snapshot = single_spec(agent).model_dump(mode="json")
                snapshot.quote = dict(snapshot.quote, policy_versions={
                    "platform-pricing": str(uuid4()),
                })
                policy = DecisionVersion(
                    decision_id="D-01", version="TEST_ONLY_text_" + uuid4().hex,
                    mode="mock", test_only=True, payload={"agents": {
                        str(agent.agent_id): {"protocol_version": PROTOCOL},
                    }},
                )
                connection.execute(DecisionVersionRecord.__table__.insert().values(
                    **policy.model_dump(mode="json"),
                ))
                snapshot.policy_versions = dict(
                    snapshot.policy_versions, **{"D-01": policy.version},
                )

        return upstream[2](
            snapshot_transform=configure, endpoint=profile.base_url, secret_ref="text-v1"
        )

    def submit(task_id):
        lease = LeaseManager(factory).claim_task(task_id, "text-test")
        try:
            return service.submit_original_task(task_id, lease)
        finally:
            service.leases.release(lease)

    yield factory, service, publisher, create, submit, state
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_sync_text_saves_publishes_and_settles_once(text_runtime):
    factory, service, publisher, create, submit, state = text_runtime
    task_id = create()
    assert submit(task_id).state == "RUNNING"
    assert service.poll_original_task(task_id).state == "SAVING"
    assert publisher.run(task_id).state == "SUCCEEDED"
    assert publisher.run(task_id).state == "SUCCEEDED"
    with factory() as session:
        task = session.get(GenerationTask, task_id)
        account = session.get(CreditAccount, task.user_id)
        assert (account.available, account.frozen, account.consumed) == (70, 0, 30)
        assert len(session.scalars(select(Work).where(Work.task_id == task_id)).all()) == 1
        assert (
            len(
                session.scalars(
                    select(CreditLedger).where(
                        CreditLedger.task_id == task_id,
                        CreditLedger.kind == "consume",
                    )
                ).all()
            )
            == 1
        )
        assert state["posts"][0][0] == task.external_submission_id
    assert len(state["posts"]) == 1


def test_concurrency_rejection_queues_and_retries_same_task_once(text_runtime):
    factory, service, publisher, create, submit, state = text_runtime
    task_id = create()
    state["scenario"] = "limited"
    assert submit(task_id).state == "QUEUED"
    with factory() as session:
        assert session.get(GenerationTask, task_id).settlement_state == "FROZEN"
    state["scenario"] = "success"
    # The scheduler enforces not-before; direct invocation also refuses an early retry.
    assert submit(task_id).state == "QUEUED"
    assert len(state["posts"]) == 1
    from sqlalchemy import text
    with factory.begin() as session:
        session.execute(text("UPDATE generation_tasks SET submission_not_before=UTC_TIMESTAMP(6) "
                             "WHERE id=:id"), {"id": task_id})
    assert submit(task_id).state == "RUNNING"
    assert service.poll_original_task(task_id).state == "SAVING"
    assert publisher.run(task_id).state == "SUCCEEDED"
    assert len(state["posts"]) == 2
    assert state["posts"][0][0] == state["posts"][1][0]
    with factory() as session:
        kinds = session.scalars(select(CreditLedger.kind).where(
            CreditLedger.task_id == task_id,
        )).all()
        assert kinds.count("freeze") == 1 and kinds.count("consume") == 1
        assert "release" not in kinds


def test_full_local_pool_queues_without_attempt_or_extra_charge(text_runtime):
    from app.agents.execution_pool import text_scope
    from app.agents.models import UpstreamAttempt

    factory, service, publisher, create, submit, state = text_runtime
    task_id = create()
    with factory() as session:
        adapter = service.registry.bind_task(session, session.get(GenerationTask, task_id)).adapter
    scope = text_scope(adapter.profile.base_url)
    tokens = [service.text_pool.acquire(scope) for _ in range(6)]
    assert all(tokens)
    try:
        assert submit(task_id).state == "QUEUED"
        assert state["posts"] == []
        with factory() as session:
            assert session.scalar(select(UpstreamAttempt).where(
                UpstreamAttempt.task_id == task_id,
            )) is None
            assert session.get(GenerationTask, task_id).settlement_state == "FROZEN"
    finally:
        for token in tokens:
            service.text_pool.release(scope, token)
    from sqlalchemy import text
    with factory.begin() as session:
        session.execute(text("UPDATE generation_tasks SET submission_not_before=UTC_TIMESTAMP(6) "
                             "WHERE id=:id"), {"id": task_id})
    assert submit(task_id).state == "RUNNING"
    assert service.poll_original_task(task_id).state == "SAVING"
    assert publisher.run(task_id).state == "SUCCEEDED"
    assert len(state["posts"]) == 1


def test_restart_replays_committed_limit_rejection_without_another_post(
    text_runtime, monkeypatch,
):
    factory, service, publisher, create, submit, state = text_runtime
    task_id = create()
    state["scenario"] = "limited"
    apply = service._apply_observation
    monkeypatch.setattr(service, "_apply_observation", lambda *args, **kw: (
        _ for _ in ()).throw(RuntimeError("worker stopped after receipt")))
    with pytest.raises(RuntimeError, match="worker stopped"):
        submit(task_id)
    monkeypatch.setattr(service, "_apply_observation", apply)
    assert service.recover_original_task(task_id).state == "QUEUED"
    assert len(state["posts"]) == 1
    assert state["gets"] == []


def test_audited_historical_rejection_preserves_original_unknown_receipt(text_runtime):
    from datetime import timedelta

    from sqlalchemy import event, text

    from app.agents.contracts import SubmitOutcome
    from app.agents.models import UpstreamAttempt, UpstreamEvidence
    from app.dispatch.recovery import database_now

    factory, service, publisher, create, submit, state = text_runtime
    task_id = create()
    state["scenario"] = "lost_reply"

    def old_attempt(mapper, connection, target):
        target.created_at -= timedelta(seconds=601)

    event.listen(UpstreamAttempt, "before_insert", old_attempt)
    try:
        assert submit(task_id).state == "INVESTIGATING"
    finally:
        event.remove(UpstreamAttempt, "before_insert", old_attempt)
    with factory.begin() as session:
        task = session.get(GenerationTask, task_id)
        attempt = service._latest(session, task_id)
        audit = UpstreamEvidence(
            id=str(uuid4()), task_id=task_id, attempt_id=attempt.id,
            kind="concurrency_rejection_audit", created_at=database_now(session),
            payload={"identity": service._identity(session, task,
                        service.registry.bind_task(session, task)), "operation": "submit",
                     "outcome": SubmitOutcome(status="RATE_LIMITED", protocol_version=PROTOCOL,
                        external_submission_id=task.external_submission_id,
                        retry_after_seconds=1).model_dump(mode="json"),
                     "verified_by": "text-agent-v1.database_audit",
                     "upstream_record_absent": True, "http_status": 429,
                     "error_code": "concurrency_limit"},
        )
        session.add(audit)
        session.flush()
        proof = service._text_rejection_retry(session, task, audit.id)
        assert proof.safe_retry.kind == "proven_not_accepted"
        assert service._text_retry_reference(session, task) == audit.id
        original = session.scalar(select(UpstreamEvidence).where(
            UpstreamEvidence.attempt_id == attempt.id, UpstreamEvidence.kind == "observation",
        ))
        assert original.payload["outcome"]["status"] == "UNKNOWN"
    # A restart between the audit commit and requeue must discover the audit itself.
    assert service.recover_original_task(task_id).state == "QUEUED"
    with factory.begin() as session:
        session.execute(text("UPDATE generation_tasks SET submission_not_before=UTC_TIMESTAMP(6) "
                             "WHERE id=:id"), {"id": task_id})
    state["scenario"] = "success"
    assert submit(task_id).state == "RUNNING"
    assert service.poll_original_task(task_id).state == "SAVING"
    assert publisher.run(task_id).state == "SUCCEEDED"


def test_lost_submit_reply_stays_frozen_and_never_reposts(text_runtime):
    factory, service, publisher, create, submit, state = text_runtime
    state["scenario"] = "lost_reply"
    task_id = create()
    assert submit(task_id).state == "INVESTIGATING"
    for _ in range(2):
        assert service.recover_original_task(task_id).state == "INVESTIGATING"
    with factory() as session:
        assert session.get(GenerationTask, task_id).settlement_state == "FROZEN"
    assert len(state["posts"]) == 1


def test_definite_record_failure_releases_once(text_runtime):
    factory, service, publisher, create, submit, state = text_runtime
    state["scenario"] = "failure"
    task_id = create()
    assert submit(task_id).state == "RUNNING"
    service.poll_original_task(task_id)
    from app.ledger.service import release_credits
    from app.tasks.state_machine import TransitionEvidence

    for _ in range(2):
        lease = service.leases.claim_task(task_id, "text-failure-test")
        if lease:
            try:
                with factory() as session, session.begin():
                    publisher.install_verifiers(session)
                    release_credits(
                        session,
                        task_id,
                        TransitionEvidence(lease, service.pending_failure(task_id)),
                    )
            finally:
                service.leases.release(lease)
    with factory() as session:
        task = session.get(GenerationTask, task_id)
        assert task.state == "FAILED"
        account = session.get(CreditAccount, task.user_id)
        assert (account.available, account.frozen, account.consumed) == (100, 0, 0)
        assert (
            len(
                session.scalars(
                    select(CreditLedger).where(
                        CreditLedger.task_id == task_id,
                        CreditLedger.kind == "release",
                    )
                ).all()
            )
            == 1
        )
    assert len(state["posts"]) == 1


def test_sync_generation_renews_lease_while_waiting(text_runtime, monkeypatch):
    import app.agents.upstream as upstream_module

    factory, service, publisher, create, submit, state = text_runtime
    state["scenario"] = "slow"
    renewed = []
    original = service.leases.renew

    def renew(lease):
        result = original(lease)
        renewed.append(result)
        state["release"].set()
        return result

    monkeypatch.setattr(upstream_module, "SUBMIT_LEASE_REFRESH_SECONDS", 0.02)
    monkeypatch.setattr(service.leases, "renew", renew)
    task_id = create()
    assert submit(task_id).state == "RUNNING"
    assert renewed and all(renewed)
    service.poll_original_task(task_id)
    assert publisher.run(task_id).state == "SUCCEEDED"
    assert len(state["posts"]) == 1


def test_original_task_retains_model_configuration_after_profile_change(text_runtime):
    factory, service, publisher, create, submit, state = text_runtime
    task_id = create()
    submit(task_id)
    if service.registry.settings is not None:
        from app.admin.models import TextServiceConnection
        with factory.begin() as session:
            session.get(TextServiceConnection, 'text').default_model_id = str(uuid4())
    else:
        profile = service.registry.text_profiles["text-v1"]
        service.registry.text_profiles["text-v1"] = profile.model_copy(
            update={"model_config_id": uuid4()}
        )
    assert service.poll_original_task(task_id).state == "SAVING"
    assert publisher.run(task_id).state == "SUCCEEDED"
    assert len(state["posts"]) == 1


def test_save_failure_recovers_original_without_generation(text_runtime, monkeypatch):
    factory, service, publisher, create, submit, state = text_runtime
    task_id = create()
    submit(task_id)
    service.poll_original_task(task_id)
    store = publisher.persistence.store
    original = store.commit

    def disk_full(*args, **kwargs):
        raise OSError("TEST_ONLY full disk")

    monkeypatch.setattr(store, "commit", disk_full)
    assert publisher.run(task_id) is None
    with factory() as session:
        task = session.get(GenerationTask, task_id)
        assert task.state == "SAVE_RECOVERY" and task.settlement_state == "FROZEN"
    monkeypatch.setattr(store, "commit", original)
    assert publisher.run(task_id).state == "SUCCEEDED"
    assert len(state["posts"]) == 1


def test_warnings_remain_bound_to_published_work_after_reread(text_runtime, monkeypatch):
    from types import SimpleNamespace

    from app.catalog.service import CatalogService
    from app.conversations.models import Message
    from app.tasks.state_machine import TransitionError
    from app.works.service import WorkService

    factory, service, publisher, create, submit, state = text_runtime
    task_id = create()
    submit(task_id)
    service.poll_original_task(task_id)
    assert publisher.run(task_id).state == "SUCCEEDED"
    # Only session authentication is substituted; resource ownership and content
    # verification still use the actual persisted task, work, message and files.
    monkeypatch.setattr(CatalogService, "_principal", lambda *a, **kw: None)
    with factory() as session:
        work = session.scalar(select(Work).where(Work.task_id == task_id))
        message = session.get(Message, work.message_id)
        assert message.content["warnings"] == ["材质信息尚待核实"]
        view = WorkService(session)._view(SimpleNamespace(user_id=work.user_id), work)
        assert view.warnings == ["材质信息尚待核实"]
        assert view.items[0].text == "测试商品的完整文案"
    assert publisher.published(task_id).state == "SUCCEEDED"
    with factory() as session:
        work = session.scalar(select(Work).where(Work.task_id == task_id))
        message = session.get(Message, work.message_id)
        # Committed messages are DB-enforced append-only. Exercise the verifier
        # with an unflushed altered view without changing that durable history.
        with session.no_autoflush:
            message.content = dict(message.content, warnings=["篡改后的提示"])
            task = session.get(GenerationTask, task_id)
            with pytest.raises(TransitionError, match="PUBLICATION_REQUIRED"):
                publisher.verify_publication(session, task, "SUCCEEDED", work.manifest_id, None)
        session.rollback()
    assert publisher.published(task_id).state == "SUCCEEDED"
    assert len(state["posts"]) == 1


def test_writing_requirements_reach_publication_without_reposting(text_runtime):
    factory, service, publisher, create, submit, state = text_runtime
    task_id = create(parameters={
        "copy_type": "宣传文案", "platform": "淘宝", "audience": "学生",
        "tone": "自然", "max_chars": 300,
    })
    submit(task_id)
    assert service.poll_original_task(task_id).state == "SAVING"
    assert publisher.run(task_id).state == "SUCCEEDED"
    assert publisher.run(task_id).state == "SUCCEEDED"
    assert len(state["posts"]) == 1
    assert state["posts"][0][1]["requirements"]["max_chars"] == 300
    with factory() as session:
        task = session.get(GenerationTask, task_id)
        assert task.settlement_state == "CONSUMED"
        assert len(session.scalars(select(Work).where(Work.task_id == task_id)).all()) == 1
        assert len(session.scalars(select(CreditLedger).where(
            CreditLedger.task_id == task_id, CreditLedger.kind == "consume",
        )).all()) == 1


def test_recover_rejected_writing_result_preserves_history_and_does_not_generate(
    text_runtime, monkeypatch,
):
    from app.agents.callbacks import CallbackService
    from app.agents.models import AgentEvent, AgentEventDecision
    from app.results.recovery import recover_text_result
    from app.tasks.state_machine import TransitionError

    factory, service, publisher, create, submit, state = text_runtime
    task_id = create(parameters={"platform": "淘宝", "max_chars": 300})
    state["warnings"] = []
    submit(task_id)
    original = CallbackService._manifest

    def old_policy(*args):
        raise TransitionError("RESULT_POLICY_UNAVAILABLE")

    monkeypatch.setattr(CallbackService, "_manifest", old_policy)
    assert service.poll_original_task(task_id).state == "INVESTIGATING"
    monkeypatch.setattr(CallbackService, "_manifest", original)
    with factory() as session:
        rejected = session.scalar(select(AgentEventDecision).where(
            AgentEventDecision.task_id == task_id,
        ))
        assert rejected.disposition == "CONFLICT"
        rejected_id = rejected.event_ref
        original_event = session.get(AgentEvent, rejected_id)
        original_manifest = original_event.payload["event"]["result"]
        assert not original_manifest.get("warnings")
    next(iter(state["records"].values()))["result_json"]["warnings"] = ["新增核验提示"]
    assert recover_text_result(service, task_id).state == "SAVING"
    assert publisher.run(task_id).state == "SUCCEEDED"
    assert recover_text_result(service, task_id).state == "SUCCEEDED"
    assert len(state["posts"]) == 1
    with factory() as session:
        assert session.get(AgentEventDecision, rejected_id).disposition == "CONFLICT"
        assert session.get(AgentEvent, rejected_id).payload["event"]["result"] == original_manifest
        repaired = session.scalar(select(AgentEvent).where(
            AgentEvent.task_id == task_id, AgentEvent.id != rejected_id,
        ))
        repaired_manifest = repaired.payload["event"]["result"]
        assert repaired_manifest["items"] == original_manifest["items"]
        assert repaired_manifest["warnings"] == ["新增核验提示"]
        assert len(session.scalars(select(AgentEvent).where(
            AgentEvent.task_id == task_id,
        )).all()) == 2
        assert len(session.scalars(select(CreditLedger).where(
            CreditLedger.task_id == task_id, CreditLedger.kind == "consume",
        )).all()) == 1


def test_recovery_refuses_changed_original_result(text_runtime, monkeypatch):
    from app.agents.callbacks import CallbackService
    from app.results.recovery import recover_text_result
    from app.tasks.state_machine import TransitionError

    factory, service, publisher, create, submit, state = text_runtime
    task_id = create(parameters={"platform": "淘宝"})
    submit(task_id)
    original = CallbackService._manifest

    def old_policy(*args):
        raise TransitionError("RESULT_POLICY_UNAVAILABLE")

    monkeypatch.setattr(CallbackService, "_manifest", old_policy)
    service.poll_original_task(task_id)
    monkeypatch.setattr(CallbackService, "_manifest", original)
    next(iter(state["records"].values()))["result_json"]["text"] = "changed result"
    with pytest.raises(TransitionError, match="RESULT_MANIFEST_MISMATCH"):
        recover_text_result(service, task_id)
    with factory() as session:
        assert session.get(GenerationTask, task_id).state == "INVESTIGATING"
    assert len(state["posts"]) == 1


def test_revalidation_restarts_from_committed_receipt_without_another_query(
    text_runtime, monkeypatch,
):
    from app.agents.callbacks import CallbackService
    from app.results.recovery import recover_text_result
    from app.tasks.state_machine import TransitionError

    factory, service, publisher, create, submit, state = text_runtime
    task_id = create(parameters={"platform": "淘宝"})
    submit(task_id)
    original_manifest = CallbackService._manifest
    monkeypatch.setattr(CallbackService, "_manifest", lambda *args: (
        _ for _ in ()
    ).throw(TransitionError("RESULT_POLICY_UNAVAILABLE")))
    assert service.poll_original_task(task_id).state == "INVESTIGATING"
    monkeypatch.setattr(CallbackService, "_manifest", original_manifest)
    original_reduce = CallbackService.reduce_pending
    monkeypatch.setattr(CallbackService, "reduce_pending", lambda *args: (
        _ for _ in ()
    ).throw(RuntimeError("worker stopped after receipt commit")))
    with pytest.raises(RuntimeError, match="worker stopped"):
        recover_text_result(service, task_id)
    monkeypatch.setattr(CallbackService, "reduce_pending", original_reduce)
    original_transport = service._leased_transport
    monkeypatch.setattr(service, "_leased_transport", lambda *args: pytest.fail(
        "Committed revalidation must resume without querying upstream again"))
    assert recover_text_result(service, task_id).state == "SAVING"
    monkeypatch.setattr(service, "_leased_transport", original_transport)
    assert publisher.run(task_id).state == "SUCCEEDED"
    assert recover_text_result(service, task_id).state == "SUCCEEDED"
    assert len(state["posts"]) == 1
    with factory() as session:
        assert len(session.scalars(select(Work).where(Work.task_id == task_id)).all()) == 1
        assert len(session.scalars(select(CreditLedger).where(
            CreditLedger.task_id == task_id, CreditLedger.kind == "consume",
        )).all()) == 1
