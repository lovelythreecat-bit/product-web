"""T22a offline checks only: no shared MySQL, Redis, client invocation or deployment."""

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import Settings
from app.main import create_app
from app.operations.metrics import project_metrics, validate_thresholds
from app.operations.runtime import independent_roots
from app.operations.telemetry import event

SCRIPTS = Path(__file__).resolve().parents[3] / "infra" / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


storage = load("verify_storage")
backup = load("backup_restore")


def test_backup_detects_missing_file_and_includes_public_cleanup(tmp_path):
    path = tmp_path / "public.blob"
    path.write_bytes(b"TEST_ONLY public copy")
    entry = {
        "path": path.name,
        "actual_bytes": path.stat().st_size,
        "sha256": storage.digest(path),
        "required": True,
        "state": "published",
    }
    assert storage.verify(tmp_path, [entry]) == []
    missing = dict(entry, path="missing.blob")
    assert storage.verify(tmp_path, [missing])[0]["code"] == "missing_file"
    pending = dict(missing, required=False, state="cleanup_pending")
    assert storage.verify(tmp_path, [pending]) == []
    path.write_bytes(b"tampered")
    assert storage.verify(tmp_path, [entry])[0]["code"] == "file_hash_mismatch"
    with pytest.raises(ValueError):
        storage.verify(tmp_path, [dict(entry, path="../outside")])


def test_deploy_keeps_storage_root():
    independent_roots("/srv/releases/v1", "/data/ecommerce")
    independent_roots(r"F:\release\v1", r"F:\persistent")
    for release, persistent in (
        ("/srv/release", "/srv/release/data"),
        ("/srv", "/srv"),
        ("relative", "/data"),
    ):
        with pytest.raises(ValueError):
            independent_roots(release, persistent)
    for invalid in (
        {"unknown": 1},
        {"capacity_used_ratio_max": 1.1},
        {"outbox_pending": float("nan")},
    ):
        with pytest.raises(ValueError):
            validate_thresholds(invalid)


def test_restore_rejects_existing_or_unowned_target(tmp_path):
    owner = str(uuid4())
    (tmp_path / ".operations-owner.json").write_text(
        json.dumps(
            {
                "owner": owner,
                "purpose": "isolated-restore",
                "network_isolated": True,
            }
        )
    )
    target = tmp_path / "TEST_ONLY_new"
    assert backup.fresh_target(target, tmp_path, owner, "isolated-restore") == target
    target.mkdir()
    for destination, identity in (
        (target, owner),
        (tmp_path / "another", str(uuid4())),
        (tmp_path.parent / "outside", owner),
    ):
        with pytest.raises(ValueError):
            backup.fresh_target(destination, tmp_path, identity, "isolated-restore")


def test_client_arguments_never_embed_password_or_shell(tmp_path):
    client, defaults = tmp_path / "mysql.exe", tmp_path / "client.cnf"
    client.write_bytes(b"TEST_ONLY never executed")
    defaults.write_text("[client]\npassword=TEST_ONLY\n")
    url = make_url("mysql+pymysql://operator:DO_NOT_LOG@127.0.0.1:13306/test_db")
    command = backup.client_command(client, defaults, url, dump=True)
    assert command[1] == "--defaults-file=" + str(defaults)
    assert "DO_NOT_LOG" not in " ".join(command)
    assert "--skip-add-drop-table" in command
    assert "--single-transaction" in command
    assert command[-1] == "test_db"
    with pytest.raises(ValueError):
        backup.client_command(client, defaults, url.set(database="db; DROP DATABASE x"))


def test_restore_marker_blocks_all_api_and_trace_ignores_input(tmp_path):
    app = create_app(
        Settings(
            mode="mock",
            test_only=True,
            storage_root=tmp_path,
            storage_persistent=True,
            database_url=None,
            redis_url=None,
        )
    )
    with TestClient(app) as client:
        response = client.get("/api/v1/health/live", headers={"X-Trace-ID": "SECRET"})
        assert response.status_code == 200
        assert response.headers["x-trace-id"] != "SECRET"
        (tmp_path / ".restore-isolated.json").write_text("{}")
        for route in ("/api/v1/site/cases", "/api/v1/health/live", "/api/v1/tasks"):
            response = client.get(route)
            assert response.status_code == 503
            assert response.headers["cache-control"] == "no-store"


def test_telemetry_drops_untrusted_identifiers(monkeypatch):
    captured = []
    monkeypatch.setattr("app.operations.telemetry.logger.info", captured.append)
    event("task_stage", task_id="token=SECRET", trace_id="SECRET", outcome="SECRET")
    assert "SECRET" not in captured[0]
    assert "task_id" not in json.loads(captured[0])


@pytest.mark.parametrize(
    "free_bytes,total_bytes,used_ratio,committed_ratio,unreserved,capacity_alert",
    [(10, 100, 0.9, 1.1, 0, True), (50, 100, 0.5, 0.7, 30, False),
     (0, 100, 1.0, 1.2, 0, True), (10, None, None, None, 0, False)],
)
def test_metrics_outbox_investigation_capacity(
    free_bytes, total_bytes, used_ratio, committed_ratio, unreserved, capacity_alert
):
    # SQLite executes the real aggregate SELECTs; only MySQL datetime spelling is adapted.
    engine = create_engine("sqlite://")
    now = "2026-10-12 12:00:00"
    with engine.connect() as connection:
        raw = connection.connection.driver_connection
        raw.create_function("UTC_TIMESTAMP", 1, lambda _: now)
        raw.create_function("GREATEST", 2, max)
        raw.create_function(
            "TIMESTAMPDIFF",
            3,
            lambda unit, a, b: (
                datetime.fromisoformat(b) - datetime.fromisoformat(a)
            ).total_seconds()
            * (1000000 if unit == "MICROSECOND" else 1),
        )
        for sql in (
            "CREATE TABLE generation_tasks "
            "(id TEXT,state TEXT,created_at TEXT,recovery_due_at TEXT)",
            "CREATE TABLE task_state_events (task_id TEXT,to_state TEXT,created_at TEXT)",
            "CREATE TABLE dispatch_outbox (dispatched_at TEXT,ready_at TEXT)",
            "CREATE TABLE investigations (status TEXT,deadline_at TEXT)",
            "CREATE TABLE public_cases (state TEXT)",
            "CREATE TABLE storage_pools "
            "(id TEXT,reserved_bytes INT,actual_bytes INT)",
            "INSERT INTO generation_tasks VALUES ('1','SUCCEEDED','2026-10-12 11:00:00',NULL)",
            "INSERT INTO generation_tasks VALUES ('2','FAILED','2026-10-12 11:00:00',NULL)",
            "INSERT INTO generation_tasks VALUES ('3','SAVE_RECOVERY',"
            "'2026-10-12 11:00:00','2026-10-12 11:55:00')",
            "INSERT INTO task_state_events VALUES ('1','SUCCEEDED','2026-10-12 11:00:10')",
            "INSERT INTO task_state_events VALUES ('2','FAILED','2026-10-12 11:00:30')",
            "INSERT INTO dispatch_outbox VALUES (NULL,'2026-10-12 11:59:00')",
            "INSERT INTO investigations VALUES ('open','2026-10-12 11:00:00')",
            "INSERT INTO public_cases VALUES ('cleanup_pending')",
            "INSERT INTO storage_pools VALUES ('test',20,70)",
        ):
            connection.exec_driver_sql(sql)
        with Session(bind=connection) as session:

            class DialectAdapter:
                def execute(self, statement):
                    sql = str(statement).replace("TIMESTAMPDIFF(SECOND,", "TIMESTAMPDIFF('SECOND',")
                    sql = sql.replace("TIMESTAMPDIFF(MICROSECOND,", "TIMESTAMPDIFF('MICROSECOND',")
                    return session.execute(text(sql))

            metrics = project_metrics(
                DialectAdapter(),
                free_bytes=free_bytes,
                total_bytes=total_bytes,
                thresholds={
                    "outbox_pending": 0,
                    "investigation_overdue": 0,
                    "save_recovery": 0,
                    "disk_free_bytes_min": 20,
                    "capacity_used_ratio_max": 0.8,
                },
            )
    engine.dispose()
    assert metrics["terminal_success_rate"] == 0.5
    assert metrics["terminal_mean_seconds"] == 20
    assert metrics["supplier_cost"] is None
    assert metrics["supplier_cost_status"] == "unavailable"
    assert metrics["outbox_oldest_due_seconds"] == 60
    assert metrics["save_oldest_due_seconds"] == 300
    assert metrics["capacity"] == [{"id": "test", "reserved_bytes": 20, "actual_bytes": 70}]
    assert metrics["disk_free_bytes"] == free_bytes
    assert metrics["disk_total_bytes"] == total_bytes
    assert metrics["disk_reserved_bytes"] == 20
    assert metrics["disk_unreserved_bytes"] == unreserved
    assert metrics["disk_used_ratio"] == used_ratio
    assert metrics["disk_committed_ratio"] == committed_ratio
    expected_alerts = {
        "outbox_pending",
        "investigation_overdue",
        "save_recovery",
    }
    if free_bytes < 20:
        expected_alerts.add("disk_free_bytes")
    if capacity_alert:
        expected_alerts.add("capacity")
    assert set(metrics["alerts"]) == expected_alerts
