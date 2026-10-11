"""Physical preparation outside resource locks; publication in one caller transaction.

Only ResultPublisher.prepare can mint a preparation; a DurableDelivery DTO is not
proof. The bound verifier re-reads the manifest, policy, files, collection, final
message and references inside the settlement transaction. No I/O runs under locks.
"""

from dataclasses import dataclass
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select

from app.conversations.models import Message
from app.dispatch.consumer import LeaseManager
from app.dispatch.recovery import database_now
from app.ledger.service import lock_task_resources, release_credits, settle_credits
from app.results.models import ResultManifestRecord
from app.storage.capacity import finalize_capacity
from app.storage.models import File, FileRef
from app.tasks.models import GenerationTask
from app.tasks.repository import task_view
from app.tasks.state_machine import (
    TransitionError,
    TransitionEvidence,
    VerifiedTransition,
    transition_task,
)
from app.works.models import Work, WorkItem


@dataclass(frozen=True)
class _Prepared:
    issuer: object
    delivery: object
    lease: object
    texts: tuple


class ResultPublisher:
    def __init__(self, persistence):
        self.persistence = persistence
        self.factory = persistence.factory
        self.leases = LeaseManager(self.factory)
        self._issuer = object()

    def prepare(self, task_id, *, lease):
        if self.persistence.store is None:
            return None
        delivery = self.persistence.save_original(task_id, lease=lease)
        if delivery is None:
            return None
        with self.factory() as session:
            paths = {
                item.file_id: session.get(File, item.file_id).internal_path
                for item in delivery.items
            }
        texts = []
        # save_original validated bytes and decoded media, outside resource locks.
        # Read text again and bind its bytes to the same fixed content hash.
        for item in delivery.items:
            if item.media_type == "text/plain":
                data = self.persistence.store.result_path(paths[item.file_id]).read_bytes()
                if len(data) != item.actual_bytes or sha256(data).hexdigest() != item.sha256:
                    raise TransitionError("DURABLE_DELIVERY_MISMATCH")
                texts.append((item.item_key, data.decode("utf-8")))
        return _Prepared(self._issuer, delivery, lease, tuple(texts))

    def install_verifiers(self, session, prepared=None):
        if prepared is not None and (
            not isinstance(prepared, _Prepared) or prepared.issuer is not self._issuer
        ):
            raise TransitionError("EVIDENCE_REQUIRED")
        self.persistence.callbacks.install_verifiers(
            session,
            extra={
                "original_save": self.persistence.verify_original_save,
                "publication": lambda s, t, target, ref: self.verify_publication(
                    s, t, target, ref, prepared
                ),
            },
        )
        session.info["publication_service"] = self
        session.info["publication_prepared"] = prepared

    def _delivery(self, session, task, manifest_id, prepared):
        delivery = self.persistence.verified_delivery(session, task, manifest_id)
        if delivery is None:
            raise TransitionError("EVIDENCE_REQUIRED")
        if task.state != "SUCCEEDED" and (
            prepared is None or prepared.issuer is not self._issuer or prepared.delivery != delivery
        ):
            raise TransitionError("EVIDENCE_REQUIRED")
        return delivery

    @staticmethod
    def _content(delivery, work_id, texts):
        return {
            "work_ids": [work_id],
            "manifest_id": delivery.manifest_id,
            "items": [
                dict(
                    item_key=i.item_key,
                    file_id=i.file_id,
                    file_version=i.file_version,
                    sha256=i.sha256,
                    actual_bytes=i.actual_bytes,
                    media_type=i.media_type,
                    **({"text": dict(texts)[i.item_key]} if i.media_type == "text/plain" else {}),
                )
                for i in delivery.items
            ],
        }

    def verify_publication(self, session, task, target, reference, prepared):
        delivery = self._delivery(session, task, reference, prepared)
        work = session.scalar(
            select(Work).where(Work.task_id == task.id).with_for_update(read=True)
        )
        if work is None or (work.user_id, work.conversation_id, work.manifest_id) != (
            task.user_id,
            task.conversation_id,
            reference,
        ):
            raise TransitionError("PUBLICATION_REQUIRED")
        message = session.get(Message, work.message_id, with_for_update={"read": True})
        if message is None or (
            message.task_id,
            message.user_id,
            message.conversation_id,
            message.kind,
            message.role,
        ) != (task.id, task.user_id, task.conversation_id, "final", "assistant"):
            raise TransitionError("PUBLICATION_REQUIRED")
        items = session.scalars(
            select(WorkItem)
            .where(WorkItem.work_id == work.id)
            .order_by(WorkItem.item_key)
            .with_for_update(read=True)
        ).all()
        if [(x.item_key, x.file_id, x.file_version, x.user_id) for x in items] != [
            (x.item_key, x.file_id, x.file_version, task.user_id) for x in delivery.items
        ]:
            raise TransitionError("PUBLICATION_REQUIRED")
        texts = (
            prepared.texts
            if prepared
            else tuple(
                (i["item_key"], i["text"]) for i in message.content.get("items", []) if "text" in i
            )
        )
        if message.content != self._content(delivery, work.id, texts):
            raise TransitionError("PUBLICATION_REQUIRED")
        for item in delivery.items:
            if item.media_type == "text/plain":
                data = dict(texts)[item.item_key].encode("utf-8")
                if sha256(data).hexdigest() != item.sha256 or len(data) != item.actual_bytes:
                    raise TransitionError("PUBLICATION_REQUIRED")
            for kind, ref in [("work", work.id), ("message", message.id)]:
                if (
                    session.scalar(
                        select(FileRef.id)
                        .where(
                            FileRef.file_id == item.file_id,
                            FileRef.version == item.file_version,
                            FileRef.user_id == task.user_id,
                            FileRef.ref_type == kind,
                            FileRef.ref_id == ref,
                        )
                        .with_for_update(read=True)
                    )
                    is None
                ):
                    raise TransitionError("PUBLICATION_REQUIRED")
        record = session.get(ResultManifestRecord, reference)
        return VerifiedTransition(
            task.id,
            task.agent_id,
            task.agent_version,
            task.external_submission_id,
            "publication",
            reference,
            record.identity["protocol_version"],
            upstream_id=task.upstream_id,
        )

    def publish_and_settle(self, session, task_id, manifest_id, expected_version):
        prepared = session.info.get("publication_prepared")
        task, _, _ = lock_task_resources(session, task_id)
        if task.state == "SUCCEEDED":
            self.verify_publication(session, task, "SUCCEEDED", manifest_id, None)
            return task_view(session, task)
        if task.state != "SAVING" or task.state_version != expected_version:
            raise TransitionError("VERSION_CONFLICT")
        delivery = self._delivery(session, task, manifest_id, prepared)
        from app.dispatch.consumer import lease_matches

        if not lease_matches(task, prepared.lease, database_now(session)):
            raise TransitionError("LEASE_LOST")
        work_id, message_id = str(uuid4()), str(uuid4())
        content = self._content(delivery, work_id, prepared.texts)
        session.add(
            Message(
                id=message_id,
                user_id=task.user_id,
                conversation_id=task.conversation_id,
                task_id=task.id,
                kind="final",
                role="assistant",
                content=content,
                created_at=database_now(session),
            )
        )
        session.flush()
        session.add(
            Work(
                id=work_id,
                user_id=task.user_id,
                task_id=task.id,
                conversation_id=task.conversation_id,
                manifest_id=manifest_id,
                message_id=message_id,
                created_at=database_now(session),
            )
        )
        session.flush()
        for item in delivery.items:
            session.add(
                WorkItem(
                    id=str(uuid4()),
                    work_id=work_id,
                    user_id=task.user_id,
                    item_key=item.item_key,
                    file_id=item.file_id,
                    file_version=item.file_version,
                )
            )
            for kind, ref in [("work", work_id), ("message", message_id)]:
                session.add(
                    FileRef(
                        id=str(uuid4()),
                        file_id=item.file_id,
                        version=item.file_version,
                        user_id=task.user_id,
                        ref_type=kind,
                        ref_id=ref,
                        created_at=database_now(session),
                    )
                )
        session.flush()
        evidence = TransitionEvidence(prepared.lease, manifest_id)
        settle_credits(session, task.id, evidence)
        finalize_capacity(session, task.capacity_reservation_id, delivery.total_bytes)
        transition_task(session, task.id, expected_version, "SUCCEEDED", evidence)
        return task_view(session, task)

    def published(self, task_id):
        """Authoritative reread after uncertain commit; never downloads or regenerates."""
        with self.factory() as session:
            task = session.get(GenerationTask, task_id)
            if task is None or task.state != "SUCCEEDED":
                return None
            work = session.scalar(select(Work).where(Work.task_id == task_id))
            if work is None:
                raise TransitionError("PUBLICATION_REQUIRED")
            self.verify_publication(session, task, "SUCCEEDED", work.manifest_id, None)
            from app.ledger.models import CreditLedger, CreditReservation
            from app.storage.models import CapacityReservation

            ledger = session.scalar(
                select(CreditLedger).where(CreditLedger.operation_key == f"settle:{task_id}")
            )
            reservation = session.scalar(
                select(CreditReservation).where(CreditReservation.task_id == task_id)
            )
            capacity = session.get(CapacityReservation, task.capacity_reservation_id)
            delivery = self.persistence.verified_delivery(session, task, work.manifest_id)
            if (
                task.settlement_state != "CONSUMED"
                or ledger is None
                or ledger.kind != "consume"
                or reservation.state != "consumed"
                or ledger.amount != reservation.amount
                or capacity.state != "finalized"
                or capacity.actual_bytes != delivery.total_bytes
            ):
                raise TransitionError("SETTLEMENT_REQUIRED")
            return task_view(session, task)

    def run(self, task_id, *, lease=None):
        existing = self.published(task_id)
        if existing:
            return existing
        owned = lease is None
        lease = lease or self.leases.claim_task(task_id, "publication:" + uuid4().hex)
        if lease is None:
            return self.published(task_id)
        try:
            prepared = self.prepare(task_id, lease=lease)
            if prepared is None:
                return None
            try:
                with self.factory() as session, session.begin():
                    self.install_verifiers(session, prepared)
                    task = session.get(GenerationTask, task_id)
                    result = publish_and_settle(
                        session, task_id, prepared.delivery.manifest_id, task.state_version
                    )
                return result
            except Exception:
                recovered = self.published(task_id)
                if recovered:
                    return recovered
                raise
        finally:
            if owned:
                self.leases.release(lease)

    def handle(self, context):
        upstream = self.persistence.upstream
        reference = upstream.pending_failure(context.task_id)
        if not reference and context.action != "save_original":
            with self.factory() as session:
                manifest = session.scalar(
                    select(ResultManifestRecord.id).where(
                        ResultManifestRecord.task_id == context.task_id
                    )
                )
            if not manifest:
                upstream.handle(context)
            reference = upstream.pending_failure(context.task_id)
        if reference:
            with self.factory() as session, session.begin():
                self.install_verifiers(session)
                return release_credits(
                    session, context.task_id, TransitionEvidence(context.lease, reference)
                )
        with self.factory() as session:
            state = session.get(GenerationTask, context.task_id).state
        if (
            state in {"SAVING", "SAVE_RECOVERY"}
            or state == "INVESTIGATING"
            and upstream.original_result(context.task_id)
        ):
            return self.run(context.task_id, lease=context.lease)
        return None


def publish_and_settle(session, task_id, manifest_id, expected_version):
    """Configured trusted caller Session; no commit, downloads, or caller asserted DTOs."""
    service = session.info.get("publication_service")
    if not isinstance(service, ResultPublisher):
        raise TransitionError("EVIDENCE_REQUIRED")
    return service.publish_and_settle(session, str(task_id), str(manifest_id), expected_version)
