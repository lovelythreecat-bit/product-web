from uuid import UUID

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.common.errors import register_error_handlers
from app.config import Settings
from app.main import create_app


class SensitiveInput(BaseModel):
    amount: int


def test_validation_error_has_trace_without_echoing_private_input():
    app = create_app(Settings())

    @app.post("/probe")
    def probe(payload: SensitiveInput):
        return payload

    with TestClient(app) as client:
        response = client.post("/probe", json={"amount": "PRIVATE_PASSWORD"})
    assert response.status_code == 422
    assert "PRIVATE_PASSWORD" not in response.text
    assert response.json()["error"]["code"] == "INPUT_INVALID"
    assert UUID(response.json()["trace_id"])


def test_unexpected_error_is_sanitized_and_has_trace():
    app = create_app(Settings())

    @app.get("/probe")
    def probe():
        raise RuntimeError("SECRET_CONNECTION_STRING")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/probe")
    assert response.status_code == 500
    assert "SECRET_CONNECTION_STRING" not in response.text
    assert response.headers.get("content-type", "").startswith("application/json")
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert UUID(response.json()["trace_id"])


def test_database_failure_logs_only_type_code_and_response_trace(caplog):
    import pymysql
    from sqlalchemy.exc import OperationalError

    app = create_app(Settings())

    @app.post("/probe")
    def probe():
        raise OperationalError(
            "SELECT PRIVATE_SQL", {"password": "PRIVATE_PASSWORD"},
            pymysql.OperationalError(2013, "PRIVATE_CONNECTION_DETAILS"),
        )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/probe")
    assert response.status_code == 500
    assert "OperationalError" in caplog.text
    assert "2013" in caplog.text
    assert response.json()["trace_id"] in caplog.text
    for private in ("PRIVATE_SQL", "PRIVATE_PASSWORD", "PRIVATE_CONNECTION_DETAILS"):
        assert private not in caplog.text
        assert private not in response.text


@pytest.mark.parametrize("status,fragment", [
    (503, "辅助服务暂时不可用"),
    (504, "辅助响应超时"),
])
def test_assist_provider_errors_explain_retry_without_exposing_upstream(status, fragment):
    app = FastAPI()
    register_error_handlers(app)

    @app.post("/api/v1/assist/prompts")
    def probe():
        raise HTTPException(status, detail="PRIVATE_UPSTREAM_KEY_AND_RESPONSE")

    with TestClient(app) as client:
        response = client.post("/api/v1/assist/prompts")
    assert response.status_code == status
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert fragment in response.json()["error"]["message"]
    assert "PRIVATE_UPSTREAM" not in response.text
    assert UUID(response.json()["trace_id"])
