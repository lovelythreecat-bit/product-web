"""TEST_ONLY harness safety must fail closed before any database or process opens."""

import importlib.util

import pytest


def harness():
    spec = importlib.util.find_spec("tests.browser_support.runtime")
    assert spec is not None, "Missing fail-closed browser runtime"
    from tests.browser_support.runtime import validate_environment

    return validate_environment


@pytest.mark.parametrize("mode,flag", [("production", "true"), ("mock", "false"), ("mock", "")])
def test_harness_rejects_non_test_mode(monkeypatch, mode, flag):
    validate = harness()
    monkeypatch.setenv("APP_MODE", mode)
    monkeypatch.setenv("APP_TEST_ONLY", flag)
    with pytest.raises(ValueError):
        validate()


def test_harness_rejects_non_test_database(monkeypatch):
    validate = harness()
    monkeypatch.setenv("APP_MODE", "mock")
    monkeypatch.setenv("APP_TEST_ONLY", "true")
    monkeypatch.setenv("TEST_DATABASE_URL", "mysql+pymysql://root:secret@localhost/production")
    with pytest.raises(ValueError):
        validate()
