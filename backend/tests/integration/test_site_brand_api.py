"""Real HTTP and MySQL persistence; only isolated integration services are allowed."""

from sqlalchemy.orm import Session

from tests.integration.test_admin_access import identity, login


def test_brand_public_read_admin_write_csrf_and_conflict(auth_client, mysql_engine):
    client = auth_client
    with Session(mysql_engine) as session, session.begin():
        admin, user = identity(session), identity(session, "user")
    baseline = client.get("/api/v1/site/brand").json()
    dto = {"name": "TEST_ONLY 品牌", "expected_version": baseline["version"]}
    assert client.patch("/api/v1/admin/site/brand", json=dto).status_code == 401
    login(client, user)
    assert client.patch("/api/v1/admin/site/brand", json=dto).status_code == 403
    login(client, admin)
    assert client.patch(
        "/api/v1/admin/site/brand", json=dto, headers={"X-CSRF-Token": "wrong"}
    ).status_code == 403
    response = client.patch("/api/v1/admin/site/brand", json=dto)
    assert response.status_code == 200, response.text
    assert client.get("/api/v1/site/brand").json() == response.json()
    assert client.patch("/api/v1/admin/site/brand", json=dto).status_code == 409
    # Restore the original display value; retain monotonic version and audit history.
    assert client.patch("/api/v1/admin/site/brand", json={
        "name": baseline["name"], "expected_version": response.json()["version"]
    }).status_code == 200
