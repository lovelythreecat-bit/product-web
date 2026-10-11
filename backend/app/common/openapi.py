from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic.json_schema import models_json_schema

from app.common.errors import ErrorResponse
from app.common.types import (
    AdmissionResult,
    CursorPage,
    FileVersionRef,
    InputSnapshot,
    PageQuery,
    Principal,
    Quote,
    SubmitTaskRequest,
    TaskView,
)

CONTRACT_MODELS = [
    Principal,
    FileVersionRef,
    InputSnapshot,
    Quote,
    SubmitTaskRequest,
    TaskView,
    AdmissionResult,
    PageQuery,
    CursorPage[TaskView],
    ErrorResponse,
]


def install_openapi(app: FastAPI) -> None:
    def platform_openapi() -> dict:
        if app.openapi_schema is None:
            schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
            # Runtime intentionally uses 401/403 for missing security values instead of
            # FastAPI's body-validation 422. They are still mandatory client contracts.
            for path in schema["paths"].values():
                for operation in path.values():
                    if not isinstance(operation, dict):
                        continue
                    for parameter in operation.get("parameters", []):
                        if (
                            parameter["in"] == "header"
                            and parameter["name"].lower()
                            in {"origin", "x-requested-with", "x-csrf-token"}
                        ) or (
                            parameter["in"] == "cookie"
                            and parameter["name"] in {"session", "csrf_token"}
                        ):
                            parameter["required"] = True
                            parameter["schema"] = {"type": "string"}
            _, definitions = models_json_schema(
                [(model, "validation") for model in CONTRACT_MODELS],
                ref_template="#/components/schemas/{model}",
            )
            schema.setdefault("components", {}).setdefault("schemas", {}).update(
                definitions["$defs"]
            )
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = platform_openapi
