"""Database slots shared by every worker, without locks spanning upstream I/O."""

from datetime import UTC
from hashlib import sha256
from urllib.parse import urlsplit
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert

from app.agents.models import UpstreamExecutionPool
from app.dispatch.recovery import database_now


def execution_scope(protocol, base_url):
    parts = urlsplit(base_url)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    origin = f"{parts.scheme.lower()}://{parts.hostname.lower()}:{port}"
    # Intentionally shared across model IDs and keys: rotated keys may belong to
    # the same upstream caller. Neither credentials nor customer input are stored.
    return sha256((protocol + ":" + origin).encode()).hexdigest()


def text_scope(base_url):
    return execution_scope("text-agent-v1", base_url)


class TextExecutionPool:
    def __init__(self, factory, limit):
        self.factory, self.limit = factory, limit

    def acquire(self, scope, *, seconds=660):
        token = uuid4().hex
        with self.factory() as session, session.begin():
            statement = insert(UpstreamExecutionPool).values(scope_key=scope, holders={})
            # IGNORE takes shared duplicate-key locks, then simultaneous FOR UPDATE
            # upgrades deadlock. A no-op upsert takes the exclusive row lock directly.
            session.execute(statement.on_duplicate_key_update(
                scope_key=statement.inserted.scope_key,
            ))
            row = session.scalar(select(UpstreamExecutionPool).where(
                UpstreamExecutionPool.scope_key == scope,
            ).with_for_update())
            now = database_now(session).replace(tzinfo=UTC).timestamp()
            holders = {k: v for k, v in row.holders.items() if v > now}
            if len(holders) >= self.limit:
                row.holders = holders
                return None
            holders[token] = now + seconds
            row.holders = holders
        return token

    def release(self, scope, token):
        with self.factory() as session, session.begin():
            row = session.scalar(select(UpstreamExecutionPool).where(
                UpstreamExecutionPool.scope_key == scope,
            ).with_for_update())
            if row is not None:
                row.holders = {k: v for k, v in row.holders.items() if k != token}


class MediaExecutionPool(TextExecutionPool):
    """Slots belong to durable async tasks, not short-lived HTTP requests.

    Uncertain jobs never expire into permission to over-submit. Terminal tasks
    release their slots when the next waiter checks the database. A video plan
    waiting for the user consumes no execution slot; an explicit confirmation
    keeps its acquired slot even while its HTTP response is still outstanding.
    """

    def acquire(self, scope, task_id, *, phase="initial", lease=None,
                protocol=None, base_url=None, command_key=None):
        from app.agents.media_execution import MediaExecution
        from app.dispatch.consumer import lease_matches
        from app.dispatch.recovery import TERMINAL_STATES
        from app.tasks.models import GenerationTask, TaskSnapshot
        from app.tasks.state_machine import TransitionError

        with self.factory() as session, session.begin():
            statement = insert(UpstreamExecutionPool).values(scope_key=scope, holders={})
            session.execute(statement.on_duplicate_key_update(scope_key=statement.inserted.scope_key))
            row = session.scalar(select(UpstreamExecutionPool).where(
                UpstreamExecutionPool.scope_key == scope,
            ).with_for_update())
            if lease is not None and not lease_matches(
                session.get(GenerationTask, task_id), lease, database_now(session),
            ):
                raise TransitionError("LEASE_LOST")
            original = dict(row.holders)
            if protocol is not None:
                if protocol not in {"image-agent-v1", "video-agent-v1"} or (
                    execution_scope(protocol, base_url) != scope
                ):
                    raise ValueError("Invalid media capacity scope")
                # Adopt tasks accepted before deployment, including uncertain POSTs.
                # Frozen routing binds every model/config/key to the same service pool.
                existing = session.execute(select(GenerationTask, TaskSnapshot).join(
                    TaskSnapshot, TaskSnapshot.task_id == GenerationTask.id,
                ).where(GenerationTask.state.not_in(
                    TERMINAL_STATES | {"SUBMITTED", "QUEUED"}),
                    TaskSnapshot.routing_snapshot["protocol_version"].as_string() == protocol,
                )).all()
                for task, snapshot in existing:
                    origin = (snapshot.routing_snapshot or {}).get("base_url")
                    if origin and execution_scope(protocol, origin) == scope:
                        state = session.get(MediaExecution, task.id)
                        confirm = (state is not None and state.kind == "video" and (
                            state.state.get("generation_id")
                            or state.state.get("confirmation_intent")
                        ))
                        original.setdefault(task.id, {"phase": "confirm" if confirm else "initial"})
            holders = {}
            if original:
                tasks = {task.id: task for task in session.scalars(select(GenerationTask).where(
                    GenerationTask.id.in_(original),
                ))}
                states = {item.task_id: item for item in session.scalars(
                    select(MediaExecution).where(MediaExecution.task_id.in_(original)),
                )}
                for owner, held in original.items():
                    task, state = tasks.get(owner), states.get(owner)
                    if task is None or task.state in TERMINAL_STATES:
                        continue
                    initial = held.get("phase") == "initial"
                    input_applied = (held.get("phase") == "inputs" and state is not None
                                     and state.state.get("input_intent_applied") is True
                                     and state.state.get("input_intent", {}).get("idempotency_key")
                                     == held.get("command_key"))
                    revision_applied = (held.get("phase") == "revise" and state is not None
                                        and state.state.get("revision_intent_applied") is True
                                        and state.state.get("revision_intent", {}).get(
                                            "idempotency_key")
                                        == held.get("command_key"))
                    if (state is not None and state.kind == "video"
                            and (initial or input_applied or revision_applied)
                            and state.state.get("status") in {
                                "awaiting_input", "awaiting_confirmation",
                            } and not state.state.get("generation_id")
                            and not state.state.get("confirmation_intent")
                            and (not state.state.get("input_intent")
                                 or state.state.get("input_intent_applied") is True)
                            and (not state.state.get("revision_intent")
                                 or state.state.get("revision_intent_applied") is True)):
                        continue
                    holders[owner] = held
            if task_id in holders:
                if phase in {"confirm", "inputs", "revise"}:
                    holders[task_id] = dict(holders[task_id], phase=phase)
                if command_key is not None:
                    holders[task_id] = dict(holders[task_id], command_key=command_key)
                if lease is not None:
                    holders[task_id] = dict(holders[task_id], fencing_token=lease.fencing_token)
                row.holders = holders
                return task_id
            if len(holders) >= self.limit:
                row.holders = holders
                return None
            holders[task_id] = {"phase": phase,
                                "command_key": command_key,
                                "fencing_token": lease.fencing_token if lease else None}
            row.holders = holders
            return task_id

    def release(self, scope, task_id, *, lease=None):
        from app.dispatch.consumer import lease_matches
        from app.tasks.models import GenerationTask

        with self.factory() as session, session.begin():
            row = session.scalar(select(UpstreamExecutionPool).where(
                UpstreamExecutionPool.scope_key == scope,
            ).with_for_update())
            if row is None:
                return False
            if lease is not None and (
                not lease_matches(session.get(GenerationTask, task_id),
                                  lease, database_now(session))
                or row.holders.get(task_id, {}).get("fencing_token") != lease.fencing_token
            ):
                return False
            row.holders = {k: v for k, v in row.holders.items() if k != task_id}
            return True
