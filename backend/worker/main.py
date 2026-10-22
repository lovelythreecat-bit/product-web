"""Independent worker loop with trusted TEST_ONLY upstream composition.

Run from backend: python -m worker.main --stream <deployment-owned-stream>
T09-T13 compose TaskConsumer with trusted stage handlers; missing handlers remain due.
"""

import argparse
import logging
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event
from uuid import uuid4

from redis import Redis
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.agents.registry import AgentRegistry
from app.agents.upstream import UpstreamService
from app.config import load_runtime_settings
from app.db import create_db_engine
from app.dispatch.consumer import TaskConsumer
from app.dispatch.outbox import OutboxDispatcher
from app.dispatch.recovery import RecoveryScheduler
from app.operations.telemetry import stage_diagnostic

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, dispatcher, scheduler, consumer, investigations=None):
        self.dispatcher, self.scheduler, self.consumer = dispatcher, scheduler, consumer
        self.investigations = investigations

    def tick(self, *, batch_size=100):
        if self.investigations:
            self.investigations.scan(self.scheduler.task_ids)
        recovery = self.scheduler.recover_due_tasks()
        dispatch = self.dispatcher.dispatch_pending()
        consume = self.consumer.consume_once(batch_size)
        return recovery, dispatch, consume


def compose_worker(
    factory, redis, stream, group, worker_id, *, registry, task_ids=None, store=None
):
    service = UpstreamService(factory, registry)
    handlers = {
        action: service.handle
        for action in (
            "prepare_submission",
            "reconcile_submission",
            "query_original",
            "investigate",
        )
    }
    from app.investigations.service import InvestigationService
    from app.results.persistence import ResultPersistence
    from app.results.publisher import ResultPublisher

    publisher = ResultPublisher(ResultPersistence(factory, service, store))
    for action in handlers:
        handlers[action] = publisher.handle
    if store is not None:
        handlers["save_original"] = publisher.handle
    # No private persistent root means saving stays due; never claim a saved result.
    return Worker(
        OutboxDispatcher(factory, redis, stream, task_ids=task_ids),
        RecoveryScheduler(factory, task_ids=task_ids),
        TaskConsumer(factory, redis, stream, group, worker_id, handlers=handlers),
        InvestigationService(factory, upstream=service, mode=registry.mode),
    )


def run_workers(workers, stop, *, interval, once=False):
    """Independent consumers each claim one task, leaving work for other slots.

    Each slot owns its handlers; database leases still fence duplicate delivery.
    A synchronous upstream generation only occupies its own slot.
    """
    def run(worker):
        while not stop.is_set():
            try:
                recovered, dispatched, consumed = worker.tick(batch_size=1)
                logger.info(
                    "recovered=%s dispatched=%s dispatch_failed=%s handled=%s "
                    "unhandled=%s consume_failed=%s",
                    len(recovered.scheduled), dispatched.dispatched, dispatched.failed,
                    consumed.handled, consumed.unhandled, consumed.failed,
                )
            except SQLAlchemyError as error:
                # SQLAlchemy exception text can include SQL, input and credentials.
                # Retain only the exception class and the driver's numeric code.
                details = getattr(getattr(error, "orig", None), "args", ())
                code = details[0] if details and type(details[0]) is int else "unknown"
                logger.error(
                    "worker_database_unavailable error_type=%s database_code=%s",
                    type(error).__name__, code,
                )
                if once:
                    return 1
            except Exception as error:
                # A failed maintenance/stage operation must not terminate healthy
                # slots or leak adapter/SQL/customer details via a traceback.
                stage_diagnostic(stage="worker", error=error,
                                 code="STAGE_EXCEPTION", outcome="error")
                if once:
                    return 1
            if once:
                return 0
            stop.wait(interval)
        return 0

    with ThreadPoolExecutor(max_workers=len(workers), thread_name_prefix="generation") as pool:
        futures = [pool.submit(run, worker) for worker in workers]
        try:
            return max(future.result() for future in as_completed(futures))
        except BaseException:
            stop.set()
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stream", required=True)
    parser.add_argument("--group", default="generation-workers")
    parser.add_argument("--worker-id", default=str(uuid4()))
    parser.add_argument("--interval", type=float, default=1)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    if args.interval <= 0 or not args.stream or not args.group:
        parser.error("interval, stream and group must be valid")
    if not 1 <= args.concurrency <= 32:
        parser.error("concurrency must be between 1 and 32")
    settings = load_runtime_settings()
    if (settings.storage_root is not None
            and (settings.storage_root / ".restore-isolated.json").exists()):
        parser.error("Restored storage remains isolated; worker startup refused")
    if settings.database_url is None or settings.redis_url is None:
        parser.error("APP_DATABASE_URL and APP_REDIS_URL are required")
    engine = create_db_engine(settings)
    redis = Redis.from_url(
        settings.redis_url.get_secret_value(), socket_timeout=3, socket_connect_timeout=3
    )
    factory = sessionmaker(engine, expire_on_commit=False)
    from app.storage.local_store import LocalStore

    store = (
        LocalStore(settings.storage_root)
        if settings.storage_persistent and settings.storage_root is not None
        else None
    )
    workers = [compose_worker(
        factory,
        redis,
        args.stream,
        args.group,
        f"{args.worker_id}:{slot}",
        registry=AgentRegistry.from_settings(settings, session_factory=factory, store=store),
        store=store,
    ) for slot in range(args.concurrency)]
    stop = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    logging.basicConfig(level=logging.INFO)
    logger.info("worker_started concurrency=%s", args.concurrency)
    try:
        return run_workers(workers, stop, interval=args.interval, once=args.once)
    finally:
        redis.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
