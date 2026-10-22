"""Task-owned media protocol state, separate from immutable admission snapshots."""

from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import JSON, BigInteger, ForeignKey, String, UniqueConstraint, select
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.catalog.schemas import content_digest
from app.db import Base

PROTOCOLS = {"image": "image-agent-v1", "video": "video-agent-v1"}
PLATFORMS = {"amazon", "taobao", "tmall", "jd", "pinduoduo", "shopee", "lazada", "shein", "temu"}
OUTPUT_TYPES = {"main_image", "detail_page", "pdd_white_background", "long_image"}


class MediaExecution(Base):
    __tablename__ = "media_executions"
    task_id: Mapped[str] = mapped_column(ForeignKey("generation_tasks.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    state: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(BigInteger, default=0)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class MediaCommand(Base):
    __tablename__ = "media_commands"
    __table_args__ = (UniqueConstraint("task_id", "operation", "request_key",
                                     name="uq_media_command_intent"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("generation_tasks.id"), index=True)
    operation: Mapped[str] = mapped_column(String(24))
    request_key: Mapped[str] = mapped_column(String(128, collation="utf8mb4_bin"))
    request_hash: Mapped[str] = mapped_column(String(64))
    request: Mapped[dict] = mapped_column(JSON)
    response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


def validate_media_input(kind, value):
    parameters = value.parameters
    if kind == "image":
        if (set(parameters) != {"platform", "output_type"}
                or parameters["platform"] not in PLATFORMS
                or parameters["output_type"] not in OUTPUT_TYPES):
            raise ValueError("Choose a supported platform and output type")
    elif kind == "video":
        if (set(parameters) != {"first_frame_file_id"}
                or not isinstance(parameters["first_frame_file_id"], str)
                or parameters["first_frame_file_id"] not in {
                    str(ref.file_id) for ref in value.material_versions
                }):
            raise ValueError("Choose a first frame from the submitted materials")
    elif parameters:
        raise ValueError("Text generation has no generation parameters")


def merge_execution_state(current, patch):
    if not isinstance(patch, dict):
        raise ValueError("Invalid media state")
    result = deepcopy(current)
    for key, value in patch.items():
        if key == "uploads":
            result.setdefault(key, {})
            for reference, upload in value.items():
                if reference in result[key] and result[key][reference] != upload:
                    raise ValueError("Original media identity cannot change")
                result[key][reference] = deepcopy(upload)
        else:
            if (key in {"request_body", "upstream_task_id", "generation_id", "artifact_id",
                        "confirmed_plan_version", "manifest"}
                    and result.get(key) is not None and result[key] != value):
                raise ValueError("Original execution identity cannot change")
            if key == "submission_started" and result.get(key) and not value:
                raise ValueError("A submission cannot be reset")
            result[key] = deepcopy(value)
    return result


def public_media_state(kind, state, *, revision=None):
    fields = {"status", "core_status", "questions", "head_plan_version", "plan",
              "generation_id", "confirmed_plan_version", "artifact_id", "stage",
              "completed_shots", "total_shots", "failure"}
    result = {"kind": kind, **{k: deepcopy(v) for k, v in state.items() if k in fields},
              **({"revision": revision} if revision is not None else {})}
    if kind == "video" and state.get("command_queue"):
        result["status"] = "queued"
    return result


class MediaTaskStore:
    def __init__(self, factory, task_id, kind, lease=None):
        self.factory, self.task_id, self.kind = factory, str(task_id), kind
        self.lease = lease

    def load(self):
        with self.factory() as session:
            row = session.get(MediaExecution, self.task_id)
            if row is None or row.kind != self.kind:
                raise LookupError("Original media execution unavailable")
            return deepcopy(row.state)

    def submission_rejection(self, scope, external):
        """A durable image POST refusal bound to the exact current wire intent."""
        state = self.load()
        marker = state.get("submission_rejection")
        if (self.kind != "image" or not isinstance(marker, dict)
                or state.get("upstream_task_id") or state.get("upload_in_flight")
                or not state.get("submission_started")
                or marker.get("attempt_id") != state.get("submission_attempt_id")
                or not isinstance(marker.get("attempt_id"), str)
                or marker.get("error_code") != "queue_full"
                or state.get("external_submission_id") != external
                or marker.get("external_submission_id") != external
                or state.get("scope") != scope or marker.get("scope") != scope
                or not isinstance(state.get("request_body"), dict)
                or marker.get("request_body_digest") != content_digest(state["request_body"])):
            return None
        return deepcopy(marker)

    def can_retry_rejected_submission(self):
        """Authorize only the fresh attempt linked to the previous durable refusal.

        The service verifies all prior receipts before creating that attempt;
        this second gate binds the adapter's consumable wire marker to its proof.
        """
        from app.agents.models import UpstreamAttempt, UpstreamEvidence
        from app.dispatch.consumer import lease_matches
        from app.dispatch.recovery import database_now
        from app.tasks.models import GenerationTask

        state = self.load()
        scope, external = state.get("scope"), state.get("external_submission_id")
        marker = self.submission_rejection(scope, external)
        if marker is None:
            return False
        with self.factory() as session:
            task = session.get(GenerationTask, self.task_id)
            if (not lease_matches(task, self.lease, database_now(session))
                    or task.upstream_id or task.external_submission_id != external):
                return False
            current = session.scalar(select(UpstreamAttempt).where(
                UpstreamAttempt.task_id == self.task_id,
            ).order_by(UpstreamAttempt.created_at.desc(), UpstreamAttempt.id.desc()).limit(1))
            if (current is None or current.fencing_token != self.lease.fencing_token
                    or current.scope != scope or not current.retry_reference):
                return False
            receipt = session.get(UpstreamEvidence, current.retry_reference)
            return bool(receipt is not None and receipt.task_id == self.task_id
                        and receipt.attempt_id != current.id and receipt.kind == "observation"
                        and receipt.payload.get("operation") == "submit"
                        and receipt.payload.get("outcome", {}).get("status") == "RATE_LIMITED"
                        and receipt.payload.get("outcome", {}).get("external_submission_id")
                        == external
                        and receipt.payload.get("transport_rejection") == marker)

    def save(self, patch):
        if self.lease is None:
            raise LookupError("A current task lease is required")
        from app.events.service import append_durable_event
        from app.tasks.repository import locked_execution

        with self.factory() as session, session.begin():
            task = locked_execution(session, self.task_id, self.lease)
            row = session.get(MediaExecution, self.task_id, with_for_update=True)
            if row is None or row.kind != self.kind:
                raise LookupError("Original media execution unavailable")
            previous = public_media_state(row.kind, row.state)
            row.state = merge_execution_state(row.state, patch)
            row.revision += 1
            row.updated_at = datetime.now(UTC).replace(tzinfo=None)
            if previous != public_media_state(row.kind, row.state):
                append_durable_event(
                    session, task.user_id, "task.updated",
                    {"task_id": task.id, "state": task.state,
                     "state_version": task.state_version, "media_revision": row.revision},
                    event_key=f"media:{task.id}:{row.revision}",
                )


def saved_media_task_id(adapter, external):
    """Recover a locally persisted accepted ID; this never queries or submits."""
    if getattr(adapter, "protocol_version", None) not in PROTOCOLS.values():
        return None
    state = adapter.load_state()
    bound_external = (state.get("external_submission_id")
                      if adapter.protocol_version == PROTOCOLS["image"]
                      else state.get("request_body", {}).get("external_request_id"))
    identity = state.get("upstream_task_id")
    return identity if bound_external == external and isinstance(identity, str) else None


def media_material_loader(factory, store, task_id, user_id):
    from app.storage.models import File, FileRef
    from app.tasks.models import TaskSnapshot

    def load():
        with factory() as session:
            snapshot = session.get(TaskSnapshot, task_id)
            if snapshot is None or snapshot.user_id != user_id:
                raise ValueError("Original task unavailable")
            refs = deepcopy(snapshot.input_snapshot["material_versions"])
            files = []
            for ref in refs:
                row = session.scalar(select(File).join(FileRef, FileRef.file_id == File.id).where(
                    File.id == str(ref["file_id"]), File.version == ref["version"],
                    File.user_id == user_id, File.state == "durable",
                    FileRef.version == ref["version"], FileRef.user_id == user_id,
                    FileRef.ref_type == "task_input", FileRef.ref_id == task_id))
                if (row is None or row.actual_bytes > 20 * 1024 * 1024
                        or row.actual_mime not in {"image/png", "image/jpeg", "image/webp"}):
                    raise ValueError("Original task material unavailable")
                files.append((ref, row.internal_path, row.actual_bytes,
                              row.sha256, row.actual_mime))
        result = []
        for ref, path, size, digest, mime in files:
            with store.read(path) as stream:
                data = stream.read(size + 1)
            if len(data) != size or sha256(data).hexdigest() != digest:
                raise ValueError("Original material integrity mismatch")
            result.append(dict(file_id=str(ref["file_id"]), version=ref["version"],
                               content=data, media_type=mime, sha256=digest))
        return result

    return load


def validate_command_key(key):
    if (not isinstance(key, str) or not 1 <= len(key) <= 128
            or any(not 33 <= ord(char) <= 126 for char in key)):
        raise ValueError("Invalid command key")


def command_digest(operation, body):
    return content_digest({"operation": operation, "body": body})


def new_execution(task_id, kind):
    return MediaExecution(task_id=task_id, kind=kind, state={}, revision=0,
                          updated_at=datetime.now(UTC).replace(tzinfo=None))


def new_command(task_id, operation, key, body):
    validate_command_key(key)
    return MediaCommand(id=str(uuid4()), task_id=task_id, operation=operation,
                        request_key=key, request_hash=command_digest(operation, body),
                        request=deepcopy(body), response=None,
                        created_at=datetime.now(UTC).replace(tzinfo=None))
