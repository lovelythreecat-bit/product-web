from threading import Event
from types import SimpleNamespace

from worker.main import run_workers


def report():
    return (SimpleNamespace(scheduled=[]), SimpleNamespace(dispatched=0, failed=0),
            SimpleNamespace(handled=0, unhandled=0, failed=0))


def test_an_unfinished_generation_does_not_block_another_worker_slot():
    first_started, second_started, stop = Event(), Event(), Event()

    class First:
        def tick(self, *, batch_size):
            assert batch_size == 1
            first_started.set()
            assert second_started.wait(2), "second generation was blocked by the first"
            return report()

    class Second:
        def tick(self, *, batch_size):
            assert batch_size == 1
            assert first_started.wait(2)
            second_started.set()
            return report()

    assert run_workers([First(), Second()], stop, interval=0.01, once=True) == 0
    assert first_started.is_set() and second_started.is_set()


def test_database_failure_in_one_slot_does_not_cancel_the_other():
    from sqlalchemy.exc import SQLAlchemyError

    completed = Event()

    class Broken:
        def tick(self, *, batch_size):
            raise SQLAlchemyError()

    class Healthy:
        def tick(self, *, batch_size):
            completed.set()
            return report()

    assert run_workers([Broken(), Healthy()], Event(), interval=0.01, once=True) == 1
    assert completed.is_set()


def test_database_error_logs_safe_diagnostics(caplog):
    import pymysql
    from sqlalchemy.exc import OperationalError

    class Broken:
        def tick(self, *, batch_size):
            raise OperationalError(
                "SELECT private_content", {"password": "secret-value"},
                pymysql.OperationalError(2013, "private connection details"),
            )

    assert run_workers([Broken()], Event(), interval=0.01, once=True) == 1
    assert "OperationalError" in caplog.text
    assert "2013" in caplog.text
    for private in ("private_content", "secret-value", "private connection details"):
        assert private not in caplog.text


def test_unexpected_stage_failure_is_safe_and_does_not_cancel_other_slots(
    caplog, operations_log_capture
):
    completed = Event()

    class Broken:
        def tick(self, *, batch_size):
            raise ValueError("private model request and customer input")

    class Healthy:
        def tick(self, *, batch_size):
            completed.set()
            return report()

    assert run_workers([Broken(), Healthy()], Event(), interval=0.01, once=True) == 1
    assert completed.is_set()
    assert "STAGE_EXCEPTION" in caplog.text and "ValueError" in caplog.text
    assert "private model" not in caplog.text and "customer input" not in caplog.text
