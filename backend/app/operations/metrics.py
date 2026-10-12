"""Read-only aggregate projections using real persisted state; costs remain unavailable."""

import math

from sqlalchemy import text

THRESHOLDS = {
    "outbox_pending",
    "outbox_oldest_due_seconds",
    "investigation_overdue",
    "save_recovery",
    "save_oldest_due_seconds",
    "public_cleanup_pending",
    "disk_free_bytes_min",
    "capacity_used_ratio_max",
    "terminal_success_rate_min",
    "terminal_mean_seconds_max",
}


def validate_thresholds(values):
    if (
        not isinstance(values, dict)
        or set(values) - THRESHOLDS
        or any(
            type(value) not in (int, float) or not math.isfinite(value) or value < 0
            for value in values.values()
        )
        or any(
            values.get(key, 0) > 1
            for key in ("capacity_used_ratio_max", "terminal_success_rate_min")
        )
    ):
        raise ValueError("invalid_thresholds")


def project_metrics(session, *, free_bytes, thresholds):
    validate_thresholds(thresholds)

    def scalar(sql):
        return session.execute(text(sql)).scalar_one()

    terminal = "('SUCCEEDED','FAILED','MANUALLY_CLOSED')"
    counts = dict(
        session.execute(text("SELECT state, COUNT(*) FROM generation_tasks GROUP BY state")).all()
    )
    ended = sum(counts.get(state, 0) for state in ("SUCCEEDED", "FAILED", "MANUALLY_CLOSED"))
    metrics = {
        "task_states": counts,
        "terminal_count": ended,
        "terminal_success_rate": counts.get("SUCCEEDED", 0) / ended if ended else None,
        "terminal_mean_seconds": scalar(
            "SELECT AVG(TIMESTAMPDIFF(MICROSECOND,t.created_at,e.ended_at)/1000000) "
            "FROM generation_tasks t JOIN (SELECT task_id, MIN(created_at) ended_at "
            f"FROM task_state_events WHERE to_state IN {terminal} GROUP BY task_id) e "
            "ON e.task_id=t.id"
        ),
        "supplier_cost_status": "unavailable",
        "supplier_cost": None,
        "outbox_pending": scalar(
            "SELECT COUNT(*) FROM dispatch_outbox WHERE dispatched_at IS NULL"
        ),
        "outbox_oldest_due_seconds": scalar(
            "SELECT COALESCE(MAX(GREATEST(0,TIMESTAMPDIFF(SECOND,ready_at,UTC_TIMESTAMP(6)))),0) "
            "FROM dispatch_outbox WHERE dispatched_at IS NULL AND ready_at <= UTC_TIMESTAMP(6)"
        ),
        "investigation_overdue": scalar(
            "SELECT COUNT(*) FROM investigations WHERE status <> 'resolved' "
            "AND deadline_at <= UTC_TIMESTAMP(6)"
        ),
        "save_recovery": counts.get("SAVE_RECOVERY", 0),
        "saving": counts.get("SAVING", 0),
        "save_oldest_due_seconds": scalar(
            "SELECT COALESCE(MAX(GREATEST(0,TIMESTAMPDIFF(SECOND,recovery_due_at,"
            "UTC_TIMESTAMP(6)))),0) FROM generation_tasks WHERE state IN ('SAVING','SAVE_RECOVERY')"
        ),
        "public_cleanup_pending": scalar(
            "SELECT COUNT(*) FROM public_cases WHERE state='cleanup_pending'"
        ),
        "capacity": [
            dict(row)
            for row in session.execute(
                text("SELECT id,budget_bytes,reserved_bytes,actual_bytes FROM storage_pools")
            ).mappings()
        ],
        "disk_free_bytes": free_bytes,
    }
    for name in ("terminal_mean_seconds",):
        if metrics[name] is not None:
            metrics[name] = float(metrics[name])
    alerts = []
    for name in (
        "outbox_pending",
        "outbox_oldest_due_seconds",
        "investigation_overdue",
        "save_recovery",
        "save_oldest_due_seconds",
        "public_cleanup_pending",
    ):
        if name in thresholds and metrics[name] > thresholds[name]:
            alerts.append(name)
    if "disk_free_bytes_min" in thresholds and free_bytes < thresholds["disk_free_bytes_min"]:
        alerts.append("disk_free_bytes")
    if "capacity_used_ratio_max" in thresholds and any(
        (p["actual_bytes"] + p["reserved_bytes"]) / p["budget_bytes"]
        > thresholds["capacity_used_ratio_max"]
        for p in metrics["capacity"]
    ):
        alerts.append("capacity")
    metrics["alerts"] = alerts
    for metric, limit, minimum in (
        ("terminal_success_rate", "terminal_success_rate_min", True),
        ("terminal_mean_seconds", "terminal_mean_seconds_max", False),
    ):
        if limit in thresholds and metrics[metric] is not None:
            if (minimum and metrics[metric] < thresholds[limit]) or (
                not minimum and metrics[metric] > thresholds[limit]
            ):
                alerts.append(metric)
    metrics["thresholds_status"] = "configured" if thresholds else "unconfigured"
    metrics["window"] = "all_persisted_tasks"
    return metrics
