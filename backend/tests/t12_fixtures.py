"""T09: real MySQL/Redis and HTTP simulator; only fixture-owned task identities."""

from threading import Thread
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.agents.mock_server import PROTOCOL, BoundedServer
from app.auth.models import User
from app.catalog.models import AgentRecord
from app.dispatch.outbox import enqueue_outbox
from app.ledger.models import CreditAccount
from app.ledger.service import freeze_credits, grant_credits, now
from app.tasks.models import GenerationTask, TaskSnapshot


@pytest.fixture
def upstream(mysql_engine, redis_namespace, ledger_task, monkeypatch):
    from worker import main

    # Missing trusted worker composition is a business failure, not an import error.
    assert callable(getattr(main, "compose_worker", None)), "Worker has no upstream handlers"
    from app.agents.registry import AgentRegistry
    from app.agents.upstream import UpstreamService

    monkeypatch.setenv("APP_TEST_ONLY", "true")
    server = BoundedServer(("127.0.0.1", 0))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    factory = sessionmaker(mysql_engine, expire_on_commit=False)
    registry = AgentRegistry(mode="mock", test_only=True)
    service = UpstreamService(factory, registry)
    owned = []

    def create(scenario="normal", kind="copy", agent_identity=None):
        task_id, user_id = str(uuid4()), str(uuid4())
        with Session(mysql_engine) as s, s.begin():
            s.add(
                User(
                    id=user_id,
                    account_normalized="t09_" + uuid4().hex,
                    password_hash="TEST_ONLY_unusable",
                    created_at=now(),
                )
            )
            s.flush()
            s.add(
                CreditAccount(user_id=user_id, available=0, frozen=0, consumed=0, credited_total=0)
            )
            s.flush()

            grant_credits(s, user_id, "signup", f"signup:{user_id}", 100, "TEST_ONLY signup", None)

            def snapshot_before_insert(mapper, connection, target):
                target.agent_snapshot = dict(
                    agent_id=agent_identity or target.agent_snapshot["agent_id"],
                    version="TEST_ONLY_v1",
                    kind=kind,
                    name="TEST_ONLY Agent",
                    mode="mock",
                    test_only=True,
                    enabled=True,
                    protocol_version=PROTOCOL,
                    input_support=dict(
                        product_required_fields=[],
                        instruction_required=False,
                        min_materials=0,
                        max_materials=0,
                    ),
                    policy_versions={},
                    secret_configured=False,
                )

            def identity_before_insert(mapper, connection, target):
                if agent_identity:
                    target.agent_id = agent_identity

            event.listen(GenerationTask, "before_insert", identity_before_insert)
            event.listen(TaskSnapshot, "before_insert", snapshot_before_insert)
            try:
                task = ledger_task(s, user_id, task_id)
            finally:
                event.remove(TaskSnapshot, "before_insert", snapshot_before_insert)
                event.remove(GenerationTask, "before_insert", identity_before_insert)
            freeze_credits(s, user_id, task_id, 30)
            snapshot = s.get(TaskSnapshot, task_id).agent_snapshot
            if s.get(AgentRecord, (task.agent_id, task.agent_version)) is None:
                s.add(
                    AgentRecord(
                        agent_id=task.agent_id,
                        version=task.agent_version,
                        snapshot=snapshot,
                        endpoint=url,
                    )
                )
            external = task.external_submission_id
            enqueue_outbox(s, task_id, "submit")
        owned.append(task_id)
        with server.simulator.lock:
            server.simulator.configure(kind, external, {"scenario": scenario})
        return task_id

    def worker():
        redis, prefix = redis_namespace
        return main.compose_worker(
            factory, redis, prefix + "dispatch", "workers", "t09", registry=registry, task_ids=owned
        )

    yield factory, service, create, server, worker
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
