"""Start the existing Windows local backend stack without provisioning or migrations.

Business credentials stay in their original configuration files. This launcher only
issues health probes; starting a Worker resumes already accepted business tasks.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit


class StartupError(Exception):
    pass


@contextmanager
def startup_lock(root):
    """Serialize check-and-start across double-clicks, without a stale PID lock."""
    import msvcrt

    directory = Path(root) / ".local-data" / "runtime"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "startup.lock").open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise StartupError(
                "Another local startup is in progress; wait for its result"
            ) from None
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


@dataclass
class Service:
    name: str
    root: Path
    python: Path
    args: tuple[str, ...]
    health: str | None = None
    env: dict[str, str] = field(default_factory=dict, repr=False)


def literal_env(path):
    from dotenv import dotenv_values

    if not path.is_file():
        raise StartupError(f"Missing configuration file: {path}")
    return {
        k: v
        for k, v in dotenv_values(path, interpolate=False, encoding="utf-8-sig").items()
        if v is not None
    }


def command_tokens(command):
    # CommandLineToArgvW handles quoted Unicode paths as Windows actually does.
    count = ctypes.c_int()
    parse = ctypes.windll.shell32.CommandLineToArgvW
    parse.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    parse.restype = ctypes.POINTER(ctypes.c_wchar_p)
    result = parse(command, ctypes.byref(count))
    if not result:
        return []
    try:
        return [result[i] for i in range(count.value)]
    finally:
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes = [ctypes.c_void_p]
        free(result)


def owned_processes(service, rows):
    def matches(row):
        tokens = command_tokens(row.get("CommandLine") or "")
        args = list(service.args)
        if service.name == "text-api":
            console = os.path.normcase(str(service.python.parent / "ecommerce-copy-api.exe"))
            if any(os.path.normcase(t) == console for t in tokens) and tokens[-1:] == ["serve"]:
                return True
        # Match module/ASGI identity and endpoint/queue, independent of flag order.
        identity_length = 3 if args[:2] == ["-m", "uvicorn"] else 2
        identity = args[:identity_length]
        if not any(tokens[i : i + len(identity)] == identity for i in range(len(tokens))):
            return False
        for flag in ("--port", "--host", "--stream", "--group"):
            if flag in args:
                expected = args[args.index(flag) + 1]
                if not any(
                    tokens[i : i + 2] == [flag, expected] or tokens[i] == flag + "=" + expected
                    for i in range(len(tokens))
                ):
                    return False
        return True

    python = os.path.normcase(os.path.abspath(service.python))
    parents = {
        r["ProcessId"]
        for r in rows
        if r.get("ExecutablePath")
        and os.path.normcase(os.path.abspath(r["ExecutablePath"])) == python
        and matches(r)
    }
    return [
        r
        for r in rows
        if matches(r) and (r["ProcessId"] in parents or r.get("ParentProcessId") in parents)
    ]


def windows_environment():
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    # A long-running desktop app can retain PATH from before FFmpeg was installed.
    import winreg

    paths = [env.get("PATH", "")]
    for hive, key in (
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ),
        (winreg.HKEY_CURRENT_USER, r"Environment"),
    ):
        try:
            with winreg.OpenKey(hive, key) as handle:
                paths.append(os.path.expandvars(winreg.QueryValueEx(handle, "Path")[0]))
        except OSError:
            pass
    env["PATH"] = os.pathsep.join(paths)
    return env


class Manager:
    def __init__(
        self, root, *, port=18000, stream=None, group="local-generation-workers", concurrency=6
    ):
        self.root = Path(root).resolve()
        self.port, self.stream, self.group, self.concurrency = port, stream, group, concurrency
        self.settings = None
        self.redis = None
        self.started = []
        self.env = windows_environment()
        self.log_root = self.root / ".local-data" / "runtime"
        self.restart_requested = False

    def run(self, args, *, timeout=20):
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=self.env,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise StartupError(
                f"Cannot run {Path(args[0]).name}; check installation and permissions"
            ) from None
        if result.returncode:
            # Never print raw external-tool errors: they may include connection data.
            raise StartupError(
                f"{Path(args[0]).name} failed; check the local service/WSL configuration"
            )
        return result.stdout.strip().lstrip("\ufeff")

    def processes(self):
        script = (
            "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); "
            "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" -ErrorAction Stop | "
            "Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine) | "
            "ConvertTo-Json -Compress"
        )
        raw = self.run(["powershell.exe", "-NoProfile", "-Command", script])
        rows = json.loads(raw or "[]")
        return rows if isinstance(rows, list) else [rows]

    def listener_pids(self, service):
        port = urlsplit(service.health).port
        script = (
            "@(Get-NetTCPConnection -State Listen -ErrorAction Stop | "
            f"Where-Object LocalPort -eq {int(port)} | "
            "Select-Object -ExpandProperty OwningProcess -Unique) | ConvertTo-Json -Compress"
        )
        value = json.loads(self.run(["powershell.exe", "-NoProfile", "-Command", script]) or "[]")
        return value if isinstance(value, list) else [value]

    def restart_api(self, service):
        owned = owned_processes(service, self.processes())
        ids = {row["ProcessId"] for row in owned}
        if any(pid not in ids for pid in self.listener_pids(service)):
            raise StartupError("Web API port belongs to an unrecognized process; nothing stopped")
        # Child first; re-read ownership immediately before each stop.
        for row in reversed(owned):
            current = owned_processes(service, self.processes())
            if any(r["ProcessId"] == row["ProcessId"] for r in current):
                self.run(
                    [
                        "powershell.exe",
                        "-NoProfile",
                        "-Command",
                        f"Stop-Process -Id {int(row['ProcessId'])} -ErrorAction Stop",
                    ]
                )
        deadline = time.monotonic() + 10
        while self.port_open(service):
            if time.monotonic() >= deadline:
                raise StartupError("Web API port was not released; startup cancelled")
            time.sleep(0.25)

    def load_settings(self):
        if self.settings is None:
            sys.path.insert(0, str(self.root / "backend"))
            from app.config import load_runtime_settings

            self.settings = load_runtime_settings()
        return self.settings

    @staticmethod
    def tcp(host, port):
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            return False

    def port_open(self, service):
        if not service.health:
            return False
        url = urlsplit(service.health)
        return self.tcp(url.hostname, url.port or 80)

    def probe(self, service):
        if not service.health:
            return bool(owned_processes(service, self.processes()))
        import httpx

        try:
            response = httpx.get(service.health, timeout=3, trust_env=False, follow_redirects=False)
            return response.status_code == 200 and isinstance(response.json(), dict)
        except (httpx.HTTPError, ValueError):
            return False

    def launch(self, service):
        if not service.python.is_file():
            raise StartupError(f"{service.name}: Python environment missing: {service.python}")
        self.log_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        log = self.log_root / f"{service.name}-{stamp}.log"
        with log.open("ab", buffering=0) as handle:
            process = subprocess.Popen(
                [str(service.python), *service.args],
                cwd=service.root,
                env={**self.env, **service.env},
                stdin=subprocess.DEVNULL,
                stdout=handle,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        self.started.append((service, process, log))
        print(f"[START] {service.name}: PID {process.pid}; log: {log}", flush=True)
        return process

    def wait_ready(self, service, process, *, timeout=45):
        deadline = time.monotonic() + timeout
        while True:
            if process is not None and process.poll() is not None:
                raise StartupError(f"{service.name} exited; inspect its runtime log")
            if self.probe(service):
                return
            if time.monotonic() >= deadline:
                raise StartupError(
                    f"{service.name} did not become ready; inspect its config and runtime log"
                )
            time.sleep(0.5)

    def ensure(self, service):
        print(f"[CHECK] {service.name}", flush=True)
        if self.probe(service):
            if service.health and not owned_processes(service, self.processes()):
                raise StartupError(
                    f"{service.name}: occupied endpoint is not owned by this project"
                )
            print(f"[REUSE] {service.name}", flush=True)
            return "reused"
        if owned_processes(service, self.processes()):
            self.wait_ready(service, None, timeout=15)
            print(f"[REUSE] {service.name}", flush=True)
            return "reused"
        if self.port_open(service):
            raise StartupError(
                f"{service.name}: port occupied by another or unhealthy service; nothing stopped"
            )
        process = self.launch(service)
        self.wait_ready(service, process)
        print(f"[READY] {service.name}", flush=True)
        return "started"

    def docker(self, service):
        # Start only the existing project's data container. Never create a new DB,
        # pull an image, reinitialize a volume or fall back to a different endpoint.
        name = f"ecommerce-ai-dev-{service}-1"
        candidates = [["docker.exe"], ["wsl.exe", "-d", "Ubuntu-24.04", "--exec", "docker"]]
        for prefix in candidates:
            try:
                labels = json.loads(
                    self.run([*prefix, "inspect", "--format", "{{json .Config.Labels}}", name])
                )
                if (
                    labels.get("com.docker.compose.project") != "ecommerce-ai-dev"
                    or labels.get("com.docker.compose.service") != service
                ):
                    continue
                self.run([*prefix, "start", name], timeout=45)
                return
            except StartupError:
                continue
        raise StartupError(
            f"{service}: existing ecommerce-ai-dev container cannot start. "
            "Start Docker/WSL and prepare infra/compose.dev.yaml; no new data instance was created"
        )

    def infrastructure(self):
        from redis import Redis
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine import make_url

        settings = self.load_settings()
        if settings.database_url is None or settings.redis_url is None:
            raise StartupError("Configure APP_DATABASE_URL and APP_REDIS_URL in backend/.env")
        db_url = make_url(settings.database_url.get_secret_value())
        redis_url = urlsplit(settings.redis_url.get_secret_value())
        for name, host, port, expected in (
            ("mysql", db_url.host, db_url.port or 3306, 13306),
            ("redis", redis_url.hostname, redis_url.port or 6379, 16379),
        ):
            if not self.tcp(host, port):
                if host in {"127.0.0.1", "localhost"} and port == expected:
                    self.docker(name)
                else:
                    raise StartupError(
                        f"{name}: configured endpoint unreachable; no alternate instance started"
                    )
                deadline = time.monotonic() + 45
                while not self.tcp(host, port):
                    if time.monotonic() > deadline:
                        raise StartupError(
                            f"{name}: container started but configured endpoint is unreachable"
                        )
                    time.sleep(1)
        engine = create_engine(
            db_url, connect_args={"connect_timeout": 3, "read_timeout": 3}, hide_parameters=True
        )
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            raise StartupError(
                "MySQL authentication/database check failed; inspect backend/.env"
            ) from None
        finally:
            engine.dispose()
        self.redis = Redis.from_url(
            settings.redis_url.get_secret_value(),
            socket_connect_timeout=3,
            socket_timeout=3,
            decode_responses=True,
        )
        try:
            self.redis.ping()
            if self.stream is None:
                # Reuse the existing deployment stream; consumer groups are metadata,
                # not evidence that any Worker process is currently alive.
                streams = []
                for key in self.redis.scan_iter(_type="stream", count=100):
                    if any(group["name"] == self.group for group in self.redis.xinfo_groups(key)):
                        streams.append(key)
                if len(streams) > 1:
                    raise StartupError("Several Worker streams exist; pass -Stream explicitly")
                self.stream = streams[0] if streams else "local:ecommerce-ai-dev:generation"
        except StartupError:
            raise
        except Exception:
            raise StartupError(
                "Redis authentication/stream check failed; inspect backend/.env"
            ) from None
        print("[READY] MySQL and Redis (configured endpoints)", flush=True)

    def services(self):
        parent = self.root.parent

        def py(root):
            return root / ".venv" / "Scripts" / "python.exe"

        text_root, image_root, video_root = (
            parent / name for name in ("textAgent", "imageAgent", "videoAgent")
        )
        configs = []
        for root, name, default_port in (
            (text_root, "api-config.local.json", 8000),
            (image_root, "server.config.json", 8000),
        ):
            try:
                config = json.loads((root / name).read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                raise StartupError(
                    f"Missing/invalid service configuration: {root / name}"
                ) from None
            host = config.get("host", "127.0.0.1")
            host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
            configs.append((config, f"http://{host}:{config.get('port', default_port)}"))
        video_env = literal_env(video_root / ".env")
        if any(not key.startswith("VIDEO_AGENT_") for key in video_env):
            raise StartupError("Video .env contains unexpected variable names")
        if not Path(video_env.get("VIDEO_AGENT_HOME", ".video-agent")).is_absolute():
            video_env["VIDEO_AGENT_HOME"] = str(
                video_root / video_env.get("VIDEO_AGENT_HOME", ".video-agent")
            )
        video_host = video_env.get("VIDEO_AGENT_API_HOST", "127.0.0.1")
        video_host = "127.0.0.1" if video_host in {"0.0.0.0", "::"} else video_host
        video_port = video_env.get("VIDEO_AGENT_API_PORT", "8000")
        video_base = f"http://{video_host}:{video_port}"
        backend = self.root / "backend"
        return [
            Service(
                "text-api",
                text_root,
                py(text_root),
                ("-m", "ecommerce_copy_api.cli", "serve"),
                configs[0][1] + "/health/ready",
            ),
            Service(
                "image-api",
                image_root,
                py(image_root),
                ("-m", "image_agent.server"),
                configs[1][1] + "/health/ready",
            ),
            Service(
                "video-worker",
                video_root,
                py(video_root),
                ("-m", "video_agent.worker_main"),
                None,
                video_env,
            ),
            Service(
                "video-api",
                video_root,
                py(video_root),
                (
                    "-m",
                    "uvicorn",
                    "api_app.app:create_app",
                    "--factory",
                    "--host",
                    video_host,
                    "--port",
                    video_port,
                ),
                video_base + "/health/ready",
                video_env,
            ),
            Service(
                "web-api",
                backend,
                py(backend),
                (
                    "-m",
                    "uvicorn",
                    "app.main:application",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(self.port),
                ),
                f"http://127.0.0.1:{self.port}/api/v1/health/ready",
            ),
            Service(
                "worker",
                backend,
                py(backend),
                (
                    "-m",
                    "worker.main",
                    "--stream",
                    self.stream or "<existing-or-local-stream>",
                    "--group",
                    self.group,
                    "--concurrency",
                    str(self.concurrency),
                ),
            ),
        ]

    def check_agent_database(self, service):
        # The three Agent repositories use the existing Windows MySQL57 service.
        # Only request its start if their explicitly configured local 3306 is down.
        from sqlalchemy.engine import make_url

        if service.name in {"text-api", "image-api"}:
            name = "api-config.local.json" if service.name == "text-api" else "server.config.json"
            config = json.loads((service.root / name).read_text(encoding="utf-8-sig"))
            url = make_url(config["database_url"])
            host, port = url.host, url.port or 3306
        elif service.name == "video-worker":
            host, port = (
                service.env.get("VIDEO_AGENT_DB_HOST", "127.0.0.1"),
                int(service.env.get("VIDEO_AGENT_DB_PORT", "3306")),
            )
        else:
            return
        if self.tcp(host, port):
            return
        if host in {"localhost", "127.0.0.1"} and port == 3306:
            self.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    "Start-Service -Name MySQL57 -ErrorAction Stop",
                ],
                timeout=30,
            )
            deadline = time.monotonic() + 20
            while not self.tcp(host, port) and time.monotonic() < deadline:
                time.sleep(0.5)
        if not self.tcp(host, port):
            raise StartupError(
                f"{service.name}: configured MySQL unreachable; check service and permissions"
            )

    def worker_ready(self, service):
        rows = owned_processes(service, self.processes())
        if not rows:
            return False
        # Redis consumer activity alone can be stale. Require an owned process too.
        try:
            consumers = self.redis.xinfo_consumers(self.stream, self.group)
            return any(c["idle"] < 15000 for c in consumers) or self.worker_busy(
                [c["name"] for c in consumers]
            )
        except Exception:
            return False

    def worker_busy(self, consumer_names):
        # Synchronous generation can occupy every slot for minutes. The Worker
        # renews its task lease during that wait; Redis idle then says nothing
        # about execution health. Verify a fresh lease for this stream's consumers.
        if not consumer_names:
            return False
        from sqlalchemy import bindparam, create_engine, text

        settings = self.load_settings()
        engine = create_engine(
            settings.database_url.get_secret_value(),
            connect_args={"connect_timeout": 3, "read_timeout": 3},
            hide_parameters=True,
        )
        try:
            query = text(
                "SELECT 1 FROM generation_tasks WHERE lease_owner IN :owners "
                "AND lease_expires_at > UTC_TIMESTAMP(6) "
                "AND state NOT IN ('SUCCEEDED','FAILED','MANUALLY_CLOSED') LIMIT 1"
            ).bindparams(bindparam("owners", expanding=True))
            with engine.connect() as connection:
                return connection.execute(query, {"owners": consumer_names}).first() is not None
        finally:
            engine.dispose()

    def start(self, *, dry_run=False):
        if dry_run:
            print("[PLAN] Check/reuse MySQL and Redis; start only existing local data services")
            for service in self.services():
                print(f"[PLAN] {service.name}: {' '.join(service.args)}")
            return []
        self.infrastructure()
        services = self.services()
        # Validate the whole plan before starting the first business process.
        for service in services:
            if not service.python.is_file():
                raise StartupError(f"{service.name}: missing Python environment: {service.python}")
        for service in services:
            self.check_agent_database(service)
            if self.restart_requested and service.name == "web-api":
                self.restart_api(service)
            self.ensure(service)
            if service.name == "worker":
                deadline = time.monotonic() + 20
                while not self.worker_ready(service):
                    if time.monotonic() >= deadline:
                        raise StartupError(
                            "Worker has no active consumer or task lease; inspect worker log"
                        )
                    time.sleep(0.5)
        # Recheck after all startup steps; no partial stack is announced as ready.
        for service in services:
            if not self.probe(service):
                raise StartupError(f"{service.name} became unhealthy during startup")
        print(
            f"[READY] Complete backend stack; API: http://127.0.0.1:{self.port}; "
            f"logs: {self.log_root}",
            flush=True,
        )
        return services

    def monitor_event(self, level, message):
        line = f"[{level}] {message}"
        print(line, flush=True)
        self.log_root.mkdir(parents=True, exist_ok=True)
        with (self.log_root / "launcher.log").open("a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now().isoformat(timespec='seconds')} {line}\n")

    def monitor(self, services):
        print(
            "Keep this window open for health monitoring. "
            "Ctrl+C stops monitoring; services keep running.",
            flush=True,
        )
        failures = {service.name: 0 for service in services}
        while True:
            time.sleep(5)
            for service in services:
                try:
                    healthy = (
                        self.worker_ready(service)
                        if service.name == "worker" else self.probe(service)
                    )
                except StartupError:
                    healthy = False
                if healthy:
                    if failures[service.name]:
                        self.monitor_event("RECOVERED", f"{service.name}: health check passed")
                    failures[service.name] = 0
                    continue
                failures[service.name] += 1
                count = failures[service.name]
                if count < 3:
                    self.monitor_event(
                        "WARN", f"{service.name}: health check failed ({count}/3); retrying"
                    )
                    continue
                message = (
                    f"{service.name} unhealthy for 3 consecutive checks; "
                    f"inspect {self.log_root / (service.name + '-*.log')}; "
                    "services have not been stopped"
                )
                self.monitor_event("FAILED", message)
                raise StartupError(message)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--port", type=int, default=18000)
    parser.add_argument("--stream")
    parser.add_argument("--group", default="local-generation-workers")
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--check", action="store_true", help="Start/check services and return, without monitoring"
    )
    parser.add_argument(
        "--restart-api",
        action="store_true",
        help="Restart only the owned Web API to load code changes",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535 or not 1 <= args.concurrency <= 32:
        parser.error("port or concurrency out of range")
    manager = Manager(
        args.root,
        port=args.port,
        stream=args.stream,
        group=args.group,
        concurrency=args.concurrency,
    )
    manager.restart_requested = args.restart_api
    try:
        if args.dry_run:
            services = manager.start(dry_run=True)
        else:
            with startup_lock(manager.root):
                services = manager.start()
        if not args.dry_run and not args.check:
            manager.monitor(services)
        return 0
    except KeyboardInterrupt:
        print("Monitoring stopped. Existing services and accepted tasks continue.", flush=True)
        return 0
    except StartupError as error:
        print(f"[FAILED] {error}", file=sys.stderr, flush=True)
        return 1
    except Exception:
        print(
            "[FAILED] Local startup failed; inspect configuration and runtime logs. "
            "Secrets are not printed.",
            file=sys.stderr,
            flush=True,
        )
        return 1
    finally:
        if manager.redis:
            manager.redis.close()


if __name__ == "__main__":
    raise SystemExit(main())
