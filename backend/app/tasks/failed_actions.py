"""Owner choices after a verified failure; each route owns one atomic transaction.

Retries create a distinct upstream identity via normal admission. The deterministic
successor key and user lock serialize retries against releases without a new table.
"""

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.common.types import AdmissionResult, SubmitTaskRequest
from app.conversations.service import authenticate, owned_conversation
from app.dispatch.recovery import database_now
from app.events.service import append_durable_event
from app.ledger.models import CreditLedger
from app.ledger.service import LedgerError, balances, lock_task_resources
from app.storage.capacity import release_capacity
from app.tasks.admission import AdmissionService
from app.tasks.models import GenerationTask, TaskSnapshot, TaskStateEvent
from app.tasks.repository import task_view


def successor_key(task_id):
    return "failed-retry:" + str(task_id)


def release_failed_hold(session, task_id):
    """Internal only: caller already authenticated/authorized the original owner.

    FAILED is written only after the worker validates durable definite-failure
    evidence. Uncertain/running/saving tasks never enter this release path.
    """
    task, account, reservation = lock_task_resources(session, task_id)
    if task.state != "FAILED":
        raise HTTPException(409)
    if task.settlement_state == "RELEASED" and reservation.state == "released":
        return False
    if task.settlement_state != "FROZEN" or reservation.state != "frozen":
        raise LedgerError("SETTLEMENT_CONFLICT")
    snapshot = session.get(TaskSnapshot, task.id)
    amount = reservation.amount
    if (type(amount) is not int or amount != snapshot.quote["credits"]
            or amount != snapshot.price_snapshot["credits"]):
        raise LedgerError("QUOTE_MISMATCH")
    before = balances(account)
    account.available += amount
    account.frozen -= amount
    reservation.state, reservation.version = "released", reservation.version + 1
    task.settlement_state = "RELEASED"
    task.state_version += 1
    current = database_now(session)
    session.add(CreditLedger(
        id=str(uuid4()), operation_key=f"settle:{task.id}", user_id=task.user_id,
        reservation_id=reservation.id, task_id=task.id, kind="release", amount=amount,
        balances_before=before, balances_after=balances(account),
        reason="owner released verified failed task", created_at=current,
    ))
    release_capacity(session, task.capacity_reservation_id)
    session.add(TaskStateEvent(
        id=str(uuid4()), task_id=task.id, user_id=task.user_id, state_version=task.state_version,
        from_state="FAILED", to_state="FAILED", evidence={"kind": "owner_release"},
        created_at=current,
    ))
    append_durable_event(
        session, task.user_id, "task.updated",
        {"task_id": task.id, "state": task.state, "state_version": task.state_version},
        event_key=f"task:{task.id}:state:{task.state_version}",
    )
    session.flush()
    return True


class FailedTaskActions:
    def __init__(self, session, settings):
        self.session, self.settings = session, settings

    def _owned(self, principal, task_id):
        session = self.session
        # Authentication locks the user before credits/capacity/task, as admission does.
        authenticate(session, principal)
        task = session.scalar(select(GenerationTask).where(
            GenerationTask.id == str(task_id),
            GenerationTask.user_id == str(principal.user_id),
        ))
        if task is None:
            raise HTTPException(404)
        owned_conversation(session, principal.user_id, task.conversation_id)
        return task

    def _successor(self, principal, task_id):
        return self.session.scalar(select(GenerationTask).where(
            GenerationTask.user_id == str(principal.user_id),
            GenerationTask.idempotency_key == successor_key(task_id),
        ).with_for_update())

    def release(self, principal, task_id):
        task = self._owned(principal, task_id)
        if self._successor(principal, task.id) is not None:
            raise HTTPException(409)
        release_failed_hold(self.session, task.id)
        return task_view(self.session, task)

    def retry(self, principal, task_id):
        task = self._owned(principal, task_id)
        successor = self._successor(principal, task.id)
        if successor is not None:
            return AdmissionResult(task=task_view(self.session, successor), replayed=True)
        if task.state != "FAILED" or task.settlement_state != "FROZEN":
            raise HTTPException(409)
        snapshot = self.session.get(TaskSnapshot, task.id)
        price = getattr(snapshot, "price_snapshot", {})
        standard_quote = price.get("standard_quote") if isinstance(price, dict) else None
        free_regeneration = standard_quote is not None and price.get("credits") == 0
        request = SubmitTaskRequest.model_validate(dict(
            conversation_id=task.conversation_id, agent_id=task.agent_id,
            input=snapshot.input_snapshot,
            confirmed_quote=standard_quote if free_regeneration else snapshot.quote,
        ))
        # Release+normal admission share the caller transaction. Any stale quote,
        # missing material, disabled capability or capacity error rolls both back.
        release_failed_hold(self.session, task.id)
        options = {"free_regeneration": True} if free_regeneration else {}
        if isinstance(price, dict) and price.get("regeneration"):
            # A verified-failure successor reuses its accepted allowance; it must
            # neither consume another free use nor start an unrelated fresh chain.
            options["regeneration_metadata"] = price["regeneration"]
        return AdmissionService(self.session, self.settings).admit_task(
            principal, successor_key(task.id), request, **options,
        )
