"""Recover original bytes, never regenerate. All network/decoder work is outside SQL.

T12 must re-read verified_delivery in its publication transaction, lock credits
then capacity before task, and finalize the SUM once. This module neither settles
credits nor finalizes/reclaims the task reservation.
"""

import asyncio
import codecs
import io
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select

from app.agents.callbacks import CallbackService, OriginalResult
from app.agents.models import AgentEventDecision
from app.dispatch.consumer import LeaseManager
from app.dispatch.recovery import database_now
from app.ledger.service import lock_task_resources
from app.results.manifest import exact_policy, result_rule, validate_manifest
from app.results.models import ResultDeliveryRecord, ResultManifestRecord, ResultSaveItem
from app.storage.capacity import StorageError, ensure_reserved_capacity
from app.storage.download import DownloadPolicy, OriginalUnavailable
from app.storage.local_store import StagedFile
from app.storage.models import File, FileRef
from app.storage.validation import FileValidationError, validate_content
from app.tasks.models import TaskSnapshot
from app.tasks.repository import locked_execution
from app.tasks.state_machine import (
    TransitionError,
    TransitionEvidence,
    VerifiedTransition,
    transition_task,
)


@dataclass(frozen=True)
class DurableItem:
    item_key: str
    file_id: str
    file_version: str
    sha256: str
    actual_bytes: int
    media_type: str


@dataclass(frozen=True)
class DurableDelivery:
    task_id: str
    manifest_id: str
    receipt_id: str
    snapshot_digest: str
    items: tuple[DurableItem, ...]
    total_bytes: int
    warnings: tuple[str, ...] = ()


class ResultPersistence:
    def __init__(self, factory, upstream, store):
        self.factory, self.upstream, self.store = factory, upstream, store
        self.callbacks = CallbackService(upstream)
        self.leases = LeaseManager(factory)

    def _trusted(self, session, task, reference):
        decision = session.get(AgentEventDecision, reference)
        if decision is None or decision.disposition != "APPLIED":
            raise TransitionError("EVIDENCE_MISMATCH")
        row, event, binding = self.callbacks._event(session, task, reference)
        if event.state != "RESULT_READY" or row.sequence != 2:
            raise TransitionError("EVIDENCE_MISMATCH")
        manifest = validate_manifest(
            event.result, result_rule(session, task, binding), binding, event.upstream_task_id
        )
        return row, manifest, binding

    def prepare_manifest(self, task_id, outcome, *, lease):
        """Caller may pass only the internal OriginalResult; reference is re-read in SQL."""
        if not isinstance(outcome, OriginalResult) or outcome.task_id != task_id:
            raise TransitionError("EVIDENCE_MISMATCH")
        with self.factory() as session, session.begin():
            # Capacity must precede the task lock, as in admission and settlement.
            lock_task_resources(session, task_id)
            task = locked_execution(session, task_id, lease)
            if task.state not in {"SAVING", "SAVE_RECOVERY", "INVESTIGATING"}:
                raise TransitionError("INVALID_TRANSITION")
            row, manifest, binding = self._trusted(session, task, outcome.reference)
            snapshot = session.get(TaskSnapshot, task_id)
            policy = DownloadPolicy(**exact_policy(session, snapshot, "D-10")["result_download"])
            if sum(i.byte_length for i in manifest.items) > policy.max_total_bytes or any(
                i.byte_length > policy.max_download_bytes for i in manifest.items
            ):
                raise FileValidationError("size")
            existing = session.scalar(
                select(ResultManifestRecord).where(ResultManifestRecord.task_id == task_id)
            )
            if existing:
                self._check_manifest(session, task, existing)
            ensure_reserved_capacity(
                session, task.capacity_reservation_id,
                sum(item.byte_length for item in manifest.items),
                free_bytes=self.store.free_bytes,
            )
            if existing:
                return existing.id
            record = ResultManifestRecord(
                id=str(uuid4()),
                task_id=task_id,
                receipt_id=row.id,
                identity=dict(row.payload["identity"], upstream_id=task.upstream_id),
                manifest=manifest.model_dump(mode="json"),
                policy_versions=snapshot.policy_versions,
                created_at=database_now(session),
            )
            session.add(record)
            session.flush()
            for item in manifest.items:
                session.add(
                    ResultSaveItem(
                        id=str(uuid4()),
                        manifest_id=record.id,
                        item_key=item.item_key,
                        file_id=str(uuid4()),
                        file_version=str(uuid4()),
                        internal_path=UUID(task.user_id).hex + "/" + uuid4().hex,
                        locator=item.locator,
                        media_type=item.media_type,
                        sha256=item.sha256,
                        actual_bytes=item.byte_length,
                    )
                )
            return record.id

    def _check_manifest(self, session, task, record):
        if record is None or record.task_id != task.id:
            raise TransitionError("EVIDENCE_MISMATCH")
        row, manifest, binding = self._trusted(session, task, record.receipt_id)
        snapshot = session.get(TaskSnapshot, task.id)
        if (
            record.identity != dict(row.payload["identity"], upstream_id=task.upstream_id)
            or record.manifest != manifest.model_dump(mode="json")
            or record.policy_versions != snapshot.policy_versions
        ):
            raise TransitionError("EVIDENCE_MISMATCH")
        jobs = session.scalars(
            select(ResultSaveItem)
            .where(ResultSaveItem.manifest_id == record.id)
            .order_by(ResultSaveItem.item_key)
        ).all()
        if len(jobs) != len(manifest.items):
            raise TransitionError("EVIDENCE_MISMATCH")
        for job, item in zip(jobs, sorted(manifest.items, key=lambda i: i.item_key), strict=True):
            if (job.item_key, job.locator, job.sha256, job.actual_bytes, job.media_type) != (
                item.item_key,
                item.locator,
                item.sha256,
                item.byte_length,
                item.media_type,
            ):
                raise TransitionError("EVIDENCE_MISMATCH")
        return jobs, binding

    def verify_original_save(self, session, task, target, reference):
        record = session.get(ResultManifestRecord, reference)
        self._check_manifest(session, task, record)
        return VerifiedTransition(
            task.id,
            task.agent_id,
            task.agent_version,
            task.external_submission_id,
            "original_save",
            reference,
            record.identity["protocol_version"],
            upstream_id=task.upstream_id,
        )

    def install_verifiers(self, session):
        self.callbacks.install_verifiers(
            session, extra={"original_save": self.verify_original_save}
        )

    def verified_delivery(self, session, task, manifest_id):
        """SQL-only revalidation for T12, in caller-owned correctly ordered transaction.

        DurableDelivery is a view, never a caller-asserted publication proof.
        Physical file verification is performed before entering this transaction.
        """
        record = session.get(ResultManifestRecord, manifest_id)
        jobs, _ = self._check_manifest(session, task, record)
        receipt = session.get(ResultDeliveryRecord, manifest_id)
        if receipt is None:
            return None
        items = []
        for job in jobs:
            file = session.get(File, job.file_id)
            ref = session.scalar(
                select(FileRef).where(
                    FileRef.file_id == job.file_id,
                    FileRef.version == job.file_version,
                    FileRef.ref_type == "task_result",
                    FileRef.ref_id == task.id,
                    FileRef.user_id == task.user_id,
                )
            )
            if (
                file is None
                or ref is None
                or file.deleted_at is not None
                or (
                    file.version,
                    file.user_id,
                    file.reservation_id,
                    file.state,
                    file.internal_path,
                    file.sha256,
                    file.actual_bytes,
                    file.actual_mime,
                )
                != (
                    job.file_version,
                    task.user_id,
                    task.capacity_reservation_id,
                    "durable",
                    job.internal_path,
                    job.sha256,
                    job.actual_bytes,
                    job.media_type,
                )
            ):
                raise TransitionError("DURABLE_DELIVERY_MISMATCH")
            items.append(
                DurableItem(
                    job.item_key,
                    file.id,
                    file.version,
                    file.sha256,
                    file.actual_bytes,
                    file.actual_mime,
                )
            )
        total = sum(item.actual_bytes for item in items)
        if total != receipt.total_bytes:
            raise TransitionError("DURABLE_DELIVERY_MISMATCH")
        return DurableDelivery(
            task.id,
            record.id,
            record.receipt_id,
            record.identity["snapshot_digest"],
            tuple(items),
            total,
            tuple(record.manifest.get("warnings", ())),
        )

    @staticmethod
    def _name(job):
        return (
            job.item_key
            + {
                "text/plain": ".txt",
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "image/webp": ".webp",
                "video/mp4": ".mp4",
            }[job.media_type]
        )

    def _validate(self, path, job):
        if job.media_type == "text/plain":
            decoder = codecs.getincrementaldecoder("utf-8")("strict")
            try:
                with path.open("rb") as stream:
                    while chunk := stream.read(65536):
                        text = decoder.decode(chunk)
                        if "\x00" in text:
                            raise ValueError()
                    decoder.decode(b"", final=True)
            except (UnicodeError, ValueError):
                raise FileValidationError() from None
        else:
            validate_content(path, self._name(job), job.media_type, [job.media_type])

    def _retrieve(self, binding, job, policy):
        # The bounded mock JSON transport is an explicit fixture-only exception;
        # it cannot enable arbitrary loopback URLs or any production download.
        from app.agents.image import DOWNLOAD_SOURCE as IMAGE_SOURCE
        from app.agents.image import ImageAgentAdapter
        from app.agents.mock import MockAgentAdapter
        from app.agents.text import DOWNLOAD_SOURCE, TextAgentAdapter
        from app.agents.video import DOWNLOAD_SOURCE as VIDEO_SOURCE
        from app.agents.video import VideoAgentAdapter

        mock_source = (
            isinstance(binding.adapter, MockAgentAdapter) and binding.adapter.test_only
            and "TEST_ONLY:bound-mock" in policy.allowed_download_sources
        )
        text_source = (
            isinstance(binding.adapter, TextAgentAdapter)
            and DOWNLOAD_SOURCE in policy.allowed_download_sources
        )
        media_source = (
            isinstance(binding.adapter, ImageAgentAdapter)
            and IMAGE_SOURCE in policy.allowed_download_sources
        ) or (
            isinstance(binding.adapter, VideoAgentAdapter)
            and VIDEO_SOURCE in policy.allowed_download_sources
        )
        if not (mock_source or text_source or media_source):
            raise OriginalUnavailable("Original source unavailable")
        if media_source:
            binding.adapter.client.timeout = min(binding.adapter.client.timeout,
                                                 policy.download_timeout_seconds)
        else:
            binding.adapter.timeout = min(binding.adapter.timeout, policy.download_timeout_seconds)
        source = binding.adapter.retrieve_original(job.locator)
        if source.status in {"EXPIRED", "NOT_FOUND", "UNSUPPORTED"}:
            raise OriginalUnavailable("Original result cannot be recovered")
        if (
            source.status != "AVAILABLE"
            or not source.complete
            or source.test_only != binding.adapter.test_only
            or source.protocol_version != binding.protocol_version
            or source.locator != job.locator
            or source.sha256 != job.sha256
            or source.byte_length != job.actual_bytes
            or source.media_type != job.media_type
            or source.content is None
            or len(source.content) > policy.max_download_bytes
        ):
            raise FileValidationError()
        return io.BytesIO(source.content)

    def persist_original_result(self, task_id, manifest_id, *, lease):
        with self.factory() as session, session.begin():
            task = locked_execution(session, task_id, lease)
            record = session.get(ResultManifestRecord, manifest_id)
            jobs, binding = self._check_manifest(session, task, record)
            policy = DownloadPolicy(
                **exact_policy(session, session.get(TaskSnapshot, task_id), "D-10")[
                    "result_download"
                ]
            )
            self.install_verifiers(session)
            if task.state in {"SAVE_RECOVERY", "INVESTIGATING"}:
                reference = manifest_id if task.state == "SAVE_RECOVERY" else record.receipt_id
                transition_task(
                    session,
                    task_id,
                    task.state_version,
                    "SAVING",
                    TransitionEvidence(lease, reference),
                )
            if task.state != "SAVING":
                raise TransitionError("INVALID_TRANSITION")
            user_id, reservation_id = task.user_id, task.capacity_reservation_id
        for job in jobs:
            identity = dict(
                task_id=task_id,
                manifest_id=manifest_id,
                item_id=job.id,
                item_key=job.item_key,
                file_id=job.file_id,
                file_version=job.file_version,
                receipt_id=record.receipt_id,
                locator=job.locator,
            )
            expected = StagedFile(
                job.internal_path, job.actual_bytes, job.sha256, reservation_id, identity
            )
            with self.store.result_guard(job.internal_path):
                # A predecessor may have outlived its lease while holding this OS lock.
                with self.factory() as session, session.begin():
                    task = locked_execution(session, task_id, lease)
                    recorded = session.get(File, job.file_id) is not None
                recovered = self.store.recover_result(expected, recorded=recorded)
                if not recovered:
                    if recorded:
                        raise FileValidationError()
                    source = self.upstream._leased_transport(
                        self._retrieve, (binding, job, policy), lease)
                    prepared = StagedFile(job.internal_path, 0, "", reservation_id, identity)
                    staged = asyncio.run(
                        self.store.stage(
                            source,
                            user_id,
                            min(policy.max_download_bytes, job.actual_bytes),
                            prepared=prepared,
                        )
                    )
                    if (
                        staged.actual_bytes != expected.actual_bytes
                        or staged.sha256 != expected.sha256
                    ):
                        raise FileValidationError()
                    self._validate(self.store.staged_path(staged), job)
                    self.store.commit(staged)
                else:
                    self._validate(self.store.result_path(job.internal_path), job)
                # The only authoritative file-record commit occurs AFTER rename/fsync.
                with self.factory() as session, session.begin():
                    task = locked_execution(session, task_id, lease)
                    self._check_manifest(
                        session, task, session.get(ResultManifestRecord, manifest_id)
                    )
                    if task.state != "SAVING":
                        raise TransitionError("INVALID_TRANSITION")
                    if session.get(File, job.file_id) is None:
                        session.add(
                            File(
                                id=job.file_id,
                                version=job.file_version,
                                user_id=user_id,
                                internal_path=job.internal_path,
                                actual_mime=job.media_type,
                                actual_bytes=job.actual_bytes,
                                sha256=job.sha256,
                                display_name=self._name(job),
                                state="durable",
                                created_at=database_now(session),
                                reservation_id=reservation_id,
                            )
                        )
                        # Keep File and its protective task reference in the same commit.
                        session.add(
                            FileRef(
                                id=str(uuid4()),
                                file_id=job.file_id,
                                version=job.file_version,
                                user_id=user_id,
                                ref_type="task_result",
                                ref_id=task_id,
                                created_at=database_now(session),
                            )
                        )
                self.store.acknowledge(expected)
        with self.factory() as session, session.begin():
            task = locked_execution(session, task_id, lease)
            self._check_manifest(session, task, session.get(ResultManifestRecord, manifest_id))
            if task.state != "SAVING":
                raise TransitionError("INVALID_TRANSITION")
            if session.get(ResultDeliveryRecord, manifest_id) is None:
                session.add(
                    ResultDeliveryRecord(
                        manifest_id=manifest_id,
                        total_bytes=sum(j.actual_bytes for j in jobs),
                        fencing_token=lease.fencing_token,
                        created_at=database_now(session),
                    )
                )
                session.flush()
            return self.verified_delivery(session, task, manifest_id)

    def _failure(self, task_id, lease, unavailable):
        with self.factory() as session, session.begin():
            task = locked_execution(session, task_id, lease)
            if task.state == "SAVING":
                transition_task(
                    session, task_id, task.state_version, "SAVE_RECOVERY", TransitionEvidence(lease)
                )
            if unavailable and task.state == "SAVE_RECOVERY":
                transition_task(
                    session, task_id, task.state_version, "INVESTIGATING", TransitionEvidence(lease)
                )
            task.investigation_reason = (
                "ORIGINAL_RESULT_UNAVAILABLE" if unavailable else "ORIGINAL_SAVE_PENDING_RECOVERY"
            )

    def save_original(self, task_id, *, lease=None):
        owned = lease is None
        lease = lease or self.leases.claim_task(task_id, "original-save:" + uuid4().hex)
        if lease is None:
            return None
        try:
            outcome = self.callbacks.original_result(task_id)
            if outcome is None:
                return None
            manifest_id = self.prepare_manifest(task_id, outcome, lease=lease)
            return self.persist_original_result(task_id, manifest_id, lease=lease)
        except OriginalUnavailable:
            self._failure(task_id, lease, True)
            return None
        except (FileValidationError, OSError, StorageError):
            self._failure(task_id, lease, False)
            return None
        except TransitionError:
            raise
        except Exception:
            # A commit exception may mean committed OR rolled back. Preserve all
            # blobs and journals; the next run re-reads authoritative rows first.
            try:
                self._failure(task_id, lease, False)
            except Exception:
                pass  # Database outage/expired lease cannot authorize another write.
            raise
        finally:
            if owned:
                self.leases.release(lease)

    def recover_or_query(self, context):
        # Once the original manifest exists, a query outage cannot remove the
        # only safe recovery route. Retrieval never invokes submit.
        with self.factory() as session:
            manifest_id = session.scalar(
                select(ResultManifestRecord.id).where(
                    ResultManifestRecord.task_id == context.task_id
                )
            )
        if manifest_id:
            return self.handle(context)
        return self.upstream.handle(context)

    def handle(self, context):
        return self.save_original(context.task_id, lease=context.lease)
