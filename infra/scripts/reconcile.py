"""Local operator CLI; SELECT-only consistent snapshot, no public API or repair mode."""

import argparse
import json
import os
import shutil
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.ledger.reconcile import reconcile_accounts  # noqa: E402
from app.operations.metrics import project_metrics, validate_thresholds  # noqa: E402


@contextmanager
def readonly_session():
    url = make_url(os.environ["OPS_DATABASE_URL"])
    if url.drivername != "mysql+pymysql" or not url.database:
        raise ValueError("mysql_database_required")
    engine = create_engine(url, echo=False, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            connection.exec_driver_sql("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
            with Session(bind=connection, autoflush=False) as session:
                yield session
            connection.rollback()
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", required=True)
    parser.add_argument("--thresholds", help="Explicit D12-approved alert thresholds JSON")
    args = parser.parse_args()
    try:
        from verify_storage import absolute

        root = absolute(args.storage_root)
        thresholds = json.loads(absolute(args.thresholds).read_text()) if args.thresholds else {}
        validate_thresholds(thresholds)
        with readonly_session() as session:
            report = reconcile_accounts(session)
            disk = shutil.disk_usage(root)
            metrics = project_metrics(
                session, free_bytes=disk.free, total_bytes=disk.total, thresholds=thresholds
            )
            metrics["migration_heads"] = list(
                session.execute(text("SELECT version_num FROM alembic_version")).scalars()
            )
        # Aggregate codes only: no account IDs, input text, credentials or SQL.
        metrics["ledger_differences"] = dict(Counter(d.code for d in report.differences))
        if report.differences:
            metrics["alerts"].append("ledger_mismatch")
        print(json.dumps(metrics, separators=(",", ":")))
        return 2 if metrics["alerts"] else (3 if not thresholds else 0)
    except Exception:
        print('{"ok":false,"code":"operations_unavailable"}')
        return 1


if __name__ == "__main__":
    sys.exit(main())
