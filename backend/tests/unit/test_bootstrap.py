from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app


def test_production_rejects_test_only(monkeypatch):
    # Losing this guard would enable development controls in production.
    monkeypatch.setenv("APP_MODE", "production")
    monkeypatch.setenv("APP_TEST_ONLY", "true")
    with pytest.raises(ValidationError, match="TEST_ONLY"):
        Settings()


def test_readiness_requires_persistent_root(tmp_path: Path):
    # Readiness must not advertise safe file persistence for a missing root.
    missing_root = tmp_path / "missing-volume"
    with TestClient(create_app(Settings(storage_root=missing_root))) as client:
        response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert not missing_root.exists()


def test_live_identifies_mock_mode_without_exposing_configuration(tmp_path: Path):
    with TestClient(create_app(Settings(storage_root=tmp_path))) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"live": True, "mode": "mock", "test_only": True}
    assert str(tmp_path) not in response.text


@pytest.mark.parametrize("mode", ["production", "staging"])
def test_non_mock_rejects_placeholder_secrets(mode: str):
    with pytest.raises(ValidationError, match="TEST_ONLY"):
        Settings(mode=mode, test_only=False, database_url="mysql+pymysql://TEST_ONLY@localhost/db")


def test_existing_directory_needs_explicit_persistence_declaration(tmp_path: Path):
    with TestClient(create_app(Settings(storage_root=tmp_path))) as client:
        response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["storage"] is False


def test_writable_declared_root_is_checked_but_database_is_still_required(tmp_path: Path):
    settings = Settings(storage_root=tmp_path, storage_persistent=True)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"] == {"storage": True, "database": False}
    assert list(tmp_path.iterdir()) == []


def test_regular_file_cannot_be_persistent_root(tmp_path: Path):
    root = tmp_path / "file"
    root.write_text("not a directory")
    with TestClient(create_app(Settings(storage_root=root, storage_persistent=True))) as client:
        response = client.get("/api/v1/health/ready")
    assert response.json()["checks"]["storage"] is False


def test_mock_controls_are_not_public_routes():
    with TestClient(create_app(Settings(mode="production", test_only=False))) as client:
        for route in ("/test/reset", "/test/seed", "/test/faults"):
            assert client.post("/api/v1" + route).status_code == 404


def test_production_rejects_test_only_storage_path(tmp_path: Path):
    with pytest.raises(ValidationError, match="TEST_ONLY"):
        Settings(mode="production", test_only=False, storage_root=tmp_path / "TEST_ONLY")


def test_invalid_configuration_does_not_print_credentials():
    with pytest.raises(ValidationError) as error:
        Settings(mode="production", database_url="mysql+pymysql://root:PRIVATE_SECRET@host/db")
    assert "PRIVATE_SECRET" not in str(error.value)
