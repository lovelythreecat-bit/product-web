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
        or url.database != "ecommerce_ai_test"
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
