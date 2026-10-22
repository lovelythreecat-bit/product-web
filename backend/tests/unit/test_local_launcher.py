"""Exercise startup decisions without starting services or using a business DB."""

import importlib.util
import os
import sys
from pathlib import Path

import pytest


def script_path():
    return Path(
        os.environ.get(
            "LOCAL_LAUNCHER_UNDER_TEST",
            Path(__file__).resolve().parents[3] / "infra/scripts/start_local.py",
        )
    )


def test_complete_startup_manager_exists():
    path = script_path()
    assert path.is_file(), "The complete local startup manager is missing"


@pytest.fixture
def launcher():
    path = script_path()
    if not path.is_file():
        pytest.skip("Startup manager availability is tested separately")
    spec = importlib.util.spec_from_file_location("local_launcher", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def service(m):
    return m.Service(
        "web-api",
        Path("C:/workspace/backend"),
        Path("C:/workspace/backend/.venv/Scripts/python.exe"),
        ("-m", "uvicorn", "app.main:application", "--port", "18000"),
        "http://127.0.0.1:18000/api/v1/health/ready",
    )


def test_owned_base_python_requires_project_parent(launcher):
    s = service(launcher)
    parent = {
        "ProcessId": 1,
        "ParentProcessId": 0,
        "ExecutablePath": str(s.python),
        "CommandLine": "python -m uvicorn app.main:application --port 18000",
    }
    child = {
        "ProcessId": 2,
        "ParentProcessId": 1,
        "ExecutablePath": "C:/shared/python.exe",
        "CommandLine": parent["CommandLine"],
    }
    stranger = {**child, "ProcessId": 3, "ParentProcessId": 999}
    assert launcher.owned_processes(s, [parent, child, stranger]) == [parent, child]


def test_similar_module_and_different_port_are_not_owned(launcher):
    s = service(launcher)
    rows = [
        {"ProcessId": i, "ParentProcessId": 0, "ExecutablePath": str(s.python), "CommandLine": cmd}
        for i, cmd in enumerate(
            (
                "python -m uvicorn app.main:application_evil --port 18000",
                "python -m uvicorn app.main:application --port 180001",
                "python -m uvicorn app.main:application --port 19000",
            )
        )
    ]
    assert launcher.owned_processes(s, rows) == []


def test_reuses_healthy_service_without_spawning(launcher, monkeypatch):
    manager = launcher.Manager(Path.cwd())
    s = service(launcher)
    monkeypatch.setattr(manager, "probe", lambda _: True)
    monkeypatch.setattr(
        manager,
        "processes",
        lambda: [
            {
                "ProcessId": 1,
                "ParentProcessId": 0,
                "ExecutablePath": str(s.python),
                "CommandLine": "python -m uvicorn app.main:application --port 18000",
            }
        ],
    )
    monkeypatch.setattr(manager, "launch", lambda _: pytest.fail("healthy service must be reused"))
    assert manager.ensure(s) == "reused"


def test_refuses_to_duplicate_unhealthy_existing_service(launcher, monkeypatch):
    manager = launcher.Manager(Path.cwd())
    s = service(launcher)
    monkeypatch.setattr(manager, "probe", lambda _: False)
    monkeypatch.setattr(
        manager,
        "processes",
        lambda: [
            {
                "ProcessId": 1,
                "ParentProcessId": 0,
                "ExecutablePath": str(s.python),
                "CommandLine": "python -m uvicorn app.main:application --port 18000",
            }
        ],
    )
    monkeypatch.setattr(manager, "launch", lambda _: pytest.fail("must not duplicate"))
    monkeypatch.setattr(
        manager,
        "wait_ready",
        lambda *a, **k: (_ for _ in ()).throw(launcher.StartupError("web-api unhealthy")),
    )
    with pytest.raises(launcher.StartupError, match="web-api"):
        manager.ensure(s)


def test_occupied_port_is_never_claimed(launcher, monkeypatch):
    manager = launcher.Manager(Path.cwd())
    s = service(launcher)
    monkeypatch.setattr(manager, "probe", lambda _: False)
    monkeypatch.setattr(manager, "processes", lambda: [])
    monkeypatch.setattr(manager, "port_open", lambda _: True)
    monkeypatch.setattr(
        manager, "launch", lambda _: pytest.fail("must not start on an occupied port")
    )
    with pytest.raises(launcher.StartupError, match="occupied"):
        manager.ensure(s)


def test_early_process_exit_cannot_report_ready(launcher, monkeypatch):
    manager = launcher.Manager(Path.cwd())
    s = service(launcher)
    process = type("Process", (), {"poll": lambda _: 1})()
    monkeypatch.setattr(manager, "probe", lambda _: True)
    with pytest.raises(launcher.StartupError, match="exited"):
        manager.wait_ready(s, process, timeout=0.1)


def test_dependency_failure_prevents_starting_worker(launcher, monkeypatch):
    manager = launcher.Manager(Path.cwd())
    monkeypatch.setattr(
        manager,
        "infrastructure",
        lambda: (_ for _ in ()).throw(launcher.StartupError("Redis unavailable")),
    )
    monkeypatch.setattr(manager, "services", lambda: pytest.fail("no services before dependencies"))
    with pytest.raises(launcher.StartupError, match="Redis"):
        manager.start()


def test_dry_run_does_not_start_infrastructure_or_processes(launcher, monkeypatch, capsys):
    manager = launcher.Manager(Path.cwd())
    monkeypatch.setattr(manager, "services", lambda: [service(launcher)])
    monkeypatch.setattr(
        manager, "infrastructure", lambda: pytest.fail("dry run must not start dependencies")
    )
    monkeypatch.setattr(
        manager, "ensure", lambda _: pytest.fail("dry run must not start processes")
    )
    manager.start(dry_run=True)
    assert "web-api" in capsys.readouterr().out


def test_worker_matching_includes_exact_stream_and_group(launcher):
    s = launcher.Service(
        "worker",
        Path("C:/web/backend"),
        Path("C:/web/backend/.venv/Scripts/python.exe"),
        ("-m", "worker.main", "--stream", "local:one", "--group", "local-workers"),
    )
    row = {
        "ProcessId": 1,
        "ParentProcessId": 0,
        "ExecutablePath": str(s.python),
        "CommandLine": "python -m worker.main --stream local:other --group local-workers",
    }
    assert launcher.owned_processes(s, [row]) == []


def test_worker_with_other_concurrency_and_reordered_flags_is_reused(launcher):
    s = launcher.Service(
        "worker",
        Path("C:/web/backend"),
        Path("C:/web/backend/.venv/Scripts/python.exe"),
        (
            "-m",
            "worker.main",
            "--stream",
            "local:one",
            "--group",
            "local-workers",
            "--concurrency",
            "4",
        ),
    )
    row = {
        "ProcessId": 1,
        "ParentProcessId": 0,
        "ExecutablePath": str(s.python),
        "CommandLine": (
            "python -m worker.main --concurrency 8 --group local-workers --stream local:one"
        ),
    }
    assert launcher.owned_processes(s, [row]) == [row]


def test_restart_checks_port_owner_before_stopping(launcher, monkeypatch):
    manager = launcher.Manager(Path.cwd())
    s = service(launcher)
    monkeypatch.setattr(manager, "processes", lambda: [])
    monkeypatch.setattr(manager, "listener_pids", lambda _: [9876])
    monkeypatch.setattr(manager, "run", lambda _: pytest.fail("must not stop another process"))
    with pytest.raises(launcher.StartupError, match="unrecognized"):
        manager.restart_api(s)


def test_environment_file_values_are_literal_and_not_printed(launcher, tmp_path):
    path = tmp_path / ".env"
    path.write_text('VIDEO_AGENT_DB_PASSWORD="$(write-host SECRET)"\n', encoding="utf-8")
    assert launcher.literal_env(path)["VIDEO_AGENT_DB_PASSWORD"] == "$(write-host SECRET)"


def test_parallel_launchers_cannot_start_duplicate_workers(launcher, tmp_path):
    with launcher.startup_lock(tmp_path):
        with pytest.raises(launcher.StartupError, match="startup"):
            with launcher.startup_lock(tmp_path):
                pytest.fail("second launcher must not enter")
    # The next normal launch must work after the first releases its lock.
    with launcher.startup_lock(tmp_path):
        pass


def test_busy_worker_with_live_task_lease_is_healthy(launcher, monkeypatch):
    manager = launcher.Manager(Path.cwd())
    s = service(launcher)
    manager.redis = type(
        "Redis",
        (),
        {
            "xinfo_consumers": lambda *a: [{"name": "worker:0", "idle": 60000}],
        },
    )()
    monkeypatch.setattr(
        manager,
        "processes",
        lambda: [
            {
                "ProcessId": 1,
                "ParentProcessId": 0,
                "ExecutablePath": str(s.python),
                "CommandLine": "python -m uvicorn app.main:application --port 18000",
            }
        ],
    )
    monkeypatch.setattr(manager, "worker_busy", lambda names: names == ["worker:0"])
    assert manager.worker_ready(s)


def test_monitor_recovers_after_one_failed_worker_probe(launcher, monkeypatch, tmp_path, capsys):
    manager = launcher.Manager(tmp_path)
    worker = launcher.Service("worker", tmp_path, tmp_path / "python.exe", ("-m", "worker.main"))
    checks = iter([False, True])
    monkeypatch.setattr(manager, "worker_ready", lambda _: next(checks))
    sleeps = iter([None, None])

    def sleep(_):
        if next(sleeps, "stop") == "stop":
            raise KeyboardInterrupt

    monkeypatch.setattr(launcher.time, "sleep", sleep)
    with pytest.raises(KeyboardInterrupt):
        manager.monitor([worker])
    output = capsys.readouterr().out
    assert "[WARN] worker" in output
    assert "[RECOVERED] worker" in output
    log = (manager.log_root / "launcher.log").read_text(encoding="utf-8")
    assert "[WARN] worker" in log and "[RECOVERED] worker" in log


def test_monitor_reports_persistent_failure_with_service_and_log(launcher, monkeypatch, tmp_path):
    manager = launcher.Manager(tmp_path)
    worker = launcher.Service("worker", tmp_path, tmp_path / "python.exe", ("-m", "worker.main"))
    calls = []

    def unhealthy(_):
        calls.append(1)
        return False

    monkeypatch.setattr(manager, "worker_ready", unhealthy)
    monkeypatch.setattr(launcher.time, "sleep", lambda _: None)
    with pytest.raises(launcher.StartupError, match="worker.*3 consecutive"):
        manager.monitor([worker])
    assert len(calls) == 3
    assert "[FAILED] worker" in (manager.log_root / "launcher.log").read_text(encoding="utf-8")


def test_monitor_failure_count_resets_on_recovery(launcher, monkeypatch, tmp_path):
    manager = launcher.Manager(tmp_path)
    worker = launcher.Service("worker", tmp_path, tmp_path / "python.exe", ("-m", "worker.main"))
    checks = iter([False, False, True, False, False, False])
    calls = []

    def ready(_):
        calls.append(1)
        return next(checks)

    monkeypatch.setattr(manager, "worker_ready", ready)
    monkeypatch.setattr(launcher.time, "sleep", lambda _: None)
    with pytest.raises(launcher.StartupError, match="worker.*3 consecutive"):
        manager.monitor([worker])
    assert len(calls) == 6
