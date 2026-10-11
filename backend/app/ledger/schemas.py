from dataclasses import dataclass


@dataclass(frozen=True)
class SettlementReceipt:
    task_id: str
    reservation_id: str
    ledger_id: str
    state: str
    amount: int
    changed: bool


@dataclass(frozen=True)
class ReconciliationDifference:
    code: str
    user_id: str
    reference: str | None = None


@dataclass(frozen=True)
class ReconciliationReport:
    accounts_checked: int
    differences: tuple[ReconciliationDifference, ...]
