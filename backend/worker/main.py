"""Independent worker loop with trusted TEST_ONLY upstream composition.

Run from backend: python -m worker.main --stream <deployment-owned-stream>
T09-T13 compose TaskConsumer with trusted stage handlers; missing handlers remain due.
"""

import argparse
import logging
import signal
from threading import Event
from uuid import uuid4

from redis import Redis
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.agents.registry import AgentRegistry
from app.agents.upstream import UpstreamService
from app.config import Settings
from app.db import create_db_engine
from app.dispatch.consumer import TaskConsumer
from app.dispatch.outbox import OutboxDispatcher
from app.dispatch.recovery import RecoveryScheduler

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, dispatcher, scheduler, consumer):
        self.dispatcher, self.scheduler, self.consumer = dispatcher, scheduler, consumer

    def tick(self):
        recovery = self.scheduler.recover_due_tasks()
        dispatch = self.dispatcher.dispatch_pending()
        consume = self.consumer.consume_once()
        return recovery, dispatch, consume


def compose_worker(factory, redis, stream, group, worker_id, *, registry, task_ids=None):
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
    # T10 reduces callbacks and polls through service.handle. T11 owns save_original.
    return Worker(
        OutboxDispatcher(factory, redis, stream, task_ids=task_ids),
        RecoveryScheduler(factory, task_ids=task_ids),
        TaskConsumer(factory, redis, stream, group, worker_id, handlers=handlers),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stream", required=True)
    parser.add_argument("--group", default="generation-workers")
    parser.add_argument("--worker-id", default=str(uuid4()))
    parser.add_argument("--interval", type=float, default=1)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    if args.interval <= 0 or not args.stream or not args.group:
        parser.error("interval, stream and group must be valid")
    settings = Settings()
    if settings.database_url is None or settings.redis_url is None:
        parser.error("APP_DATABASE_URL and APP_REDIS_URL are required")
    engine = create_db_engine(settings)
    redis = Redis.from_url(
        settings.redis_url.get_secret_value(), socket_timeout=3, socket_connect_timeout=3
    )
    factory = sessionmaker(engine, expire_on_commit=False)
    worker = compose_worker(
        factory,
        redis,
        args.stream,
        args.group,
        args.worker_id,
        registry=AgentRegistry(mode=settings.mode, test_only=settings.test_only),
    )
    stop = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    logging.basicConfig(level=logging.INFO)
    try:
        while not stop.is_set():
            try:
                recovered, dispatched, consumed = worker.tick()
                logger.info(
                    "recovered=%s dispatched=%s dispatch_failed=%s handled=%s "
                    "unhandled=%s consume_failed=%s",
                    len(recovered.scheduled),
                    dispatched.dispatched,
                    dispatched.failed,
                    consumed.handled,
                    consumed.unhandled,
                    consumed.failed,
                )
            except SQLAlchemyError:
                # Retry on the next tick, logging no SQL, credentials, or user content.
                logger.error("worker_database_unavailable")
                if args.once:
                    return 1
            if args.once:
                break
            stop.wait(args.interval)
    finally:
        redis.close()
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
