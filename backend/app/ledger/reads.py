"""Only persistent owner-filtered reads; no balance reconciliation or writes."""

from datetime import UTC
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.common.pagination import page_rows
from app.common.types import CursorPage
from app.conversations.service import authenticate
from app.ledger.models import CreditAccount, CreditLedger
from app.ledger.read_schemas import AccountView, LedgerEntryView


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

    def ledger(self, principal, cursor=None, limit=20):
        authenticate(self.session, principal)
        return self._ledger_for_user(principal.user_id, cursor, limit)

    def _ledger_for_user(self, user_id, cursor=None, limit=20):
        """Internal projection; cursor stays bound to the explicitly authorized user."""
        predicates = [CreditLedger.user_id == str(user_id)]
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
        rows, next_cursor = page_rows(self.session, CreditLedger, predicates, cursor, limit)
        return CursorPage[LedgerEntryView](
            items=[
                LedgerEntryView(
                    ledger_id=row.id,
                    grant_id=row.grant_id,
                    reservation_id=row.reservation_id,
                    task_id=row.task_id,
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
