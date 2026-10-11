"""Explicit TEST_ONLY policy/catalog seed via production services; no task/balance forgery."""

from uuid import uuid4

from app.agents.mock_server import PROTOCOL
from app.assist.provider import TEST_SCHEME
from app.auth.models import User
from app.auth.service import AuthService
from app.catalog.schemas import AgentDraft, PriceDraft, SpecDraft, content_digest
from app.catalog.service import CatalogService
from app.ledger.models import RegistrationCreditHead
from app.ledger.service import set_registration_credit_config
from app.policies.schemas import DecisionVersion
from app.policies.service import PolicyService


def seed(factory, settings, prefix, endpoint):
    def policy(session, decision, payload):
        version = "TEST_ONLY_" + uuid4().hex
        PolicyService(session).add_draft(
            DecisionVersion(
                decision_id=decision, version=version, mode="mock", test_only=True, payload=payload
            )
        )
        return version

    with factory() as s, s.begin():
        registration = policy(s, "D-05", {"registration": {"credits": 1000}})
        head = s.get(RegistrationCreditHead, "mock")
        set_registration_credit_config(
            s,
            mode="mock",
            expected_version=head.version if head else None,
            amount=1000,
            policy_version=registration,
            reason="TEST_ONLY browser harness",
        )
    with factory() as s, s.begin():
        auth = AuthService(s, mode="mock").register_account(
            prefix + "admin", "TEST_ONLY_browser_password", uuid4().hex
        )
        admin_id = str(auth.profile.user_id)
        s.get(User, admin_id).role = "admin"
    with factory() as s, s.begin():
        actor = AuthService(s, mode="mock").require_active_principal(auth.session_token)
        service = CatalogService(s, mode="mock")
        agents, specs, result_rules, agent_rules = {}, {}, {}, {}
        for kind, credits in (("copy", 8), ("image", 20), ("video", 60)):
            agent_id, spec_id = str(uuid4()), str(uuid4())
            support = dict(
                product_required_fields=["name"],
                instruction_required=False,
                min_materials=0,
                max_materials=2,
            )
            parameters = {"fields": {}, "combinations": []}
            versions = {
                "D-03": policy(
                    s,
                    "D-03",
                    {
                        "agents": {
                            agent_id: dict(
                                protocol_version=PROTOCOL,
                                validation_ref="TEST_ONLY_browser",
                                supported_inputs_ref="sha256:" + content_digest(support),
                            )
                        }
                    },
                ),
                "D-02": policy(
                    s,
                    "D-02",
                    {
                        "specs": {
                            spec_id: dict(
                                agent_id=agent_id,
                                agent_version="TEST_ONLY_v1",
                                parameter_schema_ref="sha256:" + content_digest(parameters),
                                validation_evidence_ref="TEST_ONLY_browser",
                                delivery_kind="single",
                            )
                        }
                    },
                ),
                "D-05": policy(s, "D-05", {"prices": {spec_id: {"credits": credits}}}),
            }
            service.publish_agent_version(
                actor,
                AgentDraft(
                    agent_id=agent_id,
                    version="TEST_ONLY_v1",
                    enabled=True,
                    reason="TEST_ONLY browser",
                    mode="mock",
                    test_only=True,
                    kind=kind,
                    name="TEST_ONLY " + kind,
                    protocol_version=PROTOCOL,
                    input_support=support,
                    endpoint=endpoint,
                    policy_versions={"D-03": versions["D-03"]},
                ),
            )
            spec = service.publish_spec_version(
                actor,
                SpecDraft(
                    spec_id=spec_id,
                    agent_id=agent_id,
                    agent_version="TEST_ONLY_v1",
                    version="TEST_ONLY_v1",
                    enabled=True,
                    reason="TEST_ONLY browser",
                    name="TEST_ONLY " + kind,
                    parameter_schema=parameters,
                    delivery_kind="single",
                    policy_versions=versions,
                ),
            )
            service.set_price_version(
                actor,
                PriceDraft(
                    spec_id=spec_id,
                    version="TEST_ONLY_v1",
                    enabled=True,
                    credits=credits,
                    policy_version=versions["D-05"],
                    reason="TEST_ONLY browser",
                ),
            )
            agents[kind], specs[kind] = agent_id, spec_id
            result_rules[spec_id] = dict(
                protocol_version=PROTOCOL,
                spec_version="TEST_ONLY_v1",
                spec_digest=content_digest(spec.model_dump(mode="json")),
                expected_item_keys=["original-1"],
                media_type={"copy": "text/plain", "image": "image/png", "video": "video/mp4"}[kind],
            )
            agent_rules[agent_id] = dict(
                protocol_version=PROTOCOL,
                **{
                    name: "TEST_ONLY_browser"
                    for name in (
                        "input_schema_ref",
                        "authentication_ref",
                        "execution_ref",
                        "completion_ref",
                        "recovery_ref",
                        "callback_ref",
                        "error_ref",
                        "usage_ref",
                        "capabilities_ref",
                    )
                },
            )
        generation = {
            "D-01": policy(s, "D-01", {"agents": agent_rules, "result_specs": result_rules}),
            "D-05": policy(
                s,
                "D-05",
                {
                    "generation": {"max_concurrent_tasks": 5, "enforcement_ref": "TEST_ONLY_mysql"},
                    "assist": {
                        "scheme": "OTHER_CONFIRMED_SCHEME",
                        "policy_ref": TEST_SCHEME,
                        "implementation_ref": TEST_SCHEME,
                    },
                },
            ),
            "D-08": policy(
                s,
                "D-08",
                {
                    "generation": dict(
                        investigation_deadline_seconds=60,
                        deadline_is_failure=False,
                        requires_complete_delivery=True,
                        **{
                            name: "TEST_ONLY_browser"
                            for name in (
                                "responsible_party_ref",
                                "settlement_evidence_ref",
                                "late_delivery_ref",
                                "save_failure_ref",
                            )
                        },
                    ),
                    "investigation": dict(
                        schema_version="investigations-v1",
                        deadline_seconds=60,
                        responsible_user_id=admin_id,
                        authorized_actor_ids=[admin_id],
                        escalation_ref="TEST_ONLY_browser",
                        actions=["resume_original", "confirm_failure"],
                        manual_release_basis="operator_review",
                        capacity_on_close="retain_all",
                        late_delivery="quarantine",
                        evidence_types=["review", "upstream_failure"],
                        deadline_is_failure=False,
                        requires_complete_delivery=True,
                    ),
                },
            ),
            "D-10": policy(
                s,
                "D-10",
                {
                    "generation": dict(
                        account_quota_bytes=10000000,
                        server_budget_bytes=100000000,
                        estimation_ref="TEST_ONLY_complete",
                        reservation_seconds=3600,
                        reclamation_ref="TEST_ONLY_manual",
                        alert_ref="TEST_ONLY_monitor",
                        allowed_download_sources=["TEST_ONLY:bound-mock"],
                        max_download_bytes=1000000,
                        download_timeout_seconds=10,
                        max_redirects=0,
                        link_validity_ref="TEST_ONLY_original",
                        recovery_ref="TEST_ONLY_original",
                    ),
                    "upload": dict(
                        max_file_bytes=1000000,
                        account_quota_bytes=10000000,
                        allowed_types=["image/png", "image/jpeg", "image/webp"],
                        reservation_seconds=3600,
                        reclamation_ref="TEST_ONLY_manual",
                        alert_ref="TEST_ONLY_monitor",
                    ),
                    "result_download": dict(
                        allowed_download_sources=["TEST_ONLY:bound-mock"],
                        max_download_bytes=1000000,
                        max_total_bytes=1000000,
                        download_timeout_seconds=10,
                        max_redirects=0,
                    ),
                },
            ),
        }
        generation["D-09"] = policy(
            s,
            "D-09",
            {
                "generation": {
                    name: "TEST_ONLY_browser"
                    for name in (
                        "inflight_protection_ref",
                        "exception_handoff_ref",
                        "disabled_account_tasks_ref",
                    )
                },
                "delete": {
                    **{
                        name: "TEST_ONLY_browser"
                        for name in (
                            "list_history_ref",
                            "old_links_ref",
                            "restoration_ref",
                            "retention_reclamation_ref",
                            "capacity_ref",
                            "inflight_protection_ref",
                        )
                    },
                    "execution": dict(
                        schema_version="lifecycle-delete-v1",
                        list="hide",
                        history="tombstone",
                        old_links="deny",
                        restoration="disabled",
                        references="retain_all",
                        capacity="until_physical_removal",
                        retention_seconds=0,
                        unreferenced_cleanup=True,
                    ),
                },
                "account_disable": {
                    **{
                        name: "TEST_ONLY_browser"
                        for name in (
                            "tasks_ref",
                            "frozen_credits_ref",
                            "works_access_ref",
                            "restoration_ref",
                            "exception_handoff_ref",
                        )
                    },
                    "execution": dict(
                        schema_version="lifecycle-disable-v1",
                        inflight="continue_original",
                        frozen_credits="retain",
                        works_access="deny",
                        restoration="new_login",
                        exception_policy_version=generation["D-08"],
                    ),
                },
            },
        )
    settings.generation_policy_versions = generation
    settings.generation_capacity_estimates = {
        spec_id: dict(
            spec_version="TEST_ONLY_v1",
            policy_version=generation["D-10"],
            estimation_ref="TEST_ONLY_complete",
            total_bytes=1000000,
        )
        for spec_id in specs.values()
    }
    settings.storage_policy_version = generation["D-10"]
    settings.assist_policy_version = generation["D-05"]
    settings.assist_provider = "deterministic_mock"
    return dict(agents=agents, specs=specs, policies=generation)
