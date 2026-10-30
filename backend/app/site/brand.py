"""Public name reads and version-checked, audited admin writes."""

from fastapi import HTTPException
from sqlalchemy import update

from app.admin.permissions import authorize_admin
from app.audit.service import audit_admin
from app.site.models import SiteBrand
from app.site.schemas import SiteBrandView


def read_brand(session, mode):
    row = session.get(SiteBrand, mode)
    return SiteBrandView(name=row.name, version=row.version) if row else SiteBrandView(
        name="映作", version=0
    )


def update_brand(session, actor, mode, dto):
    authorize_admin(session, actor)
    before = read_brand(session, mode)
    changed = session.execute(
        update(SiteBrand)
        .where(SiteBrand.mode == mode, SiteBrand.version == dto.expected_version)
        .values(name=dto.name, version=dto.expected_version + 1)
    )
    if changed.rowcount != 1:
        raise HTTPException(409)
    audit_admin(session, actor.user_id, "site_brand_update", mode, "修改 Logo 名称", {
        "before_name": before.name, "after_name": dto.name,
        "before_version": dto.expected_version, "after_version": dto.expected_version + 1,
    })
    return SiteBrandView(name=dto.name, version=dto.expected_version + 1)
