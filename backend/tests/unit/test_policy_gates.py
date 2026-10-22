"""Policy failures must remain closed before later services perform side effects."""

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[3]
OWNER = UUID("00000000-0000-4000-8000-000000000002")


def api():
    return importlib.import_module("app.policies.service")


def decision(id="D-05", *, mode="production", status="confirmed", payload=None, version="v1"):
    schemas = importlib.import_module("app.policies.schemas")
    return schemas.DecisionVersion(
        decision_id=id,
        version=version,
        mode=mode,
        test_only=mode == "mock",
        status=status,
        payload=payload if payload is not None else {"registration": {"credits": 12}},
        confirmed_by=OWNER if status == "confirmed" else None,
        confirmed_at=datetime(2026, 10, 11, tzinfo=UTC) if status == "confirmed" else None,
        evidence_refs=("TEST_EVIDENCE:unit-policy",) if status == "confirmed" else (),
    )


def denied(feature, mode, versions):
    service = api()
    with pytest.raises(service.PolicyGateError) as caught:
        service.require_feature(feature, mode, versions)
    assert caught.value.status_code == 403
    assert caught.value.code == "FEATURE_NOT_ENABLED"


def test_missing_decision_blocks_feature():
    denied("registration", "production", {})


def test_count_only_d05_not_assist_policy():
    d05 = decision(payload={"registration": {"credits": 12}, "assist": {"scheme": "UNDECIDED"}})
    receipt = api().require_feature("registration", "production", {"D-05": d05})
    assert receipt.decision_versions == {"D-05": "v1"}
    assert receipt.test_only is False
    denied("prompt_assist", "production", {"D-05": d05})
    assert d05.payload["assist"]["scheme"] == "UNDECIDED"


@pytest.mark.parametrize("mode", ["staging", "production"])
def test_mock_not_production(mode):
    denied("registration", mode, {"D-05": decision(mode="mock")})


@pytest.mark.parametrize(
    "source,target", [("staging", "production"), ("production", "staging"), ("production", "mock")]
)
def test_approval_is_bound_to_exact_environment(source, target):
    denied("registration", target, {"D-05": decision(mode=source)})


def test_draft_cannot_open_real_feature():
    denied("registration", "production", {"D-05": decision(status="draft")})


@pytest.mark.parametrize("credits", [None, True, -1, "12"])
def test_invalid_business_value_does_not_open_registration(credits):
    denied(
        "registration",
        "production",
        {"D-05": decision(payload={"registration": {"credits": credits}})},
    )


def test_unknown_feature_and_wrong_decision_identity_are_denied():
    denied("future_payment", "production", {"D-05": decision()})
    denied("registration", "production", {"D-05": decision(id="D-04")})


def test_mock_fixture_is_test_only_and_cannot_open_staging():
    raw = json.loads((ROOT / "contracts/fixtures/policies/mock.yaml").read_text("utf-8"))
    schemas = importlib.import_module("app.policies.schemas")
    versions = {
        item["decision_id"]: schemas.DecisionVersion.model_validate(item)
        for item in raw["decisions"]
    }
    receipt = api().require_feature("registration", "mock", versions)
    assert receipt.test_only is True
    assert receipt.mode == "mock"
    denied("registration", "staging", versions)


def test_initial_twelve_drafts_never_enable_production():
    schemas = importlib.import_module("app.policies.schemas")
    versions = {}
    for index in range(1, 13):
        path = ROOT / f"contracts/policies/D-{index:02}.yaml"
        record = schemas.DecisionVersion.model_validate(json.loads(path.read_text("utf-8")))
        assert record.status == "draft"
        assert record.confirmed_by is None
        assert record.confirmed_at is None
        assert record.evidence_refs == ()
        versions[record.decision_id] = record
    for feature in (
        "registration",
        "prompt_assist",
        "agent.copy.generation",
        "spec.card.published",
        "upload",
        "delete",
        "account_disable",
        "public_site",
        "actual_cost",
    ):
        denied(feature, "production", versions)


def test_assist_requires_explicit_scheme_and_implementation():
    for assist in (
        {"quota": {"count": 3}},
        {"scheme": "UNDECIDED", "count": 3},
        {"scheme": "INDEPENDENT_FREE_QUOTA", "policy_ref": "p"},
    ):
        denied("prompt_assist", "production", {"D-05": decision(payload={"assist": assist})})
    valid = {
        "scheme": "INDEPENDENT_FREE_QUOTA",
        "policy_ref": "approved-policy:v2",
        "implementation_ref": "verified-implementation:v2",
        "quota": {"count": 3, "decrement_ref": "on-success", "reset_ref": "daily-rule"},
    }
    receipt = api().require_feature(
        "prompt_assist", "production", {"D-05": decision(payload={"assist": valid}, version="v2")}
    )
    assert receipt.decision_versions == {"D-05": "v2"}


def spec_versions(delivery_kind="single"):
    return {
        "D-02": decision(
            "D-02",
            payload={
                "specs": {
                    "card": {
                        "agent_id": "copy",
                        "agent_version": "agent-v1",
                        "parameter_schema_ref": "schema:v1",
                        "validation_evidence_ref": "validation:v1",
                        "delivery_kind": delivery_kind,
                    }
                }
            },
        ),
        "D-05": decision(payload={"prices": {"card": {"credits": 4}}}),
    }


def test_multiresolution_spec_requires_d04_for_that_exact_spec():
    versions = spec_versions("multiple")
    denied("spec.card.published", "production", versions)
    versions["D-04"] = decision(
        "D-04",
        payload={
            "specs": {
                "other": {
                    "delivery_ref": "complete",
                    "partial_failure_ref": "rules",
                    "billing_ref": "rules",
                    "missing_results_evidence_ref": "examples",
                }
            }
        },
    )
    denied("spec.card.published", "production", versions)
    versions["D-04"] = decision(
        "D-04",
        payload={
            "specs": {
                "card": {
                    "delivery_ref": "complete",
                    "partial_failure_ref": "rules",
                    "billing_ref": "rules",
                    "missing_results_evidence_ref": "examples",
                }
            }
        },
    )
    receipt = api().require_feature("spec.card.published", "production", versions)
    assert receipt.decision_versions == {"D-02": "v1", "D-05": "v1", "D-04": "v1"}


def test_single_spec_does_not_require_undecided_d04_or_cost_source():
    receipt = api().require_feature("spec.card.published", "production", spec_versions())
    assert receipt.decision_versions == {"D-02": "v1", "D-05": "v1"}


def test_real_generation_requires_target_agent_and_all_recovery_policies():
    denied(
        "agent.copy.generation",
        "production",
        {"D-01": decision("D-01", payload={"agents": {"video": {"protocol_version": "v1"}}})},
    )


def test_confirmation_rejects_unverified_actor_before_repository_access():
    service = api()
    # A Session without a bind would fail if rejection attempted any database IO.
    from sqlalchemy.orm import Session

    with Session() as session:
        policies = service.PolicyService(session)
        with pytest.raises(service.PolicyAuthorizationError):
            policies.confirm_decision("admin", "D-05", "v1", ["evidence:v1"])
        assert not session.new and not session.dirty


def test_generation_policy_matrix_checks_all_prerequisites_and_protocol_versions():
    versions = {
        "D-01": decision(
            "D-01",
            payload={
                "agents": {
                    "copy": {
                        "protocol_version": "v1",
                        "input_schema_ref": "schema:v1",
                        "authentication_ref": "auth:v1",
                        "execution_ref": "execution:v1",
                        "completion_ref": "completion:v1",
                        "recovery_ref": "recovery:v1",
                        "callback_ref": "callbacks:v1",
                        "error_ref": "errors:v1",
                        "usage_ref": "usage:v1",
                        "capabilities_ref": "capabilities:v1",
                    }
                }
            },
        ),
        "D-03": decision(
            "D-03",
            payload={
                "agents": {
                    "copy": {
                        "protocol_version": "v1",
                        "validation_ref": "validation:v1",
                        "supported_inputs_ref": "supported-inputs:v1",
                    }
                }
            },
        ),
        "D-05": decision(
            payload={"generation": {"max_concurrent_tasks": 2, "enforcement_ref": "concurrency:v1"}}
        ),
        "D-08": decision(
            "D-08",
            payload={
                "generation": {
                    "investigation_deadline_seconds": 120,
                    "responsible_party_ref": "oncall:v1",
                    "settlement_evidence_ref": "evidence:v1",
                    "late_delivery_ref": "late:v1",
                    "save_failure_ref": "save:v1",
                    "deadline_is_failure": False,
                    "requires_complete_delivery": True,
                }
            },
        ),
        "D-09": decision(
            "D-09",
            payload={
                "generation": {
                    "inflight_protection_ref": "inflight:v1",
                    "exception_handoff_ref": "handoff:v1",
                    "disabled_account_tasks_ref": "disabled:v1",
                }
            },
        ),
        "D-10": decision(
            "D-10",
            payload={
                "generation": {
                    "account_quota_bytes": 1024,
                    "server_budget_bytes": 4096,
                    "estimation_ref": "estimate:v1",
                    "reservation_seconds": 300,
                    "reclamation_ref": "reclaim:v1",
                    "alert_ref": "alert:v1",
                    "allowed_download_sources": ["provider.invalid"],
                    "max_download_bytes": 1024,
                    "download_timeout_seconds": 10,
                    "max_redirects": 0,
                    "link_validity_ref": "links:v1",
                    "recovery_ref": "recover:v1",
                }
            },
        ),
    }
    receipt = api().require_feature("agent.copy.generation", "production", versions)
    assert receipt.decision_versions == {
        "D-01": "v1",
        "D-03": "v1",
        "D-05": "v1",
        "D-08": "v1",
        "D-09": "v1",
        "D-10": "v1",
    }
    for id in ("D-01", "D-03", "D-05", "D-08", "D-09", "D-10"):
        denied(
            "agent.copy.generation", "production", {k: v for k, v in versions.items() if k != id}
        )
    versions["D-03"].payload["agents"]["copy"]["protocol_version"] = "v2"
    denied("agent.copy.generation", "production", versions)
    versions["D-03"].payload["agents"]["copy"]["protocol_version"] = "v1"
    versions["D-08"].payload["generation"]["deadline_is_failure"] = True
    denied("agent.copy.generation", "production", versions)


@pytest.mark.parametrize(
    "feature,id,section,content",
    [
        (
            "upload",
            "D-10",
            "upload",
            {
                "max_file_bytes": 512,
                "allowed_types": ["image/png"],
                "reservation_seconds": 120,
                "reclamation_ref": "reclaim:v1",
                "alert_ref": "alerts:v1",
            },
        ),
        (
            "delete",
            "D-09",
            "delete",
            {
                "list_history_ref": "history:v1",
                "old_links_ref": "links:v1",
                "restoration_ref": "restore:v1",
                "retention_reclamation_ref": "retention:v1",
                "capacity_ref": "capacity:v1",
                "inflight_protection_ref": "inflight:v1",
            },
        ),
        (
            "account_disable",
            "D-09",
            "account_disable",
            {
                "tasks_ref": "tasks:v1",
                "frozen_credits_ref": "credits:v1",
                "works_access_ref": "works:v1",
                "restoration_ref": "restore:v1",
                "exception_handoff_ref": "handoff:v1",
            },
        ),
        (
            "actual_cost",
            "D-06",
            "cost",
            {
                "source_ref": "provider:usage",
                "unit": "TEST_ONLY-credit",
                "accounting_ref": "accounting:v1",
            },
        ),
        (
            "account_recovery",
            "D-07",
            "recovery",
            {
                "identity_verification_ref": "identity:v1",
                "permissions_ref": "permissions:v1",
                "audit_ref": "audit:v1",
            },
        ),
    ],
)
def test_independent_features_require_their_complete_policy(feature, id, section, content):
    versions = {id: decision(id, payload={section: content})}
    receipt = api().require_feature(feature, "production", versions)
    assert receipt.decision_versions == {id: "v1"}
    # Every documented obligation matters: dropping any required field must close its feature.
    for field in content:
        reduced = {key: value for key, value in content.items() if key != field}
        denied(feature, "production", {id: decision(id, payload={section: reduced})})


def test_public_site_and_case_cannot_bypass_launch_or_case_authorization():
    versions = {
        "D-07": decision("D-07", payload={"login_help": {"instructions_ref": "help:v1"}}),
        "D-11": decision(
            "D-11",
            payload={
                "site": {
                    "name_brand_ref": "brand:v1",
                    "content_ref": "content:v1",
                    "visual_ref": "visual:v1",
                },
                "cases": {
                    "case1": {
                        "source_work_ref": "work:1",
                        "owner_ref": "owner:1",
                        "authorization_ref": "auth:1",
                        "withdrawal_ref": "withdraw:1",
                        "public_copy_cleanup_ref": "cleanup:1",
                        "is_mock": False,
                    }
                },
            },
        ),
        "D-12": decision(
            "D-12",
            payload={
                "deployment": {
                    "environment_ref": "environment:v1",
                    "persistent_root_ref": "storage:v1",
                    "consistent_backup_ref": "backup:v1",
                    "restore_drill_evidence_ref": "restore:v1",
                    "rpo_seconds": 60,
                    "rto_seconds": 120,
                    "monitoring_ref": "monitor:v1",
                    "public_terms_ref": "terms:v1",
                }
            },
        ),
    }
    assert api().require_feature("public_site", "production", versions).test_only is False
    assert api().require_feature("case.case1.published", "production", versions).test_only is False
    denied("case.case2.published", "production", versions)
    versions["D-11"].payload["cases"]["case1"]["is_mock"] = True
    denied("case.case1.published", "production", versions)
    versions.pop("D-12")
    denied("public_site", "production", versions)


def test_tampered_confirmation_metadata_cannot_open_gate():
    original = decision()
    for changes in (
        {"confirmed_by": None},
        {"confirmed_at": None},
        {"evidence_refs": ()},
        {"test_only": True},
    ):
        denied("registration", "production", {"D-05": original.model_copy(update=changes)})
