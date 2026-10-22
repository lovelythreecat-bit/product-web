import pytest
from pydantic import ValidationError

from app import config
from app.main import application


def test_api_reads_backend_env_from_any_working_directory(tmp_path, monkeypatch):
    env_file = tmp_path / "backend" / ".env"
    env_file.parent.mkdir()
    env_file.write_text(
        f'APP_STORAGE_ROOT="{tmp_path.as_posix()}"\nAPP_STORAGE_PERSISTENT=true\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "RUNTIME_ENV_FILE", env_file, raising=False)
    monkeypatch.chdir(tmp_path)
    app = application()
    assert app.state.settings.storage_root == tmp_path
    assert app.state.settings.storage_persistent is True


def test_runtime_environment_overrides_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("APP_EVENT_RETENTION_SECONDS=60\n", encoding="utf-8")
    monkeypatch.setattr(config, "RUNTIME_ENV_FILE", env_file, raising=False)
    monkeypatch.setenv("APP_EVENT_RETENTION_SECONDS", "120")
    assert application().state.settings.event_retention_seconds == 120


def test_missing_runtime_file_keeps_environment_startup(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUNTIME_ENV_FILE", tmp_path / "missing.env", raising=False)
    monkeypatch.setenv("APP_EVENT_RETENTION_SECONDS", "120")
    assert application().state.settings.event_retention_seconds == 120


def test_plain_settings_do_not_load_developer_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("APP_EVENT_RETENTION_SECONDS=60\n", encoding="utf-8")
    monkeypatch.setattr(config, "RUNTIME_ENV_FILE", env_file, raising=False)
    assert config.Settings().event_retention_seconds == 604800


def test_runtime_file_keeps_production_guards(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_MODE=production\nAPP_TEST_ONLY=true\n", encoding="utf-8"
    )
    monkeypatch.setattr(config, "RUNTIME_ENV_FILE", env_file, raising=False)
    with pytest.raises(ValidationError, match="TEST_ONLY"):
        application()
