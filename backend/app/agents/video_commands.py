"""Execute only persisted, explicitly authorized video commands through local capacity."""

from datetime import timedelta

from app.agents.execution_pool import execution_scope
from app.agents.media_execution import MediaCommand, MediaExecution, public_media_state
from app.agents.media_http import MediaServiceError
from app.dispatch.outbox import enqueue_outbox, rearm_outbox
from app.dispatch.recovery import database_now
from app.tasks.models import TaskSnapshot
from app.tasks.repository import locked_execution


def _save_command_state(session, task, execution, state):
    from app.events.service import append_durable_event

    previous = public_media_state("video", execution.state)
    execution.state = state
    execution.revision += 1
    execution.updated_at = database_now(session)
    if previous != public_media_state("video", state):
        append_durable_event(session, task.user_id, "task.updated", {
            "task_id": task.id, "state": task.state, "state_version": task.state_version,
            "media_revision": execution.revision,
        }, event_key=f"media:{task.id}:{execution.revision}")


def queue_authorized_command(session, task, execution, command_id):
    """Commit the wake-up with the user's command, before acquiring a worker lease."""
    if (execution.state.get("command_queue") or {}).get("command_id") == command_id:
        return
    due = database_now(session)
    _save_command_state(session, task, execution, dict(execution.state, command_queue={
        "command_id": command_id, "not_before": due.isoformat(),
    }))
    task.recovery_due_at = due
    rearm_outbox(session, task.id, "recover", ready_at=due)


def execute_video_command(upstream, task_id, lease, command_id):
    from app.tasks.media_routes import assert_video_command_task, recover_command_response

    with upstream.factory() as session, session.begin():
        task = locked_execution(session, task_id, lease)
        snapshot = session.get(TaskSnapshot, task_id)
        assert_video_command_task(task, snapshot, task.user_id)
        command = session.get(MediaCommand, command_id)
        execution = session.get(MediaExecution, task_id)
        if (command is None or command.task_id != task_id
                or command.operation not in {"confirm", "inputs", "revise"}):
            raise MediaServiceError(409)
        if command.response is not None:
            if (execution.state.get("command_queue") or {}).get("command_id") == command_id:
                _save_command_state(session, task, execution,
                                    dict(execution.state, command_queue=None))
                rearm_outbox(session, task_id, "recover", ready_at=database_now(session))
            return command.response
        recovered = recover_command_response(command, execution.state)
        if recovered is not None:
            _save_command_state(session, task, execution,
                                dict(execution.state, command_queue=None))
            recovered = public_media_state("video", execution.state)
            command.response = recovered
            rearm_outbox(session, task_id, "recover", ready_at=database_now(session))
            return recovered
        key = command.request_key
        operation, body = command.operation, command.request["upstream_body"]
        binding = upstream.registry.bind_task(session, task)
        waiting = execution.state.get("command_queue")
        current = database_now(session)
        if (waiting and waiting.get("command_id") == command_id
                and waiting.get("not_before", "") > current.isoformat()):
            return public_media_state("video", execution.state)
    scope = execution_scope("video-agent-v1", binding.adapter.profile.base_url)
    pool = upstream.media_pools["video-agent-v1"]
    if pool.acquire(scope, task_id, phase=operation,
                    lease=lease, command_key=key, protocol="video-agent-v1",
                    base_url=binding.adapter.profile.base_url) is None:
        with upstream.factory() as session, session.begin():
            task = locked_execution(session, task_id, lease)
            execution = session.get(MediaExecution, task_id, with_for_update=True)
            due = database_now(session) + timedelta(seconds=1)
            _save_command_state(session, task, execution, dict(execution.state, command_queue={
                "command_id": command_id, "not_before": due.isoformat(),
            }))
            task.recovery_due_at = due
            rearm_outbox(session, task_id, "recover", ready_at=due)
            return public_media_state("video", execution.state)
    try:
        action = (binding.adapter.confirm if operation == "confirm" else
                  binding.adapter.revise_plan if operation == "revise" else
                  binding.adapter.update_inputs)
        args = (body["plan_version"], key) if operation == "confirm" else (body, key)
        upstream._leased_transport(action, args, lease)
    except MediaServiceError as error:
        with upstream.factory() as session, session.begin():
            task = locked_execution(session, task_id, lease)
            execution = session.get(MediaExecution, task_id, with_for_update=True)
            state = dict(execution.state, command_queue=None)
            if error.status_code in {404, 409, 413, 422}:
                session.get(MediaCommand, command_id).response = {
                    "command_error": error.status_code,
                }
                field = {"confirm": "confirmation_intent", "revise": "revision_intent"}.get(
                    operation, "input_intent")
                if (state.get(field, {}).get("idempotency_key") == key
                        and not state.get("generation_id")):
                    state.pop(field, None)
                    if operation == "inputs":
                        state.pop("input_intent_applied", None)
                    if operation == "revise":
                        state.pop("revision_intent_applied", None)
                error.command_rejected = True
            _save_command_state(session, task, execution, state)
        if getattr(error, "command_rejected", False):
            pool.release(scope, task_id, lease=lease)
        raise
    with upstream.factory() as session, session.begin():
        task = locked_execution(session, task_id, lease)
        execution = session.get(MediaExecution, task_id, with_for_update=True)
        _save_command_state(session, task, execution, dict(execution.state, command_queue=None))
        response = public_media_state("video", execution.state)
        session.get(MediaCommand, command_id).response = response
        enqueue_outbox(session, task_id, "recover")
        return response


def resume_queued_video_command(upstream, task_id, lease):
    with upstream.factory() as session:
        from app.tasks.models import GenerationTask

        task = session.get(GenerationTask, task_id)
        if task is None or task.state != "RUNNING":
            # Reconcile a known upstream ID first. A restored binding can then
            # return INVESTIGATING to RUNNING with the normal accepted proof.
            return False
        state = session.get(MediaExecution, task_id)
        if state is None or state.kind != "video" or not state.state.get("command_queue"):
            return False
        command_id = state.state["command_queue"]["command_id"]
    execute_video_command(upstream, task_id, lease, command_id)
    with upstream.factory() as session:
        state = session.get(MediaExecution, task_id)
        return bool(state.state.get("command_queue"))
