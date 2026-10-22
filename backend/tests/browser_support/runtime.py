"""TEST_ONLY API/mock/Worker process with loopback token-protected control."""

import argparse
import hashlib
import ipaddress
import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, RLock, Thread
from uuid import uuid4

from redis import Redis
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


def validate_environment():
    if os.getenv("APP_MODE") != "mock" or os.getenv("APP_TEST_ONLY") != "true":
        raise ValueError("Browser harness requires APP_MODE=mock and APP_TEST_ONLY=true")
    database = os.environ.get("TEST_DATABASE_URL", "")
    url = make_url(database) if database else None
    if (
        not url
        or url.drivername != "mysql+pymysql"
        or url.username != "ecommerce_test"
        or (
            url.database not in ("ecommerce_ai_test", "ecommerce_ai_test_t07_20261011")
            or url.host not in ("127.0.0.1", "localhost")
        )
    ):
        raise ValueError("Only the explicit local ecommerce_test database is allowed")
    redis = os.environ.get("TEST_REDIS_URL", "")
    from urllib.parse import urlparse

    parsed = urlparse(redis)
    if (
        parsed.scheme != "redis"
        or parsed.hostname not in ("127.0.0.1", "localhost")
        or (parsed.path != "/15")
    ):
        raise ValueError("Only explicit local Redis database 15 is allowed")
    return database, redis


def certificate(root):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TEST_ONLY localhost")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=2))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    (root / "key.pem").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    (root / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))


class Runtime:
    def __init__(self, root, api_port, origin):
        database, redis_url = validate_environment()
        from app.agents.mock_server import BoundedServer
        from app.agents.registry import AgentRegistry
        from app.config import Settings
        from app.db import create_db_engine
        from app.main import create_app
        from app.storage.local_store import LocalStore
        from tests.browser_support.seed import seed
        from worker.main import compose_worker

        self.root, self.run_id = root, uuid4().hex
        self.prefix = "browser_" + self.run_id[:12] + "_"
        self.token = secrets.token_urlsafe(32)
        self.lock, self.stop = RLock(), Event()
        self.owned, self.paused, self.failure = [], set(), None
        root.mkdir(parents=True, exist_ok=True)
        storage = (root / "storage").resolve()
        storage.mkdir(exist_ok=True)
        settings = Settings(
            mode="mock",
            test_only=True,
            database_url=database,
            redis_url=redis_url,
            storage_root=storage,
            storage_persistent=True,
            auth_origins=[origin],
        )
        self.engine = create_db_engine(settings)
        self.factory = sessionmaker(self.engine, expire_on_commit=False)
        from app.db import database_schema_current

        with self.engine.connect() as c:
            if not database_schema_current(c):
                raise ValueError("Browser harness requires the current bundled database schema")
        self.redis = Redis.from_url(redis_url, socket_timeout=3, socket_connect_timeout=3)
        self.redis.ping()
        self.mock = BoundedServer(("127.0.0.1", 0))
        self.mock_thread = Thread(target=self.mock.serve_forever, daemon=True)
        self.mock_thread.start()
        catalog = seed(
            self.factory, settings, self.prefix, f"http://127.0.0.1:{self.mock.server_port}"
        )
        self.agents = catalog["agents"]
        self.app = create_app(settings)
        self.app.state.auth_rate_prefix = "TEST_ONLY:" + self.run_id + ":auth:"
        self.save_failures = set()
        faults = self.save_failures

        class ScopedStore(LocalStore):
            def commit(self, staged):
                if staged.identity and staged.identity.get("task_id") in faults:
                    raise OSError("TEST_ONLY scoped disk rename failure")
                return super().commit(staged)

        self.store = ScopedStore(storage)
        self.stream = "TEST_ONLY:" + self.run_id + ":tasks"
        self.worker = compose_worker(
            self.factory,
            self.redis,
            self.stream,
            self.run_id,
            self.run_id,
            registry=AgentRegistry(mode="mock", test_only=True),
            task_ids=self.owned,
            store=self.store,
        )
        self.metadata = dict(
            test_only=True,
            mode="mock",
            run_id=self.run_id,
            account_prefix=self.prefix,
            api_port=api_port,
            origin=origin,
            stream=self.stream,
            group=self.run_id,
            **catalog,
        )

    def checked_task(self, session, task_id):
        from app.auth.models import User
        from app.tasks.models import GenerationTask

        task = session.get(GenerationTask, task_id)
        user = session.get(User, task.user_id) if task else None
        if (
            not task
            or not user
            or not user.account_normalized.startswith(self.prefix)
            or (task.agent_id not in self.agents.values())
        ):
            raise ValueError("Task outside this run")
        return task

    def register(self, task_id, scenario="normal", paused=False):
        with self.lock, self.factory() as s:
            task = self.checked_task(s, task_id)
            kind = next(k for k, v in self.agents.items() if v == task.agent_id)
            if scenario == "save_failure":
                self.save_failures.add(task_id)
                scenario = "normal"
            if task_id not in self.owned:
                with self.mock.simulator.lock:
                    self.mock.simulator.configure(
                        kind, task.external_submission_id, {"scenario": scenario}
                    )
                self.owned.append(task_id)
            if paused:
                self.paused.add(task_id)
        return self.inspect(task_id)

    def inspect(self, task_id):
        from app.ledger.models import CreditAccount, CreditLedger
        from app.storage.models import File
        from app.works.models import Work

        with self.lock, self.factory() as s:
            task = self.checked_task(s, task_id)
            kind = next(k for k, v in self.agents.items() if v == task.agent_id)
            account = s.get(CreditAccount, task.user_id)
            ledger = s.scalars(
                select(CreditLedger).where(CreditLedger.user_id == task.user_id)
            ).all()
            works = s.scalars(select(Work).where(Work.task_id == task_id)).all()
            files = s.scalars(select(File).where(File.user_id == task.user_id)).all()
            disk = []
            for file in files:
                path = self.store._path(file.internal_path, ".blob")
                data = path.read_bytes() if path.exists() else b""
                disk.append(
                    dict(
                        file_id=file.id,
                        bytes=len(data),
                        sha256=hashlib.sha256(data).hexdigest(),
                        stored_sha256=file.sha256,
                        matches=bool(data) and hashlib.sha256(data).hexdigest() == file.sha256,
                    )
                )
            with self.mock.simulator.lock:
                row = self.mock.simulator.records.get((kind, task.external_submission_id))
                calls = dict(row["calls"]) if row else {}
            result = dict(
                task_id=task.id,
                user_id=task.user_id,
                state=task.state,
                settlement_state=task.settlement_state,
                external_submission_id=task.external_submission_id,
                work_ids=[w.id for w in works],
                disk=disk,
                calls=calls,
                balances={k: getattr(account, k) for k in ("available", "frozen", "consumed")},
                ledger=[
                    dict(
                        id=r.id,
                        kind=r.kind,
                        task_id=r.task_id,
                        amount=r.amount,
                        before=r.balances_before,
                        after=r.balances_after,
                    )
                    for r in ledger
                ],
            )
            (self.root / (task_id + ".json")).write_text(
                json.dumps(result, indent=2), encoding="utf8"
            )
            return result

    def drive(self, task_id):
        """Wake only a registered original task through the production outbox/consumer."""
        from app.dispatch.outbox import rearm_outbox
        from app.dispatch.recovery import automatic_recovery_blocked, recovery_action
        from app.tasks.models import GenerationTask

        with self.lock:
            if task_id not in self.owned:
                raise ValueError("Task outside this run")
            with self.factory() as session, session.begin():
                self.checked_task(session, task_id)
                task = session.scalar(
                    select(GenerationTask).where(GenerationTask.id == task_id)
                    .with_for_update().execution_options(populate_existing=True)
                )
                action = recovery_action(task)
                fields = None
                if action is not None and not automatic_recovery_blocked(task):
                    row = rearm_outbox(
                        session, task_id, "save" if action == "save_original" else "recover",
                    )
                    fields = dict(
                        event_id=row.event_id, task_id=task_id,
                        state_version=str(row.state_version),
                        dispatch_generation=str(row.dispatch_generation),
                    )
            if fields is None:
                return self.inspect(task_id)
            outcome = self.worker.consumer.process_message(fields)
            if outcome not in {"handled", "unhandled"}:
                raise RuntimeError("Original task handler did not complete")
            return self.inspect(task_id)

    def scenario(self, task_id, scenario):
        """Change simulated network availability, preserving identity and call counters."""
        from app.agents.mock_server import SCENARIOS

        if scenario not in SCENARIOS | {"save_failure"}:
            raise ValueError("Unsupported TEST_ONLY scenario")
        with self.lock, self.factory() as session:
            if task_id not in self.owned:
                raise ValueError("Task outside this run")
            task = self.checked_task(session, task_id)
            kind = next(k for k, v in self.agents.items() if v == task.agent_id)
            with self.mock.simulator.lock:
                if scenario == "save_failure":
                    self.save_failures.add(task_id)
                    scenario = "normal"
                else:
                    self.save_failures.discard(task_id)
                self.mock.simulator.records[kind, task.external_submission_id]["scenario"] = (
                    scenario
                )
        return self.inspect(task_id)

    def notify(self, task_id, failure=False):
        """Emit fixed TEST_ONLY signed upstream events through the verified callback service."""
        import hmac

        from app.agents.callbacks import CallbackService
        from app.agents.mock_server import CALLBACK_KEY, encoded
        from app.agents.registry import AgentRegistry
        from app.agents.upstream import UpstreamService

        with self.lock, self.factory() as session:
            if task_id not in self.owned:
                raise ValueError("Task outside this run")
            task = self.checked_task(session, task_id)
            kind = next(k for k, v in self.agents.items() if v == task.agent_id)
            with self.mock.simulator.lock:
                _, data = self.mock.simulator.events(kind, task.external_submission_id)
                event = data["events"][-1]
            payload = json.loads(event["raw"])
            if failure:
                payload.update(state="FAILED", result=None)
            raw = encoded(payload)
            headers = {"X-Mock-Signature": hmac.new(CALLBACK_KEY, raw, hashlib.sha256).hexdigest()}
            service = CallbackService(
                UpstreamService(self.factory, AgentRegistry(mode="mock", test_only=True))
            )
            receipts = [
                service.receive_callback(task.agent_id, task.agent_version, raw, headers).status
                for _ in range(2)
            ]
            return dict(task_id=task_id, receipts=receipts)

    def reprice(self, kind):
        """Publish a new exact version at the same TEST_ONLY 8/20/60 price."""
        from app.auth.service import AuthService
        from app.catalog.parameters import ParameterConfigUpdate, read_parameters, update_parameters

        if kind not in self.agents:
            raise ValueError("Agent outside this run")
        with self.lock, self.factory() as session, session.begin():
            auth = AuthService(session, mode="mock")
            login = auth.authenticate(self.prefix + "admin", "TEST_ONLY_browser_password")
            actor = auth.require_active_principal(login.session_token)
            previous = read_parameters(session, "mock")
            result = update_parameters(
                session,
                "mock",
                ParameterConfigUpdate(
                    expected_version=previous.version,
                    text_price=previous.text_price,
                    image_price=previous.image_price,
                    video_price=previous.video_price,
                ),
                actor.user_id,
            )
            return result.model_dump(mode="json")

    def prune(self, task_id):
        """Expire only this run's owner's event history via the real retention service."""
        from app.events.service import prune_events

        with self.lock, self.factory() as session, session.begin():
            task = self.checked_task(session, task_id)
            head = prune_events(session, task.user_id, retention_seconds=0)
            return dict(
                user_id=task.user_id, last_seq=head.last_seq, pruned_through=head.pruned_through
            )

    def tick(self):
        while not self.stop.wait(0.15):
            try:
                with self.lock:
                    allowed = [x for x in self.owned if x not in self.paused]
                    self.worker.scheduler.task_ids = allowed
                    self.worker.dispatcher.task_ids = allowed
                    if allowed:
                        self.worker.tick()
            except Exception as exc:
                self.failure = type(exc).__name__
                (self.root / "worker-error.txt").write_text(self.failure, encoding="utf8")
                self.stop.set()

    def close(self):
        self.stop.set()
        self.worker_thread.join(timeout=10)
        self.mock.shutdown()
        self.mock.server_close()
        self.mock_thread.join(timeout=3)
        # Only this run's independent stream and auth-rate keys. No database cleanup.
        keys = list(self.redis.scan_iter(match="TEST_ONLY:" + self.run_id + ":*"))
        if keys:
            self.redis.delete(*keys)
        self.redis.close()
        self.engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--api-port", type=int, default=18018)
    parser.add_argument("--origin", default="https://127.0.0.1:15173")
    args = parser.parse_args()
    validate_environment()
    runtime = Runtime(args.root.resolve(), args.api_port, args.origin)
    certificate(runtime.root)

    class Control(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            if not secrets.compare_digest(self.headers.get("Authorization", ""), runtime.token):
                self.send_error(403)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size > 8192:
                    raise ValueError("Control request too large")
                data = json.loads(self.rfile.read(size))
                if self.path == "/register":
                    result = runtime.register(**data)
                elif self.path == "/drive":
                    result = runtime.drive(data["task_id"])
                elif self.path == "/scenario":
                    result = runtime.scenario(**data)
                elif self.path == "/notify":
                    result = runtime.notify(**data)
                elif self.path == "/inspect":
                    result = runtime.inspect(data["task_id"])
                elif self.path == "/reprice":
                    result = runtime.reprice(data["kind"])
                elif self.path == "/prune":
                    result = runtime.prune(data["task_id"])
                elif self.path == "/resume":
                    with runtime.lock:
                        if data["task_id"] not in runtime.owned:
                            raise ValueError("Task outside this run")
                        runtime.paused.discard(data["task_id"])
                    result = runtime.inspect(data["task_id"])
                elif self.path == "/shutdown":
                    result = {"stopping": True}
                    server.should_exit = True
                else:
                    raise ValueError("Unknown control")
                raw = json.dumps(result).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            except Exception as exc:
                self.send_error(400, type(exc).__name__)

    control = ThreadingHTTPServer(("127.0.0.1", 0), Control)
    thread = Thread(target=control.serve_forever, daemon=True)
    thread.start()
    runtime.worker_thread = Thread(target=runtime.tick, daemon=True)
    runtime.worker_thread.start()
    import uvicorn

    server = uvicorn.Server(
        uvicorn.Config(
            runtime.app,
            host="127.0.0.1",
            port=args.api_port,
            access_log=False,
            log_level="warning",
            proxy_headers=True,
            forwarded_allow_ips="127.0.0.1",
        )
    )
    (runtime.root / "control.json").write_text(
        json.dumps(dict(url=f"http://127.0.0.1:{control.server_port}", token=runtime.token)),
        encoding="utf8",
    )
    (runtime.root / "metadata.json").write_text(
        json.dumps(runtime.metadata, indent=2), encoding="utf8"
    )
    try:
        server.run()
    finally:
        control.shutdown()
        control.server_close()
        thread.join(timeout=3)
        runtime.close()


if __name__ == "__main__":
    main()
