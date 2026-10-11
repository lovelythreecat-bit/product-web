"""Actual MySQL policy constraints and caller-owned transactions, never SQLite."""

import importlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.common.types import Principal, UserRole

pytestmark = pytest.mark.integration
OWNER = UUID("00000000-0000-4000-8000-000000000002")


def actor():
    return Principal(user_id=OWNER, role=UserRole.ADMIN, session_id=uuid4(), auth_version=1)


def draft(version=None):
    schema = importlib.import_module("app.policies.schemas")
    return schema.DecisionVersion(
        decision_id="D-05",
        version=version or uuid4().hex,
        mode="production",
        test_only=False,
        status="draft",
        payload={"registration": {"credits": 12}, "assist": {"scheme": "UNDECIDED"}},
    )


def service(session):
    module = importlib.import_module("app.policies.service")
    # Explicit test authority; production must supply T04 current-session + permission validation.
    return module.PolicyService(session, confirmation_authorizer=lambda principal, id: OWNER)


def test_confirmation_and_gate_are_visible_then_rolled_back_by_caller(db_session):
    original = draft()
    policies = service(db_session)
    policies.add_draft(original)
    before = datetime.now(UTC)
    confirmed = policies.confirm_decision(
        actor(), "D-05", original.version, ["TEST_EVIDENCE:review"]
    )
    assert confirmed.confirmed_by == OWNER
    assert confirmed.confirmed_at >= before
    assert confirmed.evidence_refs == ("TEST_EVIDENCE:review",)
    assert confirmed.payload["assist"]["scheme"] == "UNDECIDED"
    receipt = policies.require_feature("registration", "production", {"D-05": original.version})
    assert receipt.decision_versions == {"D-05": original.version}
    assert db_session.in_transaction()
    db_session.rollback()
    assert (
        db_session.execute(
            text("SELECT COUNT(*) FROM decision_versions WHERE version=:v"), {"v": original.version}
        ).scalar_one()
        == 0
    )


def test_database_rejects_duplicate_version_even_bypassing_service(db_session):
    original = draft()
    service(db_session).add_draft(original)
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text("""INSERT INTO decision_versions
            (decision_id, version, mode, test_only, status, payload, evidence_refs)
            VALUES ('D-05', :v, 'production', 0, 'draft', '{}', '[]')"""),
            {"v": original.version},
        )


@pytest.mark.parametrize(
    "mode,test_only,status,owner,at,evidence",
    [
        ("production", 1, "draft", None, None, "[]"),
        ("mock", 0, "draft", None, None, "[]"),
        ("production", 0, "confirmed", None, None, "[]"),
        ("production", 0, "confirmed", str(OWNER), datetime(2026, 10, 11), "[]"),
        ("production", 0, "invalid", None, None, "[]"),
    ],
)
def test_database_checks_environment_and_confirmation_metadata(
    db_session, mode, test_only, status, owner, at, evidence
):
    with pytest.raises(DBAPIError) as caught, db_session.begin_nested():
        db_session.execute(
            text("""INSERT INTO decision_versions
            (decision_id, version, mode, test_only, status, payload,
             confirmed_by, confirmed_at, evidence_refs)
            VALUES ('D-05', :v, :mode, :test, :status, '{}', :owner, :at, :evidence)"""),
            {
                "v": uuid4().hex,
                "mode": mode,
                "test": test_only,
                "status": status,
                "owner": owner,
                "at": at,
                "evidence": evidence,
            },
        )

    assert caught.value.orig.args[0] == 3819  # MySQL ER_CHECK_CONSTRAINT_VIOLATED


def test_database_protects_payload_and_confirmed_history(db_session):
    original = draft()
    policies = service(db_session)
    policies.add_draft(original)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(
            text("UPDATE decision_versions SET payload='{}' WHERE version=:v"),
            {"v": original.version},
        )
    policies.confirm_decision(actor(), "D-05", original.version, ["TEST_EVIDENCE:review"])
    for sql in (
        "UPDATE decision_versions SET status='draft' WHERE version=:v",
        "DELETE FROM decision_versions WHERE version=:v",
    ):
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(sql), {"v": original.version})
    assert policies.require_feature(
        "registration", "production", {"D-05": original.version}
    ).decision_versions == {"D-05": original.version}


def test_confirmed_version_cannot_be_reconfirmed_or_replaced(db_session):
    module = importlib.import_module("app.policies.service")
    original = draft()
    policies = service(db_session)
    policies.add_draft(original)
    policies.confirm_decision(actor(), "D-05", original.version, ["TEST_EVIDENCE:review"])
    with pytest.raises(module.PolicyConflictError):
        policies.confirm_decision(actor(), "D-05", original.version, ["TEST_EVIDENCE:replacement"])
    with pytest.raises(module.PolicyConflictError):
        policies.add_draft(original)


def test_wrong_version_and_gate_failure_do_not_flush_pending_writes(db_session):
    module = importlib.import_module("app.policies.service")
    models = importlib.import_module("app.policies.models")
    pending = models.DecisionVersionRecord(
        decision_id="D-05",
        version=uuid4().hex,
        mode="production",
        test_only=False,
        status="draft",
        payload={},
        evidence_refs=[],
    )
    db_session.add(pending)
    with pytest.raises(module.PolicyGateError):
        service(db_session).require_feature("registration", "production", {"D-05": "absent"})
    assert pending in db_session.new


def test_no_authorizer_and_mismatched_identity_cannot_confirm(db_session):
    module = importlib.import_module("app.policies.service")
    original = draft()
    service(db_session).add_draft(original)
    for authority in (None, lambda principal, id: uuid4()):
        policies = module.PolicyService(db_session, confirmation_authorizer=authority)
        with pytest.raises(module.PolicyAuthorizationError):
            policies.confirm_decision(actor(), "D-05", original.version, ["TEST_EVIDENCE:review"])
    assert (
        db_session.execute(
            text("SELECT status FROM decision_versions WHERE version=:v"), {"v": original.version}
        ).scalar_one()
        == "draft"
    )


def test_old_version_remains_available_after_new_version(db_session):
    policies = service(db_session)
    old, new = draft(), draft()
    policies.add_draft(old)
    policies.confirm_decision(actor(), "D-05", old.version, ["TEST_EVIDENCE:old"])
    policies.add_draft(new)
    policies.confirm_decision(actor(), "D-05", new.version, ["TEST_EVIDENCE:new"])
    receipt = policies.require_feature("registration", "production", {"D-05": old.version})
    assert receipt.decision_versions == {"D-05": old.version}


@pytest.fixture
def policy_selects(db_session):
    """Observe real SQL execution; never replace the service or repository."""
    from sqlalchemy import event

    reads = []
    connection = db_session.connection()

    def capture(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT") and "decision_versions" in statement:
            reads.append(tuple(parameters.values()))

    event.listen(connection, "before_cursor_execute", capture)
    try:
        yield reads
    finally:
        event.remove(connection, "before_cursor_execute", capture)


@pytest.mark.parametrize("unrelated_version", ["absent-unrelated", None, 123, {"invalid": True}])
def test_registration_ignores_unrelated_decision_without_reading_it(
    db_session, policy_selects, unrelated_version
):
    models = importlib.import_module("app.policies.models")
    policies = service(db_session)
    original = draft()
    policies.add_draft(original)
    policies.confirm_decision(actor(), "D-05", original.version, ["TEST_EVIDENCE:fix1"])
    pending = models.DecisionVersionRecord(
        decision_id="D-07",
        version=uuid4().hex,
        mode="production",
        test_only=False,
        status="draft",
        payload={},
        evidence_refs=[],
    )
    db_session.add(pending)
    policy_selects.clear()
    receipt = policies.require_feature(
        "registration",
        "production",
        {
            "D-05": original.version,
            "D-07": unrelated_version,
        },
    )
    assert receipt.decision_versions == {"D-05": original.version}
    assert len(policy_selects) == 1
    assert "D-05" in policy_selects[0] and original.version in policy_selects[0]
    assert pending in db_session.new  # A successful lazy read also must not autoflush.
    db_session.rollback()
    assert (
        db_session.execute(
            text("SELECT COUNT(*) FROM decision_versions WHERE version=:v"), {"v": original.version}
        ).scalar_one()
        == 0
    )


@pytest.mark.parametrize("kind", ["single", "multiple", "detail_images"])
def test_spec_gate_reads_delivery_policy_only_for_applicable_shapes(
    db_session, policy_selects, kind
):
    schemas = importlib.import_module("app.policies.schemas")
    module = importlib.import_module("app.policies.service")
    policies = service(db_session)
    versions = {}
    for id, payload in (
        (
            "D-02",
            {
                "specs": {
                    "card": {
                        "agent_id": "copy",
                        "agent_version": "agent-v1",
                        "parameter_schema_ref": "schema:v1",
                        "validation_evidence_ref": "validation:v1",
                        "delivery_kind": kind,
                    }
                }
            },
        ),
        ("D-05", {"prices": {"card": {"credits": 4}}}),
    ):
        record = schemas.DecisionVersion(
            decision_id=id, version=uuid4().hex, mode="production", test_only=False, payload=payload
        )
        policies.add_draft(record)
        policies.confirm_decision(actor(), id, record.version, ["TEST_EVIDENCE:fix1"])
        versions[id] = record.version
    versions["D-04"] = "absent-delivery"
    policy_selects.clear()
    if kind == "single":
        receipt = policies.require_feature("spec.card.published", "production", versions)
        assert receipt.decision_versions == {"D-02": versions["D-02"], "D-05": versions["D-05"]}
        assert len(policy_selects) == 2
        assert all("D-04" not in parameters for parameters in policy_selects)
    else:
        with pytest.raises(module.PolicyGateError) as caught:
            policies.require_feature("spec.card.published", "production", versions)
        assert caught.value.status_code == 403
        assert len(policy_selects) == 3
        assert "D-04" in policy_selects[-1] and "absent-delivery" in policy_selects[-1]


@pytest.mark.parametrize("versions", [{}, {"D-05": "absent"}, {"D-05": None}, {"D-05": 123}])
def test_required_unknown_or_invalid_version_still_blocks(db_session, policy_selects, versions):
    module = importlib.import_module("app.policies.service")
    with pytest.raises(module.PolicyGateError) as caught:
        service(db_session).require_feature("registration", "production", versions)
    assert caught.value.status_code == 403
    assert caught.value.code == "FEATURE_NOT_ENABLED"
    assert not db_session.new and not db_session.dirty


def test_unknown_feature_does_not_read_unrelated_decisions(db_session, policy_selects):
    module = importlib.import_module("app.policies.service")
    with pytest.raises(module.PolicyGateError) as caught:
        service(db_session).require_feature("unknown_feature", "production", {"D-05": "absent"})
    assert caught.value.status_code == 403
    assert policy_selects == []
