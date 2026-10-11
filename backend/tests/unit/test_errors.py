from uuid import UUID

from fastapi.testclient import TestClient
from pydantic import BaseModel

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
