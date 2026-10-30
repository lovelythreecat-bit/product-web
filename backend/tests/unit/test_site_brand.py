"""Brand validation, live admin authorization, CAS and audit without external I/O."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.site.brand import read_brand, update_brand
from app.site.models import SiteBrand
from app.site.schemas import SiteBrandUpdate
from tests.unit.test_admin_safe_queries import QuerySession


class BrandSession(QuerySession):
    def __init__(self, role="admin"):
        super().__init__(role=role)
        self.brand = SiteBrand(mode="mock", name="映作", version=0)
        self.audit = []

    def get(self, model, identity):
        assert model is SiteBrand
        return self.brand if identity == self.brand.mode else None

    def execute(self, statement):
        params = statement.compile().params
        assert params["mode_1"] == "mock"
        if params["version_1"] != self.brand.version:
            return SimpleNamespace(rowcount=0)
        self.brand.name, self.brand.version = params["name"], params["version"]
        return SimpleNamespace(rowcount=1)

    def add(self, row):
        self.audit.append(row)


@pytest.mark.parametrize("name", ["", "   ", "字" * 25, "a\nb", "a\x00b"])
def test_invalid_names(name):
    with pytest.raises(ValidationError):
        SiteBrandUpdate(name=name, expected_version=0)


def test_save_normalizes_name_and_audits_then_rejects_stale_write():
    session = BrandSession()
    dto = SiteBrandUpdate(name="  星河创作  ", expected_version=0)
    result = update_brand(session, session.actor, "mock", dto)
    assert result.name == "星河创作" and result.version == 1
    assert read_brand(session, "mock") == result
    assert session.audit[0].changes["before_name"] == "映作"
    assert session.audit[0].changes["after_name"] == "星河创作"
    with pytest.raises(HTTPException) as caught:
        update_brand(session, session.actor, "mock", dto)
    assert caught.value.status_code == 409
    assert len(session.audit) == 1


@pytest.mark.parametrize("condition", ["user", "disabled", "revoked"])
def test_live_admin_permission_required(condition):
    session = BrandSession()
    if condition == "user":
        session.user.role = "user"  # Even a stale admin principal cannot write.
    elif condition == "disabled":
        session.user.status = "disabled"
    else:
        session.credential.revoked_at = session.credential.expires_at
    with pytest.raises(HTTPException):
        update_brand(
            session, session.actor, "mock", SiteBrandUpdate(name="改名", expected_version=0)
        )
    assert session.brand.name == "映作" and not session.audit
