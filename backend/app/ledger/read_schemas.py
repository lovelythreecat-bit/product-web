"""Owner-only public ledger projections; writing remains in ledger.service."""

from uuid import UUID

from pydantic import Field

from app.common.types import DTO, NonNegativeInt, NumberedPage, Timestamp


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
    task_name: str | None = None
    kind: str
    amount: NonNegativeInt
    balances_before: LedgerBalances
    balances_after: LedgerBalances
    reason: str
    created_at: Timestamp


class LedgerConsumption(DTO):
    copy_: NonNegativeInt = Field(default=0, alias="copy")
    image: NonNegativeInt = 0
    video: NonNegativeInt = 0
    other: NonNegativeInt = 0


class AccountLedgerPage(NumberedPage[LedgerEntryView]):
    consumption: LedgerConsumption
