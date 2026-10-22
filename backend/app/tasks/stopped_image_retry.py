"""Owner-requested verification of an image task stopped before generation.

Only a fresh, identity-bound upstream receipt can make this task retryable.
The ordinary failure reducer preserves evidence, fencing and frozen credits;
normal admission then creates the single deterministic retry successor.
"""

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from app.agents.callbacks import CallbackService
from app.agents.image import ImageAgentAdapter
from app.agents.media_execution import MediaExecution
from app.agents.registry import AgentRegistry
from app.agents.upstream import UpstreamService
from app.ledger.service import lock_task_resources
from app.storage.local_store import LocalStore
from app.tasks.failed_actions import FailedTaskActions
from app.tasks.repository import locked_execution
from app.tasks.state_machine import TransitionEvidence, transition_task


def stopped_input(task, execution):
    return (
        task.state == "INVESTIGATING" and task.settlement_state == "FROZEN"
        and task.investigation_reason == "UPSTREAM_NEEDS_INPUT"
        and execution is not None and execution.kind == "image"
        and execution.state.get("status") == "completed"
        and execution.state.get("core_status") == "needs_input"
        and task.upstream_id
        and execution.state.get("upstream_task_id") == task.upstream_id
        and execution.state.get("external_submission_id") == task.external_submission_id
    )


def prepare_stopped_image_retry(session, principal, task_id, settings):
    task_id = str(task_id)
    task = FailedTaskActions(session, settings)._owned(principal, task_id)
    if task.state != "INVESTIGATING" or task.investigation_reason != "UPSTREAM_NEEDS_INPUT":
        return  # Ordinary failed-task retry (including successor replay).
    if not stopped_input(task, session.get(MediaExecution, task_id)):
        raise HTTPException(409, "原图片任务尚不满足重试条件。")
    factory = sessionmaker(session.get_bind(), expire_on_commit=False)
    session.rollback()  # Never hold authentication/account locks over remote I/O.
    store = LocalStore(settings.storage_root) if settings.storage_persistent and settings.storage_root else None
    upstream = UpstreamService(factory, AgentRegistry.from_settings(
        settings, session_factory=factory, store=store,
    ))
    verify_stopped_image(upstream, principal, task_id, settings)


def verify_stopped_image(upstream, principal, task_id, settings):
    lease = upstream.leases.claim_task(task_id, "owner-image-retry:" + uuid4().hex)
    if lease is None:
        raise HTTPException(409, "原任务状态正在更新，请稍后重试。")
    try:
        with upstream.factory() as source, source.begin():
            FailedTaskActions(source, settings)._owned(principal, task_id)
            task = locked_execution(source, task_id, lease)
            if not stopped_input(task, source.get(MediaExecution, task_id)):
                raise HTTPException(409, "原图片任务状态已变化，请刷新后重试。")
            binding = upstream.registry.bind_task(source, task)
            if not isinstance(binding.adapter, ImageAgentAdapter):
                raise HTTPException(409)
            identity = upstream._identity(source, task, binding)
            attempt = upstream._latest(source, task_id)
            if attempt is None:
                raise HTTPException(409)
            attempt_id, original_id = attempt.id, task.upstream_id
        outcome = upstream._leased_transport(binding.adapter.query_for_owner_retry, (original_id,), lease)
        reference = upstream._observe(task_id, identity, attempt_id, "query", outcome)
        if outcome.status != "FOUND" or outcome.state != "FAILED":
            raise HTTPException(409, "尚未确认原任务已停止且未生成图片，已保留原任务和冻结积分。")
        upstream._apply_observation(task_id, lease, reference, explicit=True)
        callbacks = CallbackService(upstream)
        callbacks.reduce_pending(task_id, lease)
        failure = callbacks.pending_failure(task_id)
        if failure is None:
            raise HTTPException(409, "原任务核验尚未完成，请刷新后重试。")
        with upstream.factory() as source, source.begin():
            FailedTaskActions(source, settings)._owned(principal, task_id)
            callbacks.install_verifiers(source)
            task, _, _ = lock_task_resources(source, task_id)
            transition_task(source, task_id, task.state_version, "FAILED", TransitionEvidence(lease, failure))
            task.investigation_reason = None
    finally:
        upstream.leases.release(lease)
