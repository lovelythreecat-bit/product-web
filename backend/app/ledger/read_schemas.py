"""Owner-only public ledger projections; writing remains in ledger.service."""

from uuid import UUID

from app.common.types import DTO, NonNegativeInt, Timestamp


class AccountView(DTO):
    available: NonNegativeInt
    frozen: NonNegativeInt
    consumed: NonNegativeInt
    credited_total: NonNegativeInt


class LedgerBalances(DTO):
    available: NonNegativeInt
    frozen: NonNegativeInt
    consumed: NonNegativeInt


class LedgerEntryView(DTO):
    ledger_id: UUID
    grant_id: UUID | None
    reservation_id: UUID | None
    task_id: UUID | None
    kind: str
    amount: NonNegativeInt
    balances_before: LedgerBalances
    balances_after: LedgerBalances
    reason: str
    created_at: Timestamp
