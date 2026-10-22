"""Account mutation and ledger tests use in-memory transport doubles; no DDL."""

from contextlib import nullcontext
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.admin import user_management as m
from app.audit.models import AuditEvent
from app.auth.models import AuthSession, User
from app.auth.schemas import ProfileUpdate
from app.auth.security import verify_password
from app.auth.service import AuthService
from app.catalog.service import CatalogService
from app.common.types import Principal
from app.ledger.models import CreditAccount, CreditGrant, CreditLedger
from app.ledger.reconcile import reconcile_accounts
from app.ledger.service import LedgerError, grant_credits


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def __iter__(self):
        return iter(self.rows)


class Transport:
    def __init__(self):
        self.actor = Principal(user_id=uuid4(), role="admin", session_id=uuid4(), auth_version=0)
        self.admin = self.user(str(self.actor.user_id), "admin")
        self.target = self.user(str(uuid4()), "user")
        self.credential = AuthSession(
            id=str(self.actor.session_id),
            user_id=self.admin.id,
            auth_version=0,
            revoked_at=None,
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        )
        self.balance = CreditAccount(
            user_id=self.target.id, available=0, frozen=0, consumed=0, credited_total=0
        )
        self.rows = [self.admin, self.target, self.credential, self.balance]
        self.queries = []
        self.no_autoflush = nullcontext()
        self.ledger_snapshots = {}

    @staticmethod
    def user(identity, role):
        return User(
            id=identity,
            account_normalized=role + identity[:6],
            role=role,
            status="active",
            auth_version=0,
            created_at=datetime(2026, 10, 17),
            password_hash="old-hash",
            nickname="商家",
            shop_name="店铺",
        )

    def scalar(self, statement):
        self.queries.append(statement)
        description = statement.column_descriptions[0]
        model = description.get("entity")
        params = statement.compile().params
        values = list(params.values())
        if model is User:
            identity = next((x for x in values if x in (self.admin.id, self.target.id)), None)
            if description["name"] == "id":
                return None  # account uniqueness probe
            return self.admin if identity == self.admin.id else self.target
        if model is AuthSession:
            return self.credential
        if model is CreditAccount:
            return self.balance
        if model is CreditLedger:
            return next(
                (
                    x
                    for x in self.rows
                    if isinstance(x, CreditLedger)
                    and (x.operation_key in values or x.grant_id in values)
                ),
                None,
            )
        if model is CreditGrant:
            return next(
                (x for x in self.rows if isinstance(x, CreditGrant) and x.business_key in values),
                None,
            )
        if description["name"] == "count":
            return 0
        return any(
            isinstance(x, AuditEvent) and x.action == "admin_user_delete" and x.object_id in values
            for x in self.rows
        )

    def get(self, model, identity):
        return next(
            (
                x
                for x in self.rows
                if isinstance(x, model)
                and getattr(x, "id", getattr(x, "user_id", None)) == str(identity)
            ),
            None,
        )

    def scalars(self, statement):
        self.queries.append(statement)
        model = statement.column_descriptions[0]["entity"]
        return Rows([x for x in self.rows if isinstance(x, model)])

    def execute(self, statement):
        self.queries.append(statement)
        if getattr(statement, "is_update", False):
            params = statement.compile().params
            for row in self.rows:
                if isinstance(row, AuthSession) and row.user_id in params.values():
                    row.revoked_at = params.get("revoked_at")
        return Rows([])

    def add(self, row):
        self.rows.append(row)

    def flush(self):
        # Mirror credit_ledger_update_guard: every field is immutable after INSERT.
        for row in self.rows:
            if isinstance(row, CreditLedger):
                state = {
                    column.name: deepcopy(getattr(row, column.name))
                    for column in CreditLedger.__table__.columns
                }
                if row.id in self.ledger_snapshots:
                    assert state == self.ledger_snapshots[row.id], "Immutable history"
                else:
                    self.ledger_snapshots[row.id] = state

    def begin_nested(self):
        return nullcontext()


def edit_dto(session, **values):
    return m.ManagedUserUpdate(
        expected_auth_version=session.target.auth_version,
        expected_profile_version=m.profile_version(session.target),
        account=session.target.account_normalized,
        nickname="新昵称",
        role="user",
        status="active",
        reason="修正商户资料",
        **values,
    )


def test_edit_rechecks_live_role_updates_profile_and_revokes_sessions():
    session = Transport()
    session.rows.append(
        AuthSession(id=str(uuid4()), user_id=session.target.id, auth_version=0, revoked_at=None)
    )
    receipt = m.update_user(
        session,
        session.actor,
        session.target.id,
        edit_dto(session, shop_name="新店铺", email="a@example.com"),
    )
    assert receipt.nickname == "新昵称" and receipt.shop_name == "新店铺"
    assert receipt.auth_version == 1
    assert session.rows[-2].revoked_at is not None
    event = session.rows[-1]
    assert event.action == "admin_user_update" and "password" not in str(event.changes)
    assert any(
        query._for_update_arg is not None
        for query in session.queries
        if getattr(query, "is_select", False)
    )


def test_non_admin_and_stale_version_are_rejected_before_changes():
    session = Transport()
    session.admin.role = "user"
    with pytest.raises(HTTPException) as caught:
        m.update_user(session, session.actor, session.target.id, edit_dto(session))
    assert caught.value.status_code == 403
    session.admin.role = "admin"
    dto = edit_dto(session)
    session.target.auth_version = 1
    with pytest.raises(HTTPException) as caught:
        m.update_user(session, session.actor, session.target.id, dto)
    assert caught.value.status_code == 409 and session.target.nickname == "商家"


def test_password_reset_uses_existing_argon_hash_and_never_audits_password():
    session = Transport()
    raw = "unique-new-password"
    m.reset_password(
        session,
        session.actor,
        session.target.id,
        m.ManagedPasswordReset(expected_auth_version=0, new_password=raw, reason="已核验请求"),
    )
    assert verify_password(session.target.password_hash, raw)
    assert session.target.auth_version == 1
    assert raw not in str(session.rows[-1].changes)
    assert "password_hash" not in str(session.rows[-1].changes)


def test_delete_keeps_history_hides_target_revokes_access_and_is_replayable():
    session = Transport()
    history = SimpleNamespace(history="task/ledger audit reference")
    session.rows.append(history)
    dto = m.ManagedUserDelete(expected_auth_version=0, reason="用户申请删除")
    m.delete_user(session, session.actor, session.target.id, dto)
    m.delete_user(session, session.actor, session.target.id, dto)
    assert session.target.status == "disabled" and session.target.auth_version == 1
    assert history in session.rows
    assert len([x for x in session.rows if isinstance(x, AuditEvent)]) == 1
    assert not verify_password(session.target.password_hash, "old-password")
    with pytest.raises(HTTPException) as caught:
        m.reset_password(
            session,
            session.actor,
            session.target.id,
            m.ManagedPasswordReset(
                expected_auth_version=1, new_password="new-password", reason="retry"
            ),
        )
    assert caught.value.status_code == 404
    session.actor = Principal(
        user_id=session.target.id, role="user", session_id=uuid4(), auth_version=0
    )
    with pytest.raises(HTTPException) as caught:
        CatalogService(session)._principal(session.actor)
    assert caught.value.status_code == 401


def test_admin_cannot_be_deleted_even_with_forged_request():
    session = Transport()
    session.target.role = "admin"
    with pytest.raises(HTTPException) as caught:
        m.delete_user(
            session,
            session.actor,
            session.target.id,
            m.ManagedUserDelete(expected_auth_version=0, reason="remove"),
        )
    assert caught.value.status_code == 403
    assert session.target.status == "active"


def test_positive_and_negative_adjustments_reconcile_and_replay_without_touching_frozen():
    session = Transport()
    positive = m.CreditAdjustment(business_key=uuid4(), delta=50, reason="补偿")
    m.adjust_credits(session, session.actor, session.target.id, positive)
    negative = m.CreditAdjustment(business_key=uuid4(), delta=-18, reason="更正发放")
    receipt = m.adjust_credits(session, session.actor, session.target.id, negative)
    assert m.adjust_credits(session, session.actor, session.target.id, negative) == receipt
    assert (
        session.balance.available,
        session.balance.frozen,
        session.balance.consumed,
        session.balance.credited_total,
    ) == (32, 0, 0, 32)
    assert reconcile_accounts(session).differences == ()
    assert (
        sum(x.amount for x in session.rows if isinstance(x, CreditGrant) and x.kind == "admin")
        == 50
    )
    assert (
        len(
            [
                x
                for x in session.rows
                if isinstance(x, AuditEvent) and x.action == "admin_credit_adjustment"
            ]
        )
        == 2
    )
    assert any(isinstance(x, CreditLedger) and x.kind == "admin_deduct" for x in session.rows)


def test_insufficient_available_rejects_without_using_frozen_or_mutating_history():
    session = Transport()
    grant_credits(session, session.target.id, "admin", "fund", 10, "fund", session.actor)
    session.balance.available, session.balance.frozen = 2, 8
    count = len(session.rows)
    with pytest.raises(LedgerError) as caught:
        m.adjust_credits(
            session,
            session.actor,
            session.target.id,
            m.CreditAdjustment(business_key=uuid4(), delta=-3, reason="decrease"),
        )
    assert caught.value.code == "INSUFFICIENT_CREDITS"
    assert (session.balance.available, session.balance.frozen) == (2, 8)
    assert len(session.rows) == count


def test_reused_adjustment_key_cannot_change_target_sign_amount_or_reason():
    session = Transport()
    dto = m.CreditAdjustment(business_key=uuid4(), delta=50, reason="first")
    m.adjust_credits(session, session.actor, session.target.id, dto)
    for changed in ({"delta": -5}, {"delta": 10}, {"reason": "changed"}):
        with pytest.raises(LedgerError):
            m.adjust_credits(
                session, session.actor, session.target.id, dto.model_copy(update=changed)
            )
    assert session.balance.available == 50


@pytest.mark.parametrize("delta", [0, True, 1.5, 2**53, -(2**53)])
def test_adjustment_rejects_non_integer_zero_and_unsafe_browser_amounts(delta):
    with pytest.raises(ValidationError):
        m.CreditAdjustment(business_key=uuid4(), delta=delta, reason="validation")


def test_all_mutations_require_session_bound_csrf():
    mutations = [route for route in m.router.routes if route.methods & {"POST", "PATCH", "DELETE"}]
    assert len(mutations) == 4
    for route in mutations:
        assert any(dependency.call is m.require_csrf for dependency in route.dependant.dependencies)


def test_successful_adjustment_receipt_can_be_replayed_after_target_deletion():
    session = Transport()
    dto = m.CreditAdjustment(business_key=uuid4(), delta=50, reason="补偿")
    first = m.adjust_credits(session, session.actor, session.target.id, dto)
    m.delete_user(
        session,
        session.actor,
        session.target.id,
        m.ManagedUserDelete(expected_auth_version=0, reason="用户申请"),
    )
    assert m.adjust_credits(session, session.actor, session.target.id, dto) == first
    with pytest.raises(m.AdjustmentTargetDeleted):
        m.adjust_credits(
            session,
            session.actor,
            session.target.id,
            m.CreditAdjustment(business_key=uuid4(), delta=3, reason="new"),
        )
    assert session.balance.available == 50


def test_positive_adjustment_preserves_inserted_ledger_identity_and_only_credits_once():
    session = Transport()
    dto = m.CreditAdjustment(business_key=uuid4(), delta=50, reason="补偿")
    first = m.adjust_credits(session, session.actor, session.target.id, dto)
    second = m.adjust_credits(session, session.actor, session.target.id, dto)
    assert first == second
    entries = [row for row in session.rows if isinstance(row, CreditLedger)]
    assert len(entries) == 1 and entries[0].operation_key == f"grant:{entries[0].grant_id}"
    assert session.balance.available == session.balance.credited_total == 50
    assert reconcile_accounts(session).differences == ()


def test_ledger_transport_rejects_any_change_after_flush():
    session = Transport()
    grant_credits(session, session.target.id, "admin", "seed", 10, "seed", session.actor)
    entry = next(row for row in session.rows if isinstance(row, CreditLedger))
    entry.operation_key = "changed-after-insert"
    with pytest.raises(AssertionError, match="Immutable history"):
        session.flush()


@pytest.mark.parametrize("original_delta,changed_delta", [(20, -20), (-20, 20)])
def test_adjustment_replay_cannot_change_sign_target_or_actor(original_delta, changed_delta):
    session = Transport()
    grant_credits(session, session.target.id, "admin", "seed", 100, "seed", session.actor)
    dto = m.CreditAdjustment(business_key=uuid4(), delta=original_delta, reason="更正")
    first = m.adjust_credits(session, session.actor, session.target.id, dto)
    assert m.adjust_credits(session, session.actor, session.target.id, dto) == first
    with pytest.raises(LedgerError):
        m.adjust_credits(
            session,
            session.actor,
            session.target.id,
            dto.model_copy(update={"delta": changed_delta}),
        )
    # The other authorized administrator is also a valid target with its own account.
    original_account = session.balance
    session.balance = CreditAccount(
        user_id=session.admin.id, available=100, frozen=0, consumed=0, credited_total=100
    )
    session.rows.append(session.balance)
    with pytest.raises(LedgerError):
        m.adjust_credits(session, session.actor, session.admin.id, dto)
    session.balance = original_account
    session.target.role = "admin"
    session.credential.user_id = session.target.id
    another_actor = Principal(
        user_id=session.target.id, role="admin", session_id=session.credential.id, auth_version=0
    )
    with pytest.raises(LedgerError):
        m.adjust_credits(session, another_actor, session.target.id, dto)
    assert original_account.available == 100 + original_delta


def test_opposite_signs_share_a_unique_immutable_audit_intent_identity():
    key = uuid4()
    audit_ids = []
    for delta in (30, -30):
        session = Transport()
        grant_credits(session, session.target.id, "admin", "fund", 50, "fund", session.actor)
        m.adjust_credits(
            session,
            session.actor,
            session.target.id,
            m.CreditAdjustment(business_key=key, delta=delta, reason="same intent"),
        )
        audit_ids.append(
            next(
                row.id
                for row in session.rows
                if isinstance(row, AuditEvent) and row.action == "admin_credit_adjustment"
            )
        )
    assert audit_ids[0] == audit_ids[1]


def test_uncommitted_adjustment_to_deleted_target_has_explicit_rejection():
    session = Transport()
    m.delete_user(
        session,
        session.actor,
        session.target.id,
        m.ManagedUserDelete(expected_auth_version=0, reason="用户申请"),
    )
    with pytest.raises(m.AdjustmentTargetDeleted):
        m.adjust_credits(
            session,
            session.actor,
            session.target.id,
            m.CreditAdjustment(business_key=uuid4(), delta=10, reason="not sent"),
        )
    assert session.balance.available == 0
    assert not any(isinstance(row, CreditLedger) for row in session.rows)


def test_deleted_target_route_response_has_explicit_business_code_and_rolls_back():
    import json

    class MutationTransport:
        rollbacks = 0

        def rollback(self):
            self.rollbacks += 1

        def commit(self):
            pytest.fail("Rejected adjustment must never commit")

    session = MutationTransport()

    def deleted():
        raise m.AdjustmentTargetDeleted()

    response = m._mutate(session, deleted)
    assert response.status_code == 409
    assert json.loads(response.body)["error"]["code"] == "ADJUSTMENT_TARGET_DELETED"
    assert session.rollbacks == 2


def test_profile_revision_rejects_stale_admin_form_after_real_owner_profile_edit():
    session = Transport()
    dto = edit_dto(session, phone="123456")
    revision = m.profile_version(session.target)
    admin_credential = session.credential
    owner_credential = AuthSession(
        id=str(uuid4()),
        user_id=session.target.id,
        auth_version=0,
        revoked_at=None,
        expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
    )
    session.credential = owner_credential
    owner = Principal(
        user_id=session.target.id, role="user", session_id=owner_credential.id, auth_version=0
    )
    AuthService(session).update_profile(owner, ProfileUpdate(nickname="用户自行修改B"))
    assert session.target.auth_version == 0
    assert owner_credential.revoked_at is None
    assert m.profile_version(session.target) != revision
    session.credential = admin_credential
    with pytest.raises(HTTPException) as caught:
        m.update_user(session, session.actor, session.target.id, dto)
    assert caught.value.status_code == 409
    assert session.target.nickname == "用户自行修改B"
    assert session.target.phone is None
    assert session.target.auth_version == 0
    fresh = edit_dto(session, phone="123456")
    result = m.update_user(session, session.actor, session.target.id, fresh)
    assert result.phone == "123456"
    assert result.profile_version == m.profile_version(session.target)


@pytest.mark.parametrize(
    "field",
    [
        "account_normalized",
        "nickname",
        "bio",
        "shop_name",
        "category",
        "email",
        "phone",
        "role",
        "status",
        "avatar_file_id",
        "avatar_file_version",
    ],
)
def test_profile_revision_covers_every_editable_identity_and_profile_field(field):
    session = Transport()
    before = m.profile_version(session.target)
    setattr(session.target, field, "changed-value")
    assert m.profile_version(session.target) != before
