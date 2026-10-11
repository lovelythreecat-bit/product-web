"""Fail-closed policy gates, exact-version reads and one-time confirmation.

The pure gate consumes trusted snapshots (not request bodies). HTTP/business
callers use PolicyService.require_feature with a map of decision IDs to versions;
only that method resolves authoritative database records. GateReceipt is evidence
for a caller-owned transaction, not a reusable authorization token.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.types import Principal
from app.policies import schemas as s
from app.policies.models import DecisionVersionRecord as Record


class PolicyGateError(Exception):
    status_code = 403
    code = "FEATURE_NOT_ENABLED"

    def __init__(self):
        super().__init__("Feature policy requirements have not been satisfied")


class PolicyAuthorizationError(Exception):
    status_code = 403
    code = "FORBIDDEN"

    def __init__(self):
        super().__init__("Verified policy confirmation authority is required")


class PolicyConflictError(Exception):
    status_code = 409

    def __init__(self):
        super().__init__("Policy version is absent, already exists or was already confirmed")


# This is a minimum schema per feature, not a declaration that any policy is decided.
FIXED_REQUIREMENTS = {
    "investigations": (("D-08", "investigations", s.InvestigationPolicy),),
    "registration": (("D-05", "registration", s.Credits),),
    "prompt_assist": (("D-05", "assist", s.AssistPolicy),),
    "upload": (("D-10", "upload", s.UploadPolicy),),
    "delete": (("D-09", "delete", s.DeletePolicy),),
    "account_disable": (("D-09", "account_disable", s.DisablePolicy),),
    "actual_cost": (("D-06", "cost", s.CostPolicy),),
    "account_recovery": (("D-07", "recovery", s.RecoveryPolicy),),
    "public_site": (
        ("D-07", "login_help", s.LoginHelpPolicy),
        ("D-11", "site", s.SitePolicy),
        ("D-12", "deployment", s.DeploymentPolicy),
    ),
}
GENERATION_REQUIREMENTS = (
    ("D-05", "generation", s.ConcurrencyPolicy),
    ("D-08", "generation", s.ExceptionPolicy),
    ("D-09", "generation", s.LifecycleHandoff),
    ("D-10", "generation", s.StoragePolicy),
)


def require_feature(
    feature: str, mode: s.Mode, decision_versions: Mapping[str, s.DecisionVersion]
) -> s.GateReceipt:
    """Check applicable sections only; no database, configuration or business mutation."""
    if mode not in ("mock", "staging", "production"):
        raise PolicyGateError()
    used: dict[str, str] = {}

    def section(id, path, schema):
        record = decision_versions.get(id)
        if not isinstance(record, s.DecisionVersion):
            raise PolicyGateError()
        # Revalidate because model_copy / nested dict mutation can bypass a DTO validator.
        record = s.DecisionVersion.model_validate(record.model_dump())
        if record.decision_id != id or record.mode != mode:
            raise PolicyGateError()
        if mode != "mock" and record.status != "confirmed":
            raise PolicyGateError()
        value = record.payload
        for key in path:
            value = value[key]
        content = schema.model_validate(value)
        used[id] = record.version
        return content

    try:
        if feature in FIXED_REQUIREMENTS:
            for id, key, schema in FIXED_REQUIREMENTS[feature]:
                section(id, (key,), schema)
        elif match := re.fullmatch(r"spec\.([\w-]+)\.published", feature):
            spec_id = match[1]
            spec = section("D-02", ("specs", spec_id), s.SpecPolicy)
            section("D-05", ("prices", spec_id), s.Credits)
            if spec.delivery_kind in ("multiple", "detail_images"):
                section("D-04", ("specs", spec_id), s.DeliveryPolicy)
        elif match := re.fullmatch(r"agent\.([\w-]+)\.generation", feature):
            agent_id = match[1]
            protocol = section("D-01", ("agents", agent_id), s.AgentPolicy)
            inputs = section("D-03", ("agents", agent_id), s.InputPolicy)
            if protocol.protocol_version != inputs.protocol_version:
                raise PolicyGateError()
            for id, key, schema in GENERATION_REQUIREMENTS:
                section(id, (key,), schema)
        elif match := re.fullmatch(r"case\.([\w-]+)\.published", feature):
            section("D-11", ("cases", match[1]), s.CasePolicy)
            for id, key, schema in FIXED_REQUIREMENTS["public_site"]:
                section(id, (key,), schema)
        else:
            raise PolicyGateError()
    except (ValidationError, KeyError, TypeError, AttributeError):
        raise PolicyGateError() from None
    return s.GateReceipt(
        feature=feature, mode=mode, test_only=mode == "mock", decision_versions=used
    )


# Adapter must verify the current live session and explicit decision permission,
# and return its authoritative user UUID. Merely trusting principal.role is insufficient.
ConfirmationAuthorizer = Callable[[Principal, str], UUID]


class _DecisionSnapshots(Mapping[str, s.DecisionVersion]):
    """Load only decisions requested by the pure gate, caching within this check."""

    def __init__(
        self,
        versions: Mapping[str, str],
        read: Callable[[str, str], s.DecisionVersion | None],
    ):
        self._versions = versions
        self._read = read
        self._loaded: dict[str, s.DecisionVersion] = {}

    def __getitem__(self, id: str) -> s.DecisionVersion:
        if id not in self._loaded:
            version = self._versions[id]
            if not isinstance(version, str):
                raise PolicyGateError()
            record = self._read(id, version)
            if record is None:
                raise PolicyGateError()
            self._loaded[id] = record
        return self._loaded[id]

    def __iter__(self):
        return iter(self._versions)

    def __len__(self):
        return len(self._versions)


class PolicyService:
    def __init__(
        self, session: Session, *, confirmation_authorizer: ConfirmationAuthorizer | None = None
    ):
        self.session = session
        self.confirmation_authorizer = confirmation_authorizer

    def _read(self, id: str, version: str) -> s.DecisionVersion | None:
        # Core mappings avoid stale ORM identities and do not autoflush another service's writes.
        with self.session.no_autoflush:
            row = (
                self.session.execute(
                    select(Record.__table__).where(
                        Record.decision_id == id, Record.version == version
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        values = dict(row)
        if values["confirmed_at"] is not None:
            values["confirmed_at"] = values["confirmed_at"].replace(tzinfo=UTC)
        return s.DecisionVersion.model_validate(values)

    def add_draft(self, decision: s.DecisionVersion) -> s.DecisionVersion:
        """Append a new content version; never upsert, replace or commit.

        This is an internal repository operation. Its eventual management route
        needs separate authoring permissions. Existing snapshots are immutable.
        """
        decision = s.DecisionVersion.model_validate(decision.model_dump())
        if decision.status != "draft":
            raise PolicyConflictError()
        values = decision.model_dump(mode="json")
        try:
            with self.session.no_autoflush:
                self.session.execute(insert(Record.__table__).values(**values))
        except IntegrityError:
            raise PolicyConflictError() from None
        return decision

    def confirm_decision(
        self, actor: Principal, id: str, version: str, evidence_refs: Sequence[str]
    ) -> s.DecisionVersion:
        if not isinstance(actor, Principal) or self.confirmation_authorizer is None:
            raise PolicyAuthorizationError()
        owner = self.confirmation_authorizer(actor, id)
        if not isinstance(owner, UUID) or owner != actor.user_id:
            raise PolicyAuthorizationError()
        if isinstance(evidence_refs, (str, bytes)):
            raise ValueError("Evidence must be a nonempty sequence of references")
        original = self._read(id, version)
        if original is None or original.status != "draft":
            raise PolicyConflictError()
        values = original.model_dump()
        values.update(
            status="confirmed",
            confirmed_by=owner,
            confirmed_at=datetime.now(UTC),
            evidence_refs=tuple(evidence_refs),
        )
        confirmed = s.DecisionVersion.model_validate(values)
        with self.session.no_autoflush:
            changed = self.session.execute(
                update(Record.__table__)
                .where(
                    Record.decision_id == id, Record.version == version, Record.status == "draft"
                )
                .values(
                    status="confirmed",
                    confirmed_by=str(owner),
                    confirmed_at=confirmed.confirmed_at.replace(tzinfo=None),
                    evidence_refs=list(confirmed.evidence_refs),
                )
            )
        if changed.rowcount != 1:
            raise PolicyConflictError()
        return confirmed

    def require_feature(
        self, feature: str, mode: s.Mode, decision_versions: Mapping[str, str]
    ) -> s.GateReceipt:
        """Resolve only applicable exact versions; never substitute the newest version."""
        return require_feature(feature, mode, _DecisionSnapshots(decision_versions, self._read))
