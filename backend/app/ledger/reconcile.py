"""Read-only financial diagnostics; never fixes balances or exposes private content."""

from collections import Counter, defaultdict

from sqlalchemy import select

from app.ledger.models import CreditAccount, CreditGrant, CreditLedger, CreditReservation
from app.ledger.schemas import ReconciliationDifference, ReconciliationReport
from app.tasks.models import GenerationTask


def _complete_balance_trail(edges, end):
    """An Euler trail uses every ledger transition once, from zero to net balance.

    Directed degree balance plus weak connectivity is sufficient. This is O(E+V),
    including repeated freeze/release cycles and zero-amount self loops; neither
    timestamp sorting nor a search through possible operation permutations is used.
    """
    start = (0, 0, 0)
    degrees = Counter()
    neighbors = defaultdict(set)
    for before, after in edges:
        degrees[before] += 1
        degrees[after] -= 1
        neighbors[before].add(after)
        neighbors[after].add(before)
    for node, degree in degrees.items():
        if degree != int(node == start) - int(node == end):
            return False
    if end != start and (start not in degrees or end not in degrees):
        return False
    visited, pending = set(), [start]
    while pending:
        node = pending.pop()
        if node not in visited:
            visited.add(node)
            pending.extend(neighbors.get(node, ()) - visited if node in neighbors else ())
    return all(node in visited for node in neighbors)


def reconcile_accounts(session):
    differences = []

    def add(code, uid, ref=None):
        differences.append(ReconciliationDifference(code, uid, ref))

    with session.no_autoflush:
        accounts = session.scalars(select(CreditAccount)).all()
        grants = session.scalars(select(CreditGrant)).all()
        ledgers = session.scalars(select(CreditLedger)).all()
        reservations = session.scalars(select(CreditReservation)).all()
        tasks = {x.id: x for x in session.scalars(select(GenerationTask))}
        by_user, by_task, by_grant = defaultdict(list), defaultdict(list), defaultdict(list)
        for row in ledgers:
            by_user[row.user_id].append(row)
            by_task[row.task_id].append(row)
            by_grant[row.grant_id].append(row)
        totals = defaultdict(int)
        for grant in grants:
            totals[grant.user_id] += grant.amount
            rows = by_grant[grant.id]
            if len(rows) != 1 or (rows[0].amount, rows[0].kind, rows[0].user_id) != (
                grant.amount,
                grant.kind,
                grant.user_id,
            ):
                add("GRANT_LEDGER_MISMATCH", grant.user_id, grant.id)
        for account in accounts:
            uid = account.user_id
            balances = (account.available, account.frozen, account.consumed)
            if min(balances) < 0 or sum(balances) != account.credited_total:
                add("BALANCE_CONSERVATION", uid)
            if account.credited_total != totals[uid]:
                add("CREDITED_TOTAL_MISMATCH", uid)
            rows = by_user[uid]
            net = [0, 0, 0]
            edges = []
            keys = ("available", "frozen", "consumed")
            for row in rows:
                delta = {
                    "signup": (row.amount, 0, 0),
                    "admin": (row.amount, 0, 0),
                    "freeze": (-row.amount, row.amount, 0),
                    "consume": (0, -row.amount, row.amount),
                    "release": (row.amount, -row.amount, 0),
                }.get(row.kind)
                if delta is None:
                    add("UNKNOWN_LEDGER_KIND", uid, row.id)
                    continue
                expected = {
                    key: row.balances_before[key] + value
                    for key, value in zip(("available", "frozen", "consumed"), delta)
                }
                if (
                    expected != row.balances_after
                    or min(row.balances_before.values()) < 0
                    or min(row.balances_after.values()) < 0
                ):
                    add("LEDGER_DELTA_MISMATCH", uid, row.id)
                    continue
                net = [current + change for current, change in zip(net, delta)]
                edges.append(
                    (
                        tuple(row.balances_before[key] for key in keys),
                        tuple(row.balances_after[key] for key in keys),
                    )
                )
            if not _complete_balance_trail(edges, tuple(net)):
                add("LEDGER_CHAIN_MISMATCH", uid)
            if tuple(net) != balances:
                add("LEDGER_ACCOUNT_MISMATCH", uid)
            for key, count in Counter(r.operation_key for r in rows).items():
                if count > 1:
                    add("DUPLICATE_OPERATION", uid)
            frozen = sum(r.amount for r in reservations if r.user_id == uid and r.state == "frozen")
            consumed = sum(
                r.amount for r in reservations if r.user_id == uid and r.state == "consumed"
            )
            if (frozen, consumed) != (account.frozen, account.consumed):
                add("RESERVATION_BALANCE_MISMATCH", uid)
        for reservation in reservations:
            task = tasks.get(reservation.task_id)
            rows = by_task[reservation.task_id]
            freeze = [r for r in rows if r.kind == "freeze"]
            final = [r for r in rows if r.kind in {"consume", "release"}]
            if len(freeze) != 1 or any(
                (r.reservation_id, r.user_id, r.amount)
                != (reservation.id, reservation.user_id, reservation.amount)
                for r in rows
            ):
                add("RESERVATION_LEDGER_MISMATCH", reservation.user_id, reservation.id)
            kind = {"consumed": "consume", "released": "release"}.get(reservation.state)
            if (kind is None and final) or (kind and (len(final) != 1 or final[0].kind != kind)):
                add("DUPLICATE_OR_MISSING_SETTLEMENT", reservation.user_id, reservation.id)
            if (
                task is None
                or task.settlement_state != reservation.state.upper()
                or (reservation.state == "consumed" and task.state != "SUCCEEDED")
                or (
                    reservation.state == "released"
                    and task.state not in {"FAILED", "MANUALLY_CLOSED"}
                )
            ):
                add("TASK_SETTLEMENT_MISMATCH", reservation.user_id, reservation.id)
    return ReconciliationReport(len(accounts), tuple(differences))
