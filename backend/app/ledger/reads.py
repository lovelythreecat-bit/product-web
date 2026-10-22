"""Only persistent owner-filtered reads; no balance reconciliation or writes."""

from datetime import UTC
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select

from app.common.pagination import numbered_page_rows
from app.common.types import NumberedPage
from app.conversations.service import authenticate
from app.ledger.models import CreditAccount, CreditLedger
from app.ledger.read_schemas import (
    AccountLedgerPage,
    AccountView,
    LedgerConsumption,
    LedgerEntryView,
)
from app.tasks.models import TaskSnapshot


def _time_bounds(start_time, end_time):
    for value in (start_time, end_time):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise HTTPException(422, "Time filters must include a timezone")
    if start_time is not None and end_time is not None and start_time >= end_time:
        raise HTTPException(422, "Start time must be before end time")
    return tuple(
        value.astimezone(UTC).replace(tzinfo=None) if value is not None else None
        for value in (start_time, end_time)
    )


def _ledger_scope(user_id, start_time=None, end_time=None):
    predicates = [CreditLedger.user_id == str(user_id)]
    if start_time is not None:
        predicates.append(CreditLedger.created_at >= start_time)
    if end_time is not None:
        predicates.append(CreditLedger.created_at < end_time)
    return predicates


def _task_name(snapshot):
    product = snapshot.input_snapshot.get("product", {})
    name = product.get("name") if isinstance(product, dict) else None
    if not isinstance(name, str) or not name.strip():
        return None
    suffix = {"copy": "文案", "image": "图片", "video": "视频"}.get(
        snapshot.agent_snapshot.get("kind"), "任务"
    )
    return name.strip() + suffix


class AccountReads:
    def __init__(self, session):
        self.session = session

    def account(self, principal):
        authenticate(self.session, principal)
        return self._account_for_user(principal.user_id)

    def _account_for_user(self, user_id):
        """Internal projection; caller must authorize owner or administrative access."""
        row = self.session.scalar(
            select(CreditAccount).where(CreditAccount.user_id == str(user_id))
        )
        if row is None:
            raise HTTPException(404)
        return AccountView(**{key: getattr(row, key) for key in AccountView.model_fields})

    def ledger(
        self, principal, cursor=None, limit=20, *, start_time=None, end_time=None, page=None
    ):
        authenticate(self.session, principal)
        start_time, end_time = _time_bounds(start_time, end_time)
        page = self._ledger_for_user(
            principal.user_id,
            cursor,
            limit,
            start_time=start_time,
            end_time=end_time,
            page=page,
        )
        return AccountLedgerPage(
            items=page.items,
            next_cursor=page.next_cursor,
            total=page.total,
            page=page.page,
            page_size=page.page_size,
            consumption=self._consumption_for_user(principal.user_id, start_time, end_time),
        )

    def _consumption_for_user(self, user_id, start_time, end_time):
        # The immutable consume ledger is the source of settled spending. Freeze,
        # release, grants and current quotations never contribute to this total.
        kind = TaskSnapshot.agent_snapshot["kind"].as_string()
        rows = self.session.execute(
            select(kind, func.sum(CreditLedger.amount))
            .select_from(CreditLedger)
            .outerjoin(
                TaskSnapshot,
                (TaskSnapshot.task_id == CreditLedger.task_id)
                & (TaskSnapshot.user_id == CreditLedger.user_id),
            )
            .where(*_ledger_scope(user_id, start_time, end_time), CreditLedger.kind == "consume")
            .group_by(kind)
        ).all()
        totals = {"copy": 0, "image": 0, "video": 0, "other": 0}
        for task_kind, amount in rows:
            totals[task_kind if task_kind in ("copy", "image", "video") else "other"] += int(amount)
        return LedgerConsumption(**totals)

    def _ledger_for_user(
        self, user_id, cursor=None, limit=20, *, start_time=None, end_time=None, page=None
    ):
        """Internal projection; cursor stays bound to the explicitly authorized user."""
        predicates = _ledger_scope(user_id, start_time, end_time)
        if cursor:
            try:
                cursor = str(UUID(cursor))
            except (ValueError, TypeError, AttributeError):
                raise HTTPException(404) from None
            if (
                self.session.scalar(
                    select(CreditLedger.id).where(*predicates, CreditLedger.id == cursor)
                )
                is None
            ):
                raise HTTPException(404)
        rows, next_cursor, metadata = numbered_page_rows(
            self.session,
            CreditLedger,
            predicates,
            cursor,
            limit,
            page=page,
        )
        task_ids = {row.task_id for row in rows if row.task_id}
        names = (
            {
                snapshot.task_id: _task_name(snapshot)
                for snapshot in self.session.scalars(
                    select(TaskSnapshot).where(
                        TaskSnapshot.user_id == str(user_id),
                        TaskSnapshot.task_id.in_(task_ids),
                    )
                ).all()
            }
            if task_ids
            else {}
        )
        return NumberedPage[LedgerEntryView](
            **metadata,
            items=[
                LedgerEntryView(
                    ledger_id=row.id,
                    grant_id=row.grant_id,
                    reservation_id=row.reservation_id,
                    task_id=row.task_id,
                    task_name=names.get(row.task_id),
                    kind=row.kind,
                    amount=row.amount,
                    balances_before=row.balances_before,
                    balances_after=row.balances_after,
                    reason=row.reason,
                    created_at=row.created_at.replace(tzinfo=UTC),
                )
                for row in rows
            ],
            next_cursor=next_cursor,
        )
