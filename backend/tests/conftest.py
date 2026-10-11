"""Real-service fixtures. Missing services skip; unsafe targets fail before any SQL."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from redis import Redis
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import create_db_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def require_test_environment():
    if os.getenv("TEST_ONLY") != "true" or os.getenv("APP_MODE") != "mock":
        pytest.fail("Integration fixtures require TEST_ONLY=true and APP_MODE=mock")


@pytest.fixture(scope="session")
def mysql_settings(tmp_path_factory):
    raw_url = os.getenv("TEST_DATABASE_URL")
    if raw_url is None:
        pytest.skip("Set TEST_DATABASE_URL to the isolated MySQL 8.4 test database")
    require_test_environment()
    url = make_url(raw_url)
    if (
        url.drivername != "mysql+pymysql"
        or url.database not in ("ecommerce_ai_test", "ecommerce_ai_test_t07_20261011")
        or url.username != "ecommerce_test"
    ):
        pytest.fail("Refusing any database except ecommerce_test / ecommerce_ai_test on MySQL")
    return Settings(
        mode="mock",
        test_only=True,
        database_url=raw_url,
        redis_url=None,
        storage_root=tmp_path_factory.mktemp("test-persistent-root"),
        storage_persistent=True,
    )


@pytest.fixture(scope="session")
def mysql_engine(mysql_settings):
    engine = create_db_engine(mysql_settings)
    try:
        with engine.connect() as connection:
            version = connection.execute(text("SELECT VERSION()")).scalar_one()
            if not version.startswith("8.4."):
                pytest.fail(f"MySQL 8.4 required, got {version}")
            if connection.execute(text("SELECT GET_LOCK('t01_test_migrations', 10)")).scalar() != 1:
                pytest.fail("Test migration lock unavailable")
            try:
                connection.commit()
                config = Config(str(BACKEND_ROOT / "alembic.ini"))
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
                connection.commit()
            finally:
                connection.execute(text("SELECT RELEASE_LOCK('t01_test_migrations')"))
                connection.commit()
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(mysql_engine):
    """Each test uses an outer rollback even when application code commits a savepoint.

    DDL must use separate setup/teardown because MySQL DDL implicitly commits.
    Future business tables are created by Alembic, never metadata.create_all.
    """
    with mysql_engine.connect() as connection:
        outer = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            if outer.is_active:
                outer.rollback()


@pytest.fixture
def mysql_probe_table(mysql_engine):
    # A unique fixture-owned table exercises T01 transactions without inventing business schema.
    name = f"test_probe_{uuid4().hex}"
    with mysql_engine.begin() as connection:
        connection.execute(
            text(f"CREATE TABLE {name} (id INT PRIMARY KEY, value INT NOT NULL) ENGINE=InnoDB")
        )
    try:
        yield name
    finally:
        with mysql_engine.begin() as connection:
            connection.execute(text(f"DROP TABLE IF EXISTS {name}"))


@pytest.fixture
def redis_namespace():
    url = os.getenv("TEST_REDIS_URL")
    if url is None:
        pytest.skip("Set TEST_REDIS_URL to isolated Redis 7.4 database 15")
    require_test_environment()
    client = Redis.from_url(url, socket_timeout=3, socket_connect_timeout=3)
    if client.connection_pool.connection_kwargs.get("db") != 15:
        client.close()
        pytest.fail("Integration fixtures require Redis database 15")
    prefix = f"TEST_ONLY:{uuid4().hex}:"
    try:
        if not client.info("server")["redis_version"].startswith("7.4."):
            pytest.fail("Redis 7.4 required")
        yield client, prefix
    finally:
        keys = list(client.scan_iter(match=prefix + "*"))
        if keys:
            client.delete(*keys)
        client.close()


@pytest.fixture
def auth_client(mysql_engine, mysql_settings, redis_namespace):
    from fastapi.testclient import TestClient

    from app.main import create_app

    redis, prefix = redis_namespace
    from sqlalchemy.orm import Session

    from app.ledger.models import RegistrationCreditHead
    from app.ledger.service import set_registration_credit_config
    from app.policies.schemas import DecisionVersion
    from app.policies.service import PolicyService

    with Session(mysql_engine) as session, session.begin():
        version = "TEST_ONLY_" + uuid4().hex
        PolicyService(session).add_draft(
            DecisionVersion(
                decision_id="D-05",
                version=version,
                mode="mock",
                test_only=True,
                payload={"registration": {"credits": 100}},
            )
        )
        head = session.get(RegistrationCreditHead, "mock")
        set_registration_credit_config(
            session,
            mode="mock",
            expected_version=head.version if head else None,
            amount=100,
            policy_version=version,
            reason="TEST_ONLY fixture",
        )
    app = create_app(mysql_settings.model_copy(update={"auth_origins": ["https://testserver"]}))
    app.state.auth_rate_prefix = prefix
    app.state.auth_redis = redis
    with TestClient(app, base_url="https://testserver") as client:
        client.headers.update({"Origin": "https://testserver", "X-Requested-With": "platform"})
        yield client


@pytest.fixture
def ledger_task():
    """Real relational task fixture for T04's isolated ledger transaction tests.

    It does not call admission, because these tests exercise the freeze itself.
    Every required task/product/conversation/capacity row is in the caller transaction.
    """

    def create(session, user_id, task_id, amount=30):
        from app.catalog.schemas import content_digest
        from app.conversations.models import Conversation, Product, ProductVersion
        from app.ledger.service import locked_account, now
        from app.policies.schemas import DecisionVersion
        from app.policies.service import PolicyService
        from app.storage.capacity import reserve_capacity
        from app.tasks.models import GenerationTask, TaskSnapshot

        user_id, task_id = str(user_id), str(task_id)
        locked_account(session, user_id)
        policy = "TEST_ONLY_" + uuid4().hex
        PolicyService(session).add_draft(
            DecisionVersion(
                decision_id="D-10",
                version=policy,
                mode="mock",
                test_only=True,
                payload={
                    "generation": {
                        "account_quota_bytes": 200,
                        "server_budget_bytes": 100000000,
                        "reservation_seconds": 120,
                        "reclamation_ref": "TEST_ONLY_fixture",
                        "alert_ref": "TEST_ONLY_fixture",
                    }
                },
            )
        )
        capacity = reserve_capacity(
            session, user_id, "generation:" + task_id, 1, policy, mode="mock"
        )
        conversation = Conversation(
            id=str(uuid4()), user_id=user_id, title="TEST_ONLY ledger", created_at=now()
        )
        product = Product(id=str(uuid4()), user_id=user_id)
        session.add_all([conversation, product])
        session.flush()
        product_version = ProductVersion(
            version=str(uuid4()),
            user_id=user_id,
            product_id=product.id,
            product={"name": "TEST_ONLY cup"},
            created_at=now(),
        )
        session.add(product_version)
        session.flush()
        agent_id, spec_id = str(uuid4()), str(uuid4())
        input = {
            "product_version": product_version.version,
            "product": product_version.product,
            "instruction": "TEST_ONLY ledger fixture",
            "parameters": {},
            "material_versions": [],
        }
        quote = {
            "spec_id": spec_id,
            "spec_version": "TEST_ONLY_v1",
            "price_version": "TEST_ONLY_v1",
            "agent_version": "TEST_ONLY_v1",
            "policy_versions": {},
            "credits": amount,
            "input_digest": content_digest(input),
        }
        task = GenerationTask(
            id=task_id,
            user_id=user_id,
            conversation_id=conversation.id,
            idempotency_key=uuid4().hex,
            request_hash=content_digest(input),
            agent_id=agent_id,
            agent_version="TEST_ONLY_v1",
            external_submission_id=str(uuid4()),
            state="SUBMITTED",
            state_version=1,
            settlement_state="FROZEN",
            capacity_reservation_id=capacity.id,
            fencing_token=0,
            created_at=now(),
        )
        session.add(task)
        session.flush()
        session.add(
            TaskSnapshot(
                task_id=task_id,
                user_id=user_id,
                product_version=product_version.version,
                input_snapshot=input,
                quote=quote,
                agent_snapshot={"agent_id": agent_id, "version": "TEST_ONLY_v1"},
                spec_snapshot={"spec_id": spec_id, "version": "TEST_ONLY_v1"},
                price_snapshot={"spec_id": spec_id, "version": "TEST_ONLY_v1", "credits": amount},
                policy_versions={"D-10": policy},
                capacity_estimate={"total_bytes": 1, "estimation_ref": "TEST_ONLY_fixture"},
            )
        )
        session.flush()
        return task

    return create
