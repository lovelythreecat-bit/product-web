"""D-09 lifecycle transactions. References are retained, never inferred expired.

Deletion locks user -> capacity -> tasks -> files, matching admission/save order.
The collector owns fresh short transactions around I/O; an unavailable file cannot
be admitted, and pending cleanup is a durable recovery obligation, not freed space.
"""

from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import or_, select

from app.audit.models import AuditEvent
from app.conversations.service import authenticate
from app.ledger.service import now
from app.policies.schemas import DeletePolicy
from app.policies.service import PolicyGateError, PolicyService
from app.results.models import ResultManifestRecord, ResultSaveItem
from app.storage.capacity import lock_capacity, locked
from app.storage.local_store import LocalStore
from app.storage.models import CapacityReservation, File, FileCleanup, FileRef
from app.tasks.models import GenerationTask, TaskSnapshot
from app.works.models import Work, WorkItem


def delete_policy(session, version, mode):
    service = PolicyService(session)
    service.require_feature("delete", mode, {"D-09": version})
    policy = DeletePolicy.model_validate(service._read("D-09", version).payload["delete"])
    if policy.execution is None:
        raise PolicyGateError()
    return policy.execution


def audit(session, actor, action, id, version, **changes):
    session.add(
        AuditEvent(
            id=str(uuid4()),
            actor_id=str(actor) if actor else None,
            action=action,
            object_id=str(id),
            reason="versioned lifecycle decision",
            changes={"policy_version": version, **changes},
            created_at=now(),
        )
    )


def task_protection(session, file, *, inflight_only):
    # Read authoritative snapshots as well as refs: absence of a ref is not deletion evidence.
    tasks = session.scalars(
        select(GenerationTask).where(GenerationTask.user_id == file.user_id).with_for_update()
    ).all()
    for task in tasks:
        snapshot = session.scalar(
            select(TaskSnapshot).where(TaskSnapshot.task_id == task.id).with_for_update(read=True)
        )
        refs = snapshot.input_snapshot.get("material_versions", []) if snapshot else []
        matched = any(
            r.get("file_id") == file.id and r.get("version") == file.version for r in refs
        )
        ref = session.scalar(
            select(FileRef.id)
            .where(
                FileRef.file_id == file.id,
                FileRef.version == file.version,
                FileRef.ref_type == "task_input",
                FileRef.ref_id == task.id,
            )
            .with_for_update()
        )
        if (matched or ref) and (
            not inflight_only or task.state not in ("SUCCEEDED", "FAILED", "MANUALLY_CLOSED")
        ):
            return True
        # Original capacity/save identities survive manual closure and credit release.
        if not inflight_only and task.capacity_reservation_id == file.reservation_id:
            return True
    return False


def retained(session, file):
    if task_protection(session, file, inflight_only=False):
        return True
    if session.scalar(select(FileRef.id).where(FileRef.file_id == file.id).with_for_update()):
        return True
    if session.scalar(select(WorkItem.id).where(WorkItem.file_id == file.id).with_for_update()):
        return True
    if session.scalar(
        select(ResultSaveItem.id)
        .where(
            or_(
                ResultSaveItem.file_id == file.id,
                ResultSaveItem.internal_path == file.internal_path,
            )
        )
        .with_for_update()
    ):
        return True
    # Manifest is authoritative even if save items have not yet appeared.
    manifests = session.scalars(
        select(ResultManifestRecord)
        .join(GenerationTask, GenerationTask.id == ResultManifestRecord.task_id)
        .where(GenerationTask.user_id == file.user_id)
        .with_for_update()
    ).all()
    for manifest in manifests:
        for item in manifest.manifest.get("items", []):
            if item.get("file_id") == file.id or item.get("internal_path") == file.internal_path:
                return True
    return False


class LifecycleService:
    def __init__(self, session, *, mode="production"):
        self.session, self.mode = session, mode

    def _owner_file(self, principal, id):
        file = self.session.scalar(
            select(File).where(File.id == str(id), File.user_id == str(principal.user_id))
        )
        if file is None:
            raise HTTPException(404)
        return file

    def _lock_and_check(self, files):
        if not files:
            return
        reservation = self.session.get(CapacityReservation, files[0].reservation_id)
        lock_capacity(self.session, files[0].user_id, reservation.pool_id)
        for file in sorted(files, key=lambda f: f.id):
            if task_protection(self.session, file, inflight_only=True):
                raise HTTPException(409)
        for file in sorted(files, key=lambda f: f.id):
            locked(self.session, File, File.id == file.id)

    def delete_material(self, principal, id, policy_version):
        authenticate(self.session, principal)
        file = self._owner_file(principal, id)
        delete_policy(self.session, policy_version, self.mode)
        self._lock_and_check([file])
        self._delete_file(principal, file, policy_version)
        self.session.flush()
        return {"id": file.id, "deleted": True, "policy_version": policy_version}

    def _delete_file(self, principal, file, version):
        if file.deleted_at is not None:
            if file.deletion_policy_version != version:
                raise HTTPException(409)
            return
        file.deleted_at, file.deletion_policy_version = now(), version
        audit(self.session, principal.user_id, "delete_material", file.id, version)

    def delete_work(self, principal, id, policy_version):
        authenticate(self.session, principal)
        work = self.session.scalar(
            select(Work).where(Work.id == str(id), Work.user_id == str(principal.user_id))
        )
        if work is None:
            raise HTTPException(404)
        delete_policy(self.session, policy_version, self.mode)
        files = self.session.scalars(
            select(File)
            .join(WorkItem, WorkItem.file_id == File.id)
            .where(WorkItem.work_id == work.id)
        ).all()
        self._lock_and_check(files)
        if work.deleted_at is not None:
            if work.deletion_policy_version != policy_version:
                raise HTTPException(409)
        else:
            work.deleted_at, work.deletion_policy_version = now(), policy_version
            for file in files:
                self._delete_file(principal, file, policy_version)
            audit(self.session, principal.user_id, "delete_work", work.id, policy_version)
        self.session.flush()
        return {"id": work.id, "deleted": True, "policy_version": policy_version}


class FileCollector:
    """Internal operator service, no public or admin-content bypass endpoint.

    Retry the same (file_id, policy_version) after any I/O/commit uncertainty.
    Cleanup never touches result identities, journals, reserved bytes or references.
    """

    def __init__(self, factory, root, *, mode="production"):
        self.factory, self.store, self.mode = factory, LocalStore(root), mode

    def collect_unreferenced_file(self, id, policy_version):
        with self.factory() as session, session.begin():
            policy = delete_policy(session, policy_version, self.mode)
            file = session.get(File, str(id))
            if file is None:
                raise HTTPException(404)
            reservation = session.get(CapacityReservation, file.reservation_id)
            lock_capacity(session, file.user_id, reservation.pool_id)
            protected = retained(session, file)
            file = locked(session, File, File.id == str(id))
            claim = locked(session, FileCleanup, FileCleanup.file_id == file.id)
            if claim and claim.policy_version != policy_version:
                raise HTTPException(409)
            if claim and claim.state == "completed":
                return "completed"
            if (
                protected
                or not policy.unreferenced_cleanup
                or file.deleted_at is None
                or file.deletion_policy_version != policy_version
                or file.deleted_at + timedelta(seconds=policy.retention_seconds) > now()
                or reservation.state != "finalized"
            ):
                return "protected"
            if claim is None:
                session.add(
                    FileCleanup(
                        file_id=file.id,
                        policy_version=policy_version,
                        state="pending",
                        created_at=now(),
                    )
                )
                file.state = "unavailable"
                audit(session, None, "file_cleanup_claim", file.id, policy_version)
            key, reservation_id = file.internal_path, file.reservation_id
        # No DB/resource locks held across filesystem operations.
        with self.store.result_guard(key):
            if any(
                self.store._path(key, suffix).exists()
                for suffix in (".journal", ".journal-tmp", ".part")
            ):
                return "protected"
            self.store.result_path(key).unlink(missing_ok=True)
            self.store._sync_directory(self.store.result_path(key).parent)
        with self.factory() as session, session.begin():
            delete_policy(session, policy_version, self.mode)
            identity = session.get(CapacityReservation, reservation_id)
            pool, account = lock_capacity(session, identity.user_id, identity.pool_id)
            file = session.get(File, str(id))
            if retained(session, file):
                raise HTTPException(409)
            file = locked(session, File, File.id == str(id))
            claim = locked(session, FileCleanup, FileCleanup.file_id == str(id))
            if claim.state == "completed":
                return "completed"
            if min(pool.actual_bytes, account.actual_bytes) < file.actual_bytes:
                raise HTTPException(409)
            pool.actual_bytes -= file.actual_bytes
            account.actual_bytes -= file.actual_bytes
            claim.state, claim.completed_at = "completed", now()
            audit(
                session,
                None,
                "file_cleanup_completed",
                file.id,
                policy_version,
                reclaimed_bytes=file.actual_bytes,
            )
        return "completed"


def history_content(session, message):
    if message.kind != "final":
        return message.content
    work = session.scalar(select(Work).where(Work.message_id == message.id))
    if work and work.deleted_at:
        return {"deleted": True, "policy_version": work.deletion_policy_version}
    files = (
        session.scalars(
            select(File)
            .join(WorkItem, WorkItem.file_id == File.id)
            .where(WorkItem.work_id == work.id)
        ).all()
        if work
        else []
    )
    deleted = next((f for f in files if f.deleted_at), None)
    if deleted:
        return {"deleted": True, "policy_version": deleted.deletion_policy_version}
    return message.content
