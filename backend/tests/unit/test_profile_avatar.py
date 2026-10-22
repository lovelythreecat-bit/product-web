"""Profile/avatar behavior without database fixtures or schema operations."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.auth.models import AuthSession, User
from app.auth.schemas import ProfileUpdate
from app.auth.security import HASHER
from app.auth.service import AuthService, profile
from app.common.types import Principal
from app.storage.models import File, FileRef
from app.works.lifecycle import LifecycleService


class MemorySession:
    """Only the external persistence boundary is replaced; no engine is created."""

    def __init__(self, user, files=(), refs=()):
        self.user, self.files, self.refs = user, list(files), list(refs)
        self.added = []
        self.credential = AuthSession(
            id=str(uuid4()), user_id=user.id, auth_version=0,
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1), revoked_at=None,
        )

    def get(self, model, identity):
        if model is User and identity == self.user.id:
            return self.user
        return None

    def scalar(self, statement):
        model = statement.column_descriptions[0]["entity"]
        if model is User:
            return self.user
        if model is AuthSession:
            return self.credential
        if model is FileRef:
            return next((r.id for r in self.refs if r.ref_type == "avatar"), None)
        raise AssertionError(f"Unexpected scalar {model}")

    def scalars(self, statement):
        model = statement.column_descriptions[0]["entity"]
        rows = self.files if model is File else self.refs
        return MemoryRows(rows)

    def add(self, row):
        self.added.append(row)
        if isinstance(row, FileRef):
            self.refs.append(row)

    def delete(self, row):
        self.refs.remove(row)

    def flush(self):
        pass


class MemoryRows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows[:]


def account():
    user = User(
        id=str(uuid4()), account_normalized="profile-test", nickname="Old nickname",
        bio="Old biography", role="user", status="active", auth_version=0,
        created_at=datetime(2026, 10, 13, 1, 0),
    )
    # Assigning future fields lets RED exercise consumer behavior before mapping exists.
    for key in ("shop_name", "category", "email", "phone", "avatar_file_id",
                "avatar_file_version", "last_login_at"):
        setattr(user, key, None)
    return user


def principal(session):
    return Principal(user_id=session.user.id, session_id=session.credential.id,
                     role="user", auth_version=0)


def image(user, **overrides):
    values = dict(id=str(uuid4()), version=str(uuid4()), user_id=user.id,
                  state="durable", deleted_at=None, actual_mime="image/png")
    return File(**(values | overrides))


def test_profile_projects_shop_and_avatar_without_internal_file_path():
    user = account()
    user.shop_name, user.category, user.email, user.phone = "Shop", "Shoes", "a@b.test", "123"
    user.avatar_file_id, user.avatar_file_version = str(uuid4()), str(uuid4())
    result = profile(user).model_dump(mode="json")
    assert result["shop_name"] == "Shop"
    assert result["category"] == "Shoes"
    assert result["avatar"] == {"file_id": user.avatar_file_id, "version": user.avatar_file_version}
    assert result["created_at"] == "2026-10-13T01:00:00Z"
    assert result["last_login_at"] is None
    assert result["status"] == "active"
    assert "internal_path" not in result


def test_contact_update_normalizes_optional_empty_values():
    dto = ProfileUpdate(shop_name="  Shop  ", category=" Shoes ", email=" ", phone="  ")
    assert dto.model_dump(exclude_unset=True) == {
        "shop_name": "Shop", "category": "Shoes", "email": None, "phone": None,
    }


@pytest.mark.parametrize("field,value", [
    ("shop_name", "x" * 81), ("category", "x" * 81),
    ("email", "broken-address"), ("phone", "x" * 41),
    ("avatar", {"file_id": str(uuid4()), "version": "x" * 37}),
])
def test_profile_rejects_malformed_or_oversized_contact_fields(field, value):
    with pytest.raises(ValidationError):
        ProfileUpdate(**{field: value})


def test_avatar_bind_then_remove_preserves_non_avatar_references_and_file():
    user = account()
    file = image(user)
    task_ref = FileRef(id=str(uuid4()), file_id=file.id, version=file.version,
                       user_id=user.id, ref_type="task_input", ref_id=str(uuid4()))
    session = MemorySession(user, [file], [task_ref])
    auth = AuthService(session)
    auth.update_profile(principal(session), ProfileUpdate(avatar={
        "file_id": file.id, "version": file.version,
    }))
    assert user.avatar_file_id == file.id
    assert len([r for r in session.refs if r.ref_type == "avatar"]) == 1
    auth.update_profile(principal(session), ProfileUpdate(phone="123"))
    assert user.avatar_file_id == file.id
    auth.update_profile(principal(session), ProfileUpdate(avatar=None))
    assert user.avatar_file_id is None and user.avatar_file_version is None
    assert session.refs == [task_ref]
    assert file.deleted_at is None and file.state == "durable"


@pytest.mark.parametrize("overrides,expected", [
    ({"user_id": str(uuid4())}, 404), ({"state": "unavailable"}, 409),
    ({"deleted_at": datetime(2026, 10, 13)}, 409), ({"actual_mime": "video/mp4"}, 422),
])
def test_avatar_rejects_foreign_deleted_unavailable_or_video_file(overrides, expected):
    user = account()
    file = image(user, **overrides)
    session = MemorySession(user, [file])
    with pytest.raises(HTTPException) as caught:
        AuthService(session).update_profile(principal(session), ProfileUpdate(avatar={
            "file_id": file.id, "version": file.version,
        }, phone="123"))
    assert caught.value.status_code == expected
    assert user.avatar_file_id is None
    assert user.phone is None
    assert not session.refs


def test_avatar_rejects_stale_file_version():
    user = account()
    file = image(user)
    session = MemorySession(user, [file])
    with pytest.raises(HTTPException) as caught:
        AuthService(session).update_profile(principal(session), ProfileUpdate(avatar={
            "file_id": file.id, "version": str(uuid4()),
        }))
    assert caught.value.status_code == 404


def test_long_historical_profile_is_preserved_but_new_long_edit_is_rejected():
    user = account()
    user.nickname, user.bio = "n" * 70, "b" * 450
    session = MemorySession(user)
    auth = AuthService(session)
    auth.update_profile(principal(session), ProfileUpdate(phone="123"))
    assert user.nickname == "n" * 70 and user.bio == "b" * 450
    for data in ({"nickname": "x" * 41}, {"bio": "x" * 301}):
        with pytest.raises(HTTPException) as caught:
            auth.update_profile(principal(session), ProfileUpdate(**data))
        assert caught.value.status_code == 422


def test_explicit_null_nickname_cannot_clear_required_display_name():
    user = account()
    session = MemorySession(user)
    with pytest.raises(HTTPException) as caught:
        AuthService(session).update_profile(principal(session), ProfileUpdate(nickname=None))
    assert caught.value.status_code == 422
    assert user.nickname == "Old nickname"


def test_avatar_retry_and_replacement_leave_only_current_avatar_reference():
    user = account()
    first, second = image(user), image(user)
    session = MemorySession(user, [first, second])
    auth = AuthService(session)
    for file in (first, first, second):
        auth.update_profile(principal(session), ProfileUpdate(avatar={
            "file_id": file.id, "version": file.version,
        }))
        avatar_refs = [r for r in session.refs if r.ref_type == "avatar"]
        assert len(avatar_refs) == 1
        assert avatar_refs[0].file_id == file.id
    assert user.avatar_file_id == second.id
    assert first.deleted_at is None and second.deleted_at is None


def test_profile_mutation_rechecks_disabled_account():
    user = account()
    user.status = "disabled"
    session = MemorySession(user)
    with pytest.raises(HTTPException) as caught:
        AuthService(session).update_profile(principal(session), ProfileUpdate(phone="123"))
    assert caught.value.status_code == 401
    assert user.phone is None


def test_current_avatar_cannot_be_soft_deleted_as_material():
    user = account()
    file = image(user)
    user.avatar_file_id, user.avatar_file_version = file.id, file.version
    session = MemorySession(user, [file])
    with pytest.raises(HTTPException) as caught:
        LifecycleService(session)._delete_file(principal(session), file, "TEST_ONLY-d09")
    assert caught.value.status_code == 409
    assert file.deleted_at is None


def test_only_successful_authentication_updates_last_login():
    user = account()
    user.password_hash = HASHER.hash("TEST_ONLY_login_password")
    session = MemorySession(user)
    auth = AuthService(session)
    auth._issue(user)
    auth.get_profile(principal(session))
    assert user.last_login_at is None
    with pytest.raises(HTTPException):
        auth.authenticate("profile-test", "wrong-password")
    assert user.last_login_at is None
    result = auth.authenticate("profile-test", "TEST_ONLY_login_password")
    assert isinstance(user.last_login_at, datetime)
    assert result.profile.last_login_at is not None
    assert isinstance(result.profile.user_id, UUID)
