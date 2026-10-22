"""Unit tests start with clean app configuration, independent of the developer shell."""

import os

import pytest


@pytest.fixture(autouse=True)
def isolate_app_environment(monkeypatch):
    # Run before each unit test; tests can then explicitly set their own APP_* values.
    # monkeypatch restores the caller environment afterwards, including APP_MODE for integration.
    for name in tuple(os.environ):
        if name.upper().startswith("APP_"):
            monkeypatch.delenv(name)


@pytest.fixture
def operations_log_capture(caplog):
    """Capture operations logs even after application logging disables propagation."""
    from app.operations.telemetry import logger

    original_handlers = list(logger.handlers)
    original_propagate = logger.propagate
    try:
        logger.addHandler(caplog.handler)
        # Capture directly once, regardless of the root logger's pytest handlers.
        logger.propagate = False
        yield caplog
    finally:
        logger.handlers[:] = original_handlers
        logger.propagate = original_propagate
