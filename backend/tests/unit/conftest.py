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
