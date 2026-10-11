"""Reconciliation must use financial transitions, never wall clocks or UUID order."""

from contextlib import nullcontext
from datetime import datetime, timedelta

import pytest

from app.ledger.models import CreditAccount, CreditGrant, CreditLedger, CreditReservation
from app.ledger.reconcile import reconcile_accounts
from app.tasks.models import GenerationTask


class ReadOnlyRows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def __iter__(self):
        return iter(self.rows)


class ReadOnlySession:
    """Only the five SELECTs used by the real diagnostic function; no write API."""

    no_autoflush = nullcontext()

    def __init__(self, data):
        self.data = data

    def scalars(self, statement):
        return ReadOnlyRows(self.data[statement.column_descriptions[0]["entity"]])


def balance(available, frozen=0, consumed=0):
    return dict(available=available, frozen=frozen, consumed=consumed)


def account_data(order="ordered"):
    t = datetime(2026, 10, 12, 10)
    data = {
        CreditAccount: [
            CreditAccount(user_id="u", available=70, frozen=0, consumed=30, credited_total=100)
        ],
        CreditGrant: [CreditGrant(id="g", user_id="u", amount=100, kind="signup")],
        CreditReservation: [
            CreditReservation(id="r", user_id="u", task_id="t", amount=30, state="consumed")
        ],
        GenerationTask: [
            GenerationTask(id="t", user_id="u", state="SUCCEEDED", settlement_state="CONSUMED")
        ],
        CreditLedger: [
            CreditLedger(
                id="00000000-0000-0000-0000-000000000001",
                user_id="u",
                grant_id="g",
                kind="signup",
                amount=100,
                operation_key="grant:g",
                balances_before=balance(0),
                balances_after=balance(100),
                created_at=t,
            ),
            CreditLedger(
                id="00000000-0000-0000-0000-000000000003",
                user_id="u",
                task_id="t",
                reservation_id="r",
                kind="freeze",
                amount=30,
                operation_key="freeze:t",
                balances_before=balance(100),
                balances_after=balance(70, 30),
                created_at=t + timedelta(seconds=2),
            ),
            CreditLedger(
                id="00000000-0000-0000-0000-000000000002",
                user_id="u",
                task_id="t",
                reservation_id="r",
                kind="consume",
                amount=30,
                operation_key="settle:t",
                balances_before=balance(70, 30),
                balances_after=balance(70, 0, 30),
                created_at=t + timedelta(seconds=3),
            ),
        ],
    }
    if order == "clock_skew":
        data[CreditLedger][2].created_at = t + timedelta(seconds=1)
    elif order == "uuid_tie":
        for row in data[CreditLedger]:
            row.created_at = t
    # Even a SELECT without ORDER BY may return the records in an arbitrary order.
    data[CreditLedger].reverse()
    return data


@pytest.mark.parametrize("order", ["ordered", "clock_skew", "uuid_tie"])
def test_valid_settlement_ignores_time_and_uuid(order):
    report = reconcile_accounts(ReadOnlySession(account_data(order)))
    assert report.differences == ()


def add_cycle(data, name, before, amount):
    after = dict(before, available=before["available"] - amount, frozen=before["frozen"] + amount)
    data[CreditReservation].append(
        CreditReservation(id=name, user_id="u", task_id=name, amount=amount, state="released")
    )
    data[GenerationTask].append(
        GenerationTask(id=name, user_id="u", state="FAILED", settlement_state="RELEASED")
    )
    for kind, start, end in [("freeze", before, after), ("release", after, before)]:
        data[CreditLedger].append(
            CreditLedger(
                id=name + kind,
                user_id="u",
                task_id=name,
                reservation_id=name,
                kind=kind,
                amount=amount,
                operation_key=name + kind,
                balances_before=start,
                balances_after=end,
                created_at=datetime(2026, 10, 12),
            )
        )


def test_valid_cycles_and_zero_amount_self_loops_are_bounded():
    data = account_data("uuid_tie")
    # Thousands of indistinguishable transitions must not trigger permutation search.
    for index in range(2500):
        add_cycle(data, str(index), balance(100), 10 if index % 2 else 0)
    data[CreditLedger].reverse()
    assert reconcile_accounts(ReadOnlySession(data)).differences == ()


def test_zero_credit_account_with_only_self_loops():
    data = account_data()
    data[CreditAccount][0].available = 0
    data[CreditAccount][0].consumed = 0
    data[CreditAccount][0].credited_total = 0
    data[CreditGrant][0].amount = 0
    data[CreditReservation][0].amount = 0
    for row in data[CreditLedger]:
        row.amount = 0
        row.balances_before = balance(0)
        row.balances_after = balance(0)
    assert reconcile_accounts(ReadOnlySession(data)).differences == ()


@pytest.mark.parametrize("defect", ["disconnected_cycle", "disconnected_zero", "broken_edge"])
def test_net_correct_but_disconnected_balances_are_reported(defect):
    data = account_data("uuid_tie")
    if defect.startswith("disconnected"):
        add_cycle(data, "orphan", balance(90, 10), 10 if defect == "disconnected_cycle" else 0)
    else:
        consume = next(row for row in data[CreditLedger] if row.kind == "consume")
        consume.balances_before = balance(60, 40)
        consume.balances_after = balance(60, 10, 30)
    codes = {d.code for d in reconcile_accounts(ReadOnlySession(data)).differences}
    assert "LEDGER_CHAIN_MISMATCH" in codes
    assert "LEDGER_ACCOUNT_MISMATCH" not in codes


def test_wrong_delta_and_wrong_account_are_still_reported():
    data = account_data()
    data[CreditAccount][0].available = 69
    data[CreditAccount][0].consumed = 31
    consume = next(row for row in data[CreditLedger] if row.kind == "consume")
    consume.balances_after = balance(71, 0, 30)
    codes = {d.code for d in reconcile_accounts(ReadOnlySession(data)).differences}
    assert {"LEDGER_DELTA_MISMATCH", "LEDGER_ACCOUNT_MISMATCH"} <= codes
