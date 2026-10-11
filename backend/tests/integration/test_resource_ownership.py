"""Every existing content entry point is exercised with two persisted accounts."""

import importlib.util
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.auth.models import AuthSession, User
from app.common.types import Principal
from app.conversations.models import ProductVersion
from app.tasks.models import TaskSnapshot
from tests.integration import test_works_history as works_fixtures

base_upstream = works_fixtures.base_upstream
published = works_fixtures.published
ready = works_fixtures.ready
upstream = works_fixtures.upstream
works_task = works_fixtures.works_task


def test_guess_other_user_all_resources_files(published, upstream):
    client, create, login = published
    victim, attacker = create(), create(owner="b")
    login(victim["user_id"])
    response = client.get("/api/v1/works/" + victim["work_id"])
    assert response.status_code == 200, response.text
    detail = response.json()
    with upstream[0]() as s:
        version = s.get(TaskSnapshot, victim["task_id"]).input_snapshot["product_version"]
    login(attacker["user_id"])
    paths = [
        "/works/" + victim["work_id"],
        "/tasks/" + victim["task_id"],
        "/conversations/" + victim["conversation_id"],
        "/products/versions/" + version,
        "/tasks?conversation_id=" + victim["conversation_id"],
    ]
    for path in paths:
        result = client.get("/api/v1" + path)
        assert result.status_code == 404, (path, result.text)
        assert victim["task_id"] not in result.text
    for item in detail["items"]:
        for range_value in (None, "bytes=0-3", "bytes=999999-", "invalid"):
            result = client.get(
                item["content_url"], headers={"Range": range_value} if range_value else {}
            )
            assert result.status_code == 404
    assert client.get("/api/v1/works", params={"cursor": victim["work_id"]}).status_code == 404
    assert client.get("/api/v1/works", params={"cursor": str(uuid4())}).status_code == 404
    for route, cursor in [
        ("conversations", victim["conversation_id"]),
        ("tasks", victim["task_id"]),
    ]:
        foreign = client.get("/api/v1/" + route, params={"cursor": cursor})
        missing = client.get("/api/v1/" + route, params={"cursor": str(uuid4())})
        assert foreign.status_code == missing.status_code == 422
        assert foreign.json()["error"]["code"] == missing.json()["error"]["code"]
    history = client.get(
        "/api/v1/conversations/" + attacker["conversation_id"],
        params={"message_cursor": detail["message_id"]},
    )
    assert history.status_code == 422
    assert {w["work_id"] for w in client.get("/api/v1/works").json()["items"]} == {
        attacker["work_id"]
    }
    # The ordinary administrator role cannot become a private-content bypass.
    with upstream[0]() as s, s.begin():
        s.get(User, attacker["user_id"]).role = "admin"
    assert client.get("/api/v1/works/" + victim["work_id"]).status_code == 404
    assert client.get(detail["items"][0]["content_url"]).status_code == 404


def test_registry_rechecks_live_session_owner_and_file_version(published, upstream):
    client, create, login = published
    victim, attacker = create(), create(owner="b")
    session_id = login(victim["user_id"])
    assert importlib.util.find_spec("app.admin"), "Resource boundary registry missing"
    from app.admin.permissions import authorize_resource

    detail = client.get("/api/v1/works/" + victim["work_id"]).json()
    with upstream[0]() as s:
        version = s.get(TaskSnapshot, victim["task_id"]).input_snapshot["product_version"]
        product = s.get(ProductVersion, version).product_id
    resources = [
        ("work", victim["work_id"]),
        ("task", victim["task_id"]),
        ("conversation", victim["conversation_id"]),
        ("message", detail["message_id"]),
        ("product", product),
        ("product_version", version),
        ("file", detail["items"][0]["file_id"]),
        ("material", detail["items"][0]["file_id"]),
    ]
    principal = Principal(
        user_id=victim["user_id"], session_id=session_id, role="user", auth_version=0
    )
    other_session = login(attacker["user_id"])
    other = principal.model_copy(
        update={"user_id": attacker["user_id"], "session_id": other_session}
    )
    for kind, identity in resources:
        with upstream[0]() as s:
            assert (
                str(authorize_resource(s, principal, kind, identity).user_id) == victim["user_id"]
            )
        with upstream[0]() as s, pytest.raises(HTTPException) as error:
            authorize_resource(s, other, kind, identity)
        assert error.value.status_code == 404
    with upstream[0]() as s, pytest.raises(HTTPException) as error:
        authorize_resource(
            s, principal, "file_version", detail["items"][0]["file_id"], version=str(uuid4())
        )
    assert error.value.status_code == 404
    with upstream[0]() as s, s.begin():
        s.get(AuthSession, session_id).revoked_at = s.get(User, victim["user_id"]).created_at
    with upstream[0]() as s, pytest.raises(HTTPException) as error:
        authorize_resource(s, principal, "work", victim["work_id"])
    assert error.value.status_code == 401
    login(victim["user_id"])
    with upstream[0]() as s, s.begin():
        s.get(User, victim["user_id"]).status = "disabled"
    assert client.get("/api/v1/works").status_code == 401
    assert client.get(detail["items"][0]["content_url"]).status_code == 401


def test_registry_documents_real_api_boundaries(published):
    from app.admin.permissions import RESOURCE_ROUTES

    client, _, _ = published
    paths = client.app.openapi()["paths"]
    for routes in RESOURCE_ROUTES.values():
        for route in routes:
            method, path = route.split(" ")
            assert method.lower() in paths[path], route
