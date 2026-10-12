"""Catalog publication and transaction-local pricing. The caller owns commit.

Current reads lock heads, so a concurrent publication cannot change a validated
price until the admission transaction ends. Authenticate/lock the user first;
catalog lock order is agent -> spec -> price. T07 must keep this shared Session
through task admission and must run the generation/storage gates separately.
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import insert, select, tuple_, update
from sqlalchemy.exc import IntegrityError

from app.audit.service import audit_catalog
from app.auth.models import AuthSession, User
from app.catalog import schemas as s
from app.catalog.models import (
    AgentHead,
    AgentRecord,
    PriceHead,
    PriceRecord,
    SpecHead,
    SpecIdentity,
    SpecRecord,
)
from app.common.types import InputSnapshot, Principal, Quote
from app.policies import schemas as ps
from app.policies.models import DecisionVersionRecord
from app.policies.service import PolicyGateError


class CatalogError(Exception):
    def __init__(
        self, code="INPUT_INVALID", status_code=422, *, current_quotes=None, current_specs=None
    ):
        super().__init__("Catalog request cannot be completed")
        self.code, self.status_code = code, status_code
        self.current_quotes, self.current_specs = current_quotes, current_specs


class CatalogService:
    def __init__(self, session, *, mode="production"):
        self.session, self.mode = session, mode

    def _principal(self, actor, admin=False):
        if not isinstance(actor, Principal):
            raise HTTPException(401)
        user = self.session.scalar(
            select(User)
            .where(User.id == str(actor.user_id))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        credential = self.session.scalar(
            select(AuthSession)
            .where(AuthSession.id == str(actor.session_id))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            user is None
            or credential is None
            or credential.user_id != user.id
            or user.status != "active"
            or credential.revoked_at is not None
            or credential.expires_at <= datetime.now(UTC).replace(tzinfo=None)
            or credential.auth_version != user.auth_version
            or actor.auth_version != user.auth_version
        ):
            raise HTTPException(401)
        if admin and user.role != "admin":
            raise HTTPException(403)

    def _head(self, table, key, id, *, write=False):
        return self.session.scalar(
            select(table.version)
            .where(getattr(table, key) == str(id))
            .with_for_update(read=not write)
        )

    def _version(self, table, key, id, version, schema):
        snapshot = self.session.scalar(
            select(table.snapshot)
            .where(getattr(table, key) == str(id), table.version == version)
            .with_for_update(read=True)
        )
        return schema.model_validate(snapshot) if snapshot is not None else None

    def read_agent_version(self, id, version):
        result = self._version(AgentRecord, "agent_id", id, version, s.AgentVersion)
        return result if result and result.mode == self.mode else None

    def read_spec_version(self, id, version):
        result = self._version(SpecRecord, "spec_id", id, version, s.SpecVersion)
        return (
            result
            if result and self.read_agent_version(result.agent_id, result.agent_version)
            else None
        )

    def read_price_version(self, id, version):
        identity = self._spec_agent_id(id)
        if identity is None:
            return None
        agent_version = self._head(AgentHead, "agent_id", identity)
        if agent_version is None or not self.read_agent_version(identity, agent_version):
            return None
        return self._version(PriceRecord, "spec_id", id, version, s.PriceVersion)

    def _spec_agent_id(self, id):
        # Full unique PK lookup: for an existing identity InnoDB locks the record,
        # not a version insertion gap. Existing publishers only share this row;
        # identity INSERT belongs exclusively to first publication.
        return self.session.scalar(
            select(SpecIdentity.agent_id)
            .where(SpecIdentity.spec_id == str(id))
            .with_for_update(read=True)
        )

    def _policy(self, decision, versions, path, schema):
        row = (
            self.session.execute(
                select(DecisionVersionRecord.__table__)
                .where(
                    DecisionVersionRecord.decision_id == decision,
                    DecisionVersionRecord.version == versions.get(decision, ""),
                )
                .with_for_update(read=True)
            )
            .mappings()
            .one_or_none()
        )
        return self._policy_value(row, path, schema)

    def _policy_value(self, row, path, schema):
        if row is None:
            raise PolicyGateError()
        values = dict(row)
        if values["confirmed_at"] is not None:
            values["confirmed_at"] = values["confirmed_at"].replace(tzinfo=UTC)
        record = ps.DecisionVersion.model_validate(values)
        if (
            record is None
            or record.mode != self.mode
            or (self.mode != "mock" and record.status != "confirmed")
        ):
            raise PolicyGateError()
        try:
            payload = record.payload
            for part in path:
                payload = payload[part]
            return schema.model_validate(payload)
        except (KeyError, TypeError, ValidationError):
            raise PolicyGateError() from None

    def _agent_gate(self, agent, policy_reader=None):
        read_policy = policy_reader or self._policy
        inputs = read_policy(
            "D-03", agent.policy_versions, ("agents", str(agent.agent_id)), ps.InputPolicy
        )
        if (
            inputs.protocol_version != agent.protocol_version
            or inputs.supported_inputs_ref != s.support_ref(agent.input_support)
        ):
            raise PolicyGateError()
        if self.mode != "mock":
            protocol = read_policy(
                "D-01", agent.policy_versions, ("agents", str(agent.agent_id)), ps.AgentPolicy
            )
            if protocol.protocol_version != agent.protocol_version:
                raise PolicyGateError()

    def _spec_gate(self, spec):
        policy = self._policy(
            "D-02", spec.policy_versions, ("specs", str(spec.spec_id)), ps.SpecPolicy
        )
        self._policy("D-05", spec.policy_versions, ("prices", str(spec.spec_id)), ps.Credits)
        if spec.delivery_kind in ("multiple", "detail_images"):
            self._policy(
                "D-04", spec.policy_versions, ("specs", str(spec.spec_id)), ps.DeliveryPolicy
            )
        if (
            policy.agent_id != str(spec.agent_id)
            or policy.agent_version != spec.agent_version
            or policy.delivery_kind != spec.delivery_kind
            or policy.parameter_schema_ref != s.support_ref(spec.parameter_schema)
        ):
            raise PolicyGateError()

    def _price_gate(self, price):
        policy = self._policy(
            "D-05", {"D-05": price.policy_version}, ("prices", str(price.spec_id)), ps.Credits
        )
        if price.credits != policy.credits:
            raise PolicyGateError()

    def _append(self, table, head, key, id, dto, snapshot, private=None):
        current = self._head(head, key, id, write=True)
        if current != dto.expected_version:
            raise CatalogError("INPUT_INVALID", 409)
        try:
            with self.session.begin_nested():
                self.session.execute(
                    insert(table).values(
                        **{
                            key: str(id),
                            "version": dto.version,
                            "snapshot": snapshot.model_dump(mode="json"),
                            **(private or {}),
                        }
                    )
                )
                if current is None:
                    self.session.execute(
                        insert(head).values(**{key: str(id), "version": dto.version})
                    )
                else:
                    changed = self.session.execute(
                        update(head)
                        .where(getattr(head, key) == str(id), head.version == current)
                        .values(version=dto.version)
                    )
                    if changed.rowcount != 1:
                        raise CatalogError("INPUT_INVALID", 409)
        except IntegrityError:
            raise CatalogError("INPUT_INVALID", 409) from None
        return snapshot

    def publish_agent_version(self, actor, draft):
        self._principal(actor, admin=True)
        draft = s.AgentDraft.model_validate(draft.model_dump())
        if draft.mode != self.mode:
            raise PolicyGateError()
        current = self._head(AgentHead, "agent_id", draft.agent_id, write=True)
        old = self.read_agent_version(draft.agent_id, current) if current else None
        if current and (old is None or old.kind != draft.kind):
            raise CatalogError("INPUT_INVALID", 409)
        self._agent_gate(draft) if draft.enabled else None
        endpoint = draft.endpoint.get_secret_value()
        secret = draft.secret_ref.get_secret_value() if draft.secret_ref else None
        if not endpoint or len(endpoint) > 2048 or (secret is not None and len(secret) > 1024):
            raise CatalogError()
        value = s.AgentVersion(
            **draft.model_dump(exclude={"endpoint", "secret_ref", "reason", "expected_version"}),
            secret_configured=bool(secret),
        )
        self._append(
            AgentRecord,
            AgentHead,
            "agent_id",
            draft.agent_id,
            draft,
            value,
            {"endpoint": endpoint, "secret_ref": secret},
        )
        audit_catalog(
            self.session,
            actor.user_id,
            "agent",
            draft.agent_id,
            draft.version,
            draft.reason,
            value.enabled,
            secret_configured=bool(secret),
        )
        return value

    def publish_spec_version(self, actor, draft):
        self._principal(actor, admin=True)
        draft = s.SpecDraft.model_validate(draft.model_dump())
        av = self._head(AgentHead, "agent_id", draft.agent_id)
        agent = self.read_agent_version(draft.agent_id, av) if av else None
        if agent is None or (draft.enabled and (not agent.enabled or av != draft.agent_version)):
            raise CatalogError("SPEC_DISABLED")
        if draft.enabled:
            self._agent_gate(agent)
            self._spec_gate(draft)
        value = s.SpecVersion(**draft.model_dump(exclude={"reason", "expected_version"}))
        try:
            with self.session.begin_nested():
                if draft.expected_version is None:
                    # Insert directly before taking SpecHead's absent-key lock.
                    # Uniqueness serializes concurrent first publications. Never
                    # upsert an existing identity while readers hold shared locks.
                    self.session.execute(
                        insert(SpecIdentity).values(
                            spec_id=str(draft.spec_id), agent_id=str(draft.agent_id)
                        )
                    )
                elif self._spec_agent_id(draft.spec_id) != str(draft.agent_id):
                    raise CatalogError("INPUT_INVALID", 409)
                self._head(SpecHead, "spec_id", draft.spec_id, write=True)
                self._append(
                    SpecRecord,
                    SpecHead,
                    "spec_id",
                    draft.spec_id,
                    draft,
                    value,
                    {"agent_id": str(draft.agent_id), "agent_version": draft.agent_version},
                )
                audit_catalog(
                    self.session,
                    actor.user_id,
                    "spec",
                    draft.spec_id,
                    draft.version,
                    draft.reason,
                    value.enabled,
                )
        except IntegrityError:
            raise CatalogError("INPUT_INVALID", 409) from None
        return value

    def set_price_version(self, actor, draft):
        self._principal(actor, admin=True)
        draft = s.PriceDraft.model_validate(draft.model_dump())
        spec, agent = self._current_spec(draft.spec_id, require_enabled=draft.enabled)
        if draft.enabled:
            self._agent_gate(agent)
            # New price uses its own exact D-05 version, not the spec publication's old price.
            self._spec_gate(
                spec.model_copy(
                    update={
                        "policy_versions": spec.policy_versions | {"D-05": draft.policy_version}
                    }
                )
            )
            self._price_gate(draft)
        value = s.PriceVersion(**draft.model_dump(exclude={"reason", "expected_version"}))
        self._append(PriceRecord, PriceHead, "spec_id", draft.spec_id, draft, value)
        audit_catalog(
            self.session,
            actor.user_id,
            "price",
            draft.spec_id,
            draft.version,
            draft.reason,
            value.enabled,
            credits=value.credits,
        )
        return value

    def _current_spec(self, id, require_enabled=True):
        identity = self._spec_agent_id(id)
        if identity is None:
            raise CatalogError("SPEC_DISABLED")
        av = self._head(AgentHead, "agent_id", identity)
        sv = self._head(SpecHead, "spec_id", id)
        agent = self.read_agent_version(identity, av) if av else None
        spec = self.read_spec_version(id, sv) if sv else None
        if (
            agent is None
            or spec is None
            or (
                require_enabled
                and (not agent.enabled or not spec.enabled or spec.agent_version != av)
            )
        ):
            raise CatalogError("SPEC_DISABLED")
        return spec, agent

    def _available(self, id):
        spec, agent = self._current_spec(id)
        pv = self._head(PriceHead, "spec_id", id)
        price = self.read_price_version(id, pv) if pv else None
        if price is None or not price.enabled:
            raise CatalogError("SPEC_DISABLED")
        self._agent_gate(agent)
        self._spec_gate(
            spec.model_copy(
                update={"policy_versions": spec.policy_versions | {"D-05": price.policy_version}}
            )
        )
        self._price_gate(price)
        return spec, agent, price

    def _quote(self, input, spec, agent, price):
        input = InputSnapshot.model_validate(input.model_dump())
        support = agent.input_support
        if (
            not input.product_version.strip()
            or any(not input.product.get(key) for key in support.product_required_fields)
            or (support.instruction_required and not input.instruction.strip())
            or not support.min_materials <= len(input.material_versions) <= support.max_materials
            or not spec.parameter_schema.accepts(input.parameters)
        ):
            raise CatalogError()
        agent_decisions = ("D-03",) if self.mode == "mock" else ("D-01", "D-03")
        spec_decisions = ("D-02",) if spec.delivery_kind == "single" else ("D-02", "D-04")
        versions = {k: agent.policy_versions[k] for k in agent_decisions}
        versions.update({k: spec.policy_versions[k] for k in spec_decisions})
        versions["D-05"] = price.policy_version
        return Quote(
            spec_id=spec.spec_id,
            spec_version=spec.version,
            price_version=price.version,
            agent_version=agent.version,
            policy_versions=versions,
            credits=price.credits,
            input_digest=s.content_digest(input.model_dump(mode="json")),
        )

    def quote_generation(self, principal, input, spec_id):
        self._principal(principal)
        spec, agent, price = self._available(spec_id)
        return self._quote(input, spec, agent, price)

    def validate_confirmed_quote(self, quote, input):
        """T07: call after current user auth, before any task/credit mutation, same Session.

        No commit, no acceptance, no silent repricing. The quote is independently
        recomputed from MySQL and canonical input, never trusted from the caller.
        """
        quote = Quote.model_validate(quote.model_dump())
        try:
            spec, agent, price = self._available(quote.spec_id)
            current = self._quote(input, spec, agent, price)
        except (CatalogError, PolicyGateError):
            self._stale(quote, input)
        if current != quote:
            self._stale(quote, input)
        return s.ValidatedQuote(quote=current, spec=spec, agent=agent, price=price)

    def _stale(self, quote, input):
        old = self.read_spec_version(quote.spec_id, quote.spec_version)
        if old is None:
            raise CatalogError("SPEC_DISABLED")
        specs, quotes = [], []
        for spec in self.list_specs(old.agent_id):
            specs.append(spec)
            try:
                current_spec, agent, price = self._available(spec.spec_id)
                quotes.append(self._quote(input, current_spec, agent, price))
            except (CatalogError, PolicyGateError):
                pass
        raise CatalogError("QUOTE_STALE", 409, current_quotes=quotes, current_specs=specs)

    def list_agents(self, *, admin=False):
        # Keep authoritative current reads and the caller's transaction, but
        # acquire each class of shared locks in one ordered batch.
        heads = self.session.execute(
            select(AgentHead.agent_id, AgentHead.version)
            .order_by(AgentHead.agent_id)
            .with_for_update(read=True)
        ).all()
        if not heads:
            return []
        candidates = [
            s.AgentVersion.model_validate(snapshot)
            for snapshot in self.session.scalars(
                select(AgentRecord.snapshot)
                .where(tuple_(AgentRecord.agent_id, AgentRecord.version).in_(heads))
                .order_by(AgentRecord.agent_id, AgentRecord.version)
                .with_for_update(read=True)
            )
        ]
        candidates = [agent for agent in candidates if agent.mode == self.mode]
        if admin:
            return candidates
        candidates = [agent for agent in candidates if agent.enabled]
        decisions = ("D-03",) if self.mode == "mock" else ("D-01", "D-03")
        keys = {
            (decision, agent.policy_versions.get(decision, ""))
            for agent in candidates
            for decision in decisions
        }
        rows = (
            self.session.execute(
                select(DecisionVersionRecord.__table__)
                .where(
                    tuple_(DecisionVersionRecord.decision_id, DecisionVersionRecord.version).in_(
                        sorted(keys)
                    )
                )
                .order_by(DecisionVersionRecord.decision_id, DecisionVersionRecord.version)
                .with_for_update(read=True)
            ).mappings()
            if keys
            else []
        )
        policies = {(row["decision_id"], row["version"]): row for row in rows}

        def read_policy(decision, versions, path, schema):
            row = policies.get((decision, versions.get(decision, "")))
            return self._policy_value(row, path, schema)

        result = []
        for agent in candidates:
            try:
                self._agent_gate(agent, read_policy)
                result.append(agent)
            except PolicyGateError:
                pass
        return result

    def list_specs(self, agent_id=None, *, admin=False):
        # Enumerate authoritative current candidates, locking agents before specs.
        # Merely locking each candidate later cannot recover rows an old RR
        # snapshot already omitted. A caller's existing transaction stays intact.
        agent_ids = (
            [str(agent_id)]
            if agent_id is not None
            else self.session.scalars(
                select(AgentHead.agent_id).order_by(AgentHead.agent_id).with_for_update(read=True)
            ).all()
        )
        result = []
        for current_agent_id in agent_ids:
            if self._head(AgentHead, "agent_id", current_agent_id) is None:
                continue
            query = (
                select(SpecIdentity.spec_id)
                .where(SpecIdentity.agent_id == current_agent_id)
                .order_by(SpecIdentity.spec_id)
                .with_for_update(read=True)
            )
            for id in self.session.scalars(query):
                try:
                    spec, _ = self._current_spec(id, require_enabled=not admin)
                    if spec.agent_id != UUID(current_agent_id):
                        continue
                    if not admin:
                        spec, _, _ = self._available(id)
                    result.append(spec)
                except (CatalogError, PolicyGateError):
                    continue
        return result

    def list_prices(self):
        result = []
        for spec in self.list_specs(admin=True):
            version = self._head(PriceHead, "spec_id", spec.spec_id)
            if version:
                result.append(self.read_price_version(spec.spec_id, version))
        return result
