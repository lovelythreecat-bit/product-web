from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import create_app

pytestmark = pytest.mark.integration


def test_migration_environment_is_initialized(mysql_engine):
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    expected_head = ScriptDirectory.from_config(config).get_current_head()
    with mysql_engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == expected_head
        )
        assert connection.execute(text("SELECT DATABASE()")).scalar_one() == "ecommerce_ai_test"


def test_real_mysql_commit_and_rollback(mysql_engine, mysql_probe_table):
    name = mysql_probe_table
    with mysql_engine.begin() as connection:
        connection.execute(text(f"INSERT INTO {name} VALUES (1, 10)"))
    with mysql_engine.connect() as connection:
        assert connection.execute(text(f"SELECT value FROM {name} WHERE id=1")).scalar_one() == 10
        connection.execute(text(f"UPDATE {name} SET value=99 WHERE id=1"))
        connection.rollback()
    with mysql_engine.connect() as connection:
        assert connection.execute(text(f"SELECT value FROM {name} WHERE id=1")).scalar_one() == 10


def test_session_fixture_commit_stays_inside_outer_transaction(
    mysql_engine, mysql_probe_table, db_session
):
    name = mysql_probe_table
    db_session.execute(text(f"INSERT INTO {name} VALUES (2, 20)"))
    db_session.commit()
    # A committed savepoint must not leak into another connection.
    with mysql_engine.connect() as connection:
        assert connection.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar_one() == 0


def test_dependency_does_not_implicitly_commit(mysql_settings, mysql_engine, mysql_probe_table):
    app = create_app(mysql_settings)
    from fastapi import Depends

    @app.post("/probe")
    def probe(session: Session = Depends(get_session)):
        session.execute(text(f"INSERT INTO {mysql_probe_table} VALUES (3, 30)"))
        return {"ok": True}

    with TestClient(app) as client:
        assert client.post("/probe").status_code == 200
    with mysql_engine.connect() as connection:
        assert (
            connection.execute(text(f"SELECT COUNT(*) FROM {mysql_probe_table}")).scalar_one() == 0
        )


def test_readiness_succeeds_with_real_mysql_and_declared_storage(mysql_settings, mysql_engine):
    with TestClient(create_app(mysql_settings)) as client:
        response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["checks"] == {"storage": True, "database": True}


def test_redis_stream_roundtrip(redis_namespace):
    client, prefix = redis_namespace
    stream = prefix + "dispatch"
    event_id = client.xadd(stream, {"event_id": "TEST_ONLY-outbox-1"})
    messages = client.xread({stream: "0-0"})
    assert len(messages) == 1
    stream_name, entries = messages[0]
    assert stream_name == stream.encode()
    assert entries == [(event_id, {b"event_id": b"TEST_ONLY-outbox-1"})]
