"""T20a: small real-MySQL API permission, CAS and exact approval checks."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.common.types import Principal
from app.policies.schemas import DecisionVersion
from app.policies.service import PolicyService
from app.site.schemas import SiteContent
from app.site.service import content_digest
from tests.integration.test_admin_access import identity, login


@pytest.fixture
def site_desk(auth_client, mysql_engine):
    with Session(mysql_engine) as session, session.begin():
        admin, user = identity(session), identity(session, "user")
    login(auth_client, admin)
    return auth_client, admin, user


def body(version, label="TEST_ONLY site draft"):
    return dict(
        expected_version=version,
        policy_version="TEST_ONLY_unresolved",
        content=dict(
            product_intro=label,
            agent_descriptions=dict(
                text="TEST_ONLY text", image="TEST_ONLY image", video="TEST_ONLY video"
            ),
            process_steps=["TEST_ONLY prepare", "TEST_ONLY create"],
        ),
    )


def policies(session, admin, content, *, confirmed=True, cases=None):
    version = "TEST_ONLY_" + uuid4().hex
    payloads = {
        "D-07": {"login_help": {"instructions_ref": "TEST_ONLY_help"}},
        "D-11": {
            "site": {
                "name_brand_ref": "TEST_ONLY_brand",
                "visual_ref": "TEST_ONLY_visual",
                "content_ref": "sha256:" + content_digest(SiteContent.model_validate(content)),
            },
            "cases": cases or {},
        },
        "D-12": {
            "deployment": {
                **{
                    k: "TEST_ONLY_evidence"
                    for k in (
                        "environment_ref",
                        "persistent_root_ref",
                        "consistent_backup_ref",
                        "restore_drill_evidence_ref",
                        "monitoring_ref",
                        "public_terms_ref",
                    )
                },
                "rpo_seconds": 0,
                "rto_seconds": 60,
            }
        },
    }
    principal = Principal(
        user_id=UUID(admin["id"]), session_id=UUID(admin["sid"]), role="admin", auth_version=0
    )
    service = PolicyService(session, confirmation_authorizer=lambda actor, decision: actor.user_id)
    for decision, payload in payloads.items():
        service.add_draft(
            DecisionVersion(
                decision_id=decision, version=version, mode="mock", test_only=True, payload=payload
            )
        )
        if confirmed:
            service.confirm_decision(
                principal, decision, version, ["TEST_ONLY_explicit_fixture_approval"]
            )
    return version


def test_site_permission_cas_draft_and_audit(site_desk, mysql_engine):
    client, admin, user = site_desk
    baseline = client.get("/api/v1/admin/site/content").json()
    public_before = client.get("/api/v1/site/content").json()
    dto = body(baseline["version"], "TEST_ONLY_PRIVATE_DRAFT_" + uuid4().hex)
    with Session(mysql_engine) as session:
        count = session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.action == "site_content_update")
        )
    login(client, user)
    assert client.patch("/api/v1/admin/site/content", json=dto).status_code == 403
    client.cookies.clear()
    assert client.patch("/api/v1/admin/site/content", json=dto).status_code == 401
    login(client, admin)
    assert client.get("/api/v1/admin/site/content").json() == baseline
    with Session(mysql_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.action == "site_content_update")
            )
            == count
        )
    saved = client.patch("/api/v1/admin/site/content", json=dto)
    assert saved.status_code == 200, saved.text
    assert saved.json()["status"] == "draft"
    assert client.get("/api/v1/site/content").json() == public_before
    assert client.patch("/api/v1/admin/site/content", json=dto).status_code == 409
    assert client.get("/api/v1/admin/site/content").json() == saved.json()
    with Session(mysql_engine) as session:
        event = session.scalars(
            select(AuditEvent).where(
                AuditEvent.actor_id == admin["id"], AuditEvent.action == "site_content_update"
            )
        ).one()
        assert event.created_at and event.changes["before_version"] == baseline["version"]
        assert event.changes["after_version"] == saved.json()["version"]
        assert dto["content"]["product_intro"] not in str(event.changes)


def test_only_exact_confirmed_content_public_even_in_mock(site_desk, mysql_engine):
    client, admin, _ = site_desk
    start = client.get("/api/v1/admin/site/content").json()["version"]
    before = client.get("/api/v1/site/content").json()
    dto = body(start, "TEST_ONLY approval fixture " + uuid4().hex)
    with Session(mysql_engine) as session, session.begin():
        draft_policy = policies(session, admin, dto["content"], confirmed=False)
        confirmed = policies(session, admin, dto["content"])
    dto.update(
        policy_version=draft_policy, policy_versions={"D-07": draft_policy, "D-12": draft_policy}
    )
    draft = client.patch("/api/v1/admin/site/content", json=dto)
    assert draft.status_code == 200 and draft.json()["status"] == "draft"
    assert client.get("/api/v1/site/content").json() == before
    dto.update(
        expected_version=draft.json()["version"],
        policy_version=confirmed,
        policy_versions={"D-07": confirmed, "D-12": confirmed},
    )
    approved = client.patch("/api/v1/admin/site/content", json=dto)
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    assert client.get("/api/v1/site/content").json()["content"] == approved.json()
    dto["expected_version"] = approved.json()["version"]
    dto["content"]["product_intro"] = "TEST_ONLY unapproved edit"
    assert client.patch("/api/v1/admin/site/content", json=dto).json()["status"] == "draft"
    assert client.get("/api/v1/site/content").json()["content"] == approved.json()
