"""Read the original T12 publication; never assemble partial saves into a work."""

from datetime import UTC
from hashlib import sha256

from fastapi import HTTPException
from sqlalchemy import select

from app.admin.permissions import authorize_resource
from app.common.pagination import page_rows
from app.common.types import CursorPage
from app.conversations.models import Message
from app.conversations.service import authenticate
from app.ledger.models import CreditLedger, CreditReservation
from app.storage.models import File
from app.tasks.models import GenerationTask, TaskSnapshot
from app.tasks.repository import TaskRepository
from app.works.models import Work, WorkItem
from app.works.schemas import SourceMaterial, WorkDetail, WorkItemView, WorkSource, WorkView


class WorkService:
    def __init__(self, session):
        self.session = session

    def _predicates(self, principal, kind=None):
        tasks = select(GenerationTask.id).where(
            GenerationTask.user_id == str(principal.user_id),
            GenerationTask.state == "SUCCEEDED",
            GenerationTask.settlement_state == "CONSUMED",
        )
        predicates = [Work.user_id == str(principal.user_id), Work.task_id.in_(tasks)]
        if kind is not None:
            if kind not in ("copy", "image", "video"):
                raise HTTPException(422)
            predicates.append(
                Work.task_id.in_(
                    select(TaskSnapshot.task_id).where(
                        TaskSnapshot.user_id == str(principal.user_id),
                        TaskSnapshot.agent_snapshot["kind"].as_string() == kind,
                    )
                )
            )
        return predicates

    def list_works(self, principal, kind=None, cursor=None, limit=20):
        authenticate(self.session, principal)
        predicates = self._predicates(principal, kind)
        if cursor:
            # Resolve the anchor in precisely the same owner/filter scope.
            authorize_resource(self.session, principal, "work", cursor)
            if self.session.scalar(select(Work.id).where(*predicates, Work.id == cursor)) is None:
                raise HTTPException(404)
        rows, next_cursor = page_rows(self.session, Work, predicates, cursor, limit)
        return CursorPage[WorkView](
            items=[self._view(principal, row) for row in rows],
            next_cursor=next_cursor,
        )

    def _view(self, principal, row):
        authorize_resource(self.session, principal, "task", row.task_id)
        authorize_resource(self.session, principal, "conversation", row.conversation_id)
        authorize_resource(self.session, principal, "message", row.message_id)
        snapshot = self.session.get(TaskSnapshot, row.task_id)
        message = self.session.get(Message, row.message_id)
        if (
            (message.task_id, message.conversation_id, message.kind, message.role)
            != (row.task_id, row.conversation_id, "final", "assistant")
            or message.content.get("work_ids") != [row.id]
            or message.content.get("manifest_id") != row.manifest_id
        ):
            raise HTTPException(404)
        items = self.session.scalars(
            select(WorkItem)
            .where(WorkItem.work_id == row.id, WorkItem.user_id == str(principal.user_id))
            .order_by(WorkItem.item_key)
        ).all()
        originals = message.content.get("items", [])
        if not items or len(items) != len(originals):
            raise HTTPException(404)
        views = []
        for item, original in zip(items, originals, strict=True):
            authorize_resource(
                self.session, principal, "file_version", item.file_id, version=item.file_version
            )
            file = self.session.get(File, item.file_id)
            expected = dict(
                item_key=item.item_key,
                file_id=file.id,
                file_version=file.version,
                sha256=file.sha256,
                actual_bytes=file.actual_bytes,
                media_type=file.actual_mime,
            )
            if any(original.get(key) != value for key, value in expected.items()):
                raise HTTPException(404)
            text = original.get("text") if file.actual_mime == "text/plain" else None
            if file.actual_mime == "text/plain" and (
                not isinstance(text, str)
                or len(text.encode("utf-8")) != file.actual_bytes
                or sha256(text.encode("utf-8")).hexdigest() != file.sha256
            ):
                raise HTTPException(404)
            views.append(
                WorkItemView(
                    item_key=item.item_key,
                    file_id=file.id,
                    file_version=file.version,
                    media_type=file.actual_mime,
                    actual_bytes=file.actual_bytes,
                    content_url=f"/api/v1/files/{file.id}/content",
                    text=text,
                )
            )
        return WorkView(
            work_id=row.id,
            kind=snapshot.agent_snapshot["kind"],
            task_id=row.task_id,
            conversation_id=row.conversation_id,
            message_id=row.message_id,
            created_at=row.created_at.replace(tzinfo=UTC),
            items=views,
        )

    def read_work(self, principal, id):
        authorize_resource(self.session, principal, "work", id)
        row = self.session.scalar(
            select(Work).where(*self._predicates(principal), Work.id == str(id))
        )
        if row is None:
            raise HTTPException(404)
        view = self._view(principal, row)
        detail = TaskRepository(self.session).read_task(principal, row.task_id)
        materials = []
        for ref in detail.input.material_versions:
            file = self.session.scalar(
                select(File).where(
                    File.id == str(ref.file_id),
                    File.version == ref.version,
                    File.user_id == str(principal.user_id),
                    File.state == "durable",
                    File.deleted_at.is_(None),
                )
            )
            materials.append(
                SourceMaterial(
                    file=ref, available=file is not None, action=None if file else "upload_again"
                )
            )
        reservation = self.session.scalar(
            select(CreditReservation).where(
                CreditReservation.task_id == row.task_id,
                CreditReservation.user_id == str(principal.user_id),
            )
        )
        if reservation is None:
            raise HTTPException(404)
        ledger = self.session.scalars(
            select(CreditLedger.id)
            .where(
                CreditLedger.task_id == row.task_id,
                CreditLedger.user_id == str(principal.user_id),
            )
            .order_by(CreditLedger.created_at, CreditLedger.id)
        ).all()
        source = WorkSource(
            **detail.model_dump(),
            materials=materials,
            credit_reservation_id=reservation.id,
            ledger_ids=list(ledger),
        )
        return WorkDetail(**view.model_dump(), source=source)
