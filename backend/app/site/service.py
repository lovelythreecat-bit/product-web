"""Caller-owned transactions, exact policy approval and independent disk copies."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, update

from app.admin.permissions import authorize_admin
from app.audit.service import audit_admin
from app.catalog.models import AgentRecord
from app.policies.schemas import CasePolicy, SitePolicy
from app.policies.service import PolicyGateError, PolicyService
from app.site import schemas as s
from app.site.models import PublicCase, PublicCaseCopy, SiteContentHead, SiteContentVersion
from app.storage.local_store import LocalStore, StagedFile
from app.storage.models import File
from app.tasks.models import GenerationTask, TaskSnapshot
from app.works.models import Work, WorkItem


def now():
    return datetime.now(UTC).replace(tzinfo=None)


def content_digest(content):
    return hashlib.sha256(
        json.dumps(
            content.model_dump(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def approved_policy(session, mode, versions, feature):
    policy = PolicyService(session)
    receipt = policy.require_feature(feature, mode, versions)
    # Mock gates intentionally allow simulations elsewhere; public display never does.
    for decision, version in receipt.decision_versions.items():
        if policy._read(decision, version).status != "confirmed":
            raise PolicyGateError()
    return policy._read("D-11", versions["D-11"])


def view(row):
    if row is None:
        return s.SiteContentView(
            version=0,
            content=None,
            status="draft",
            policy_version="",
            policy_versions={},
            content_ref=None,
        )
    return s.SiteContentView(
        version=row.version,
        content=row.content,
        status=row.status,
        policy_version=row.policy_version,
        policy_versions=row.policy_versions,
        content_ref="sha256:" + row.content_sha256,
    )


def get_admin_site_content(session, actor, mode):
    authorize_admin(session, actor)
    head = session.get(SiteContentHead, mode)
    return view(session.get(SiteContentVersion, (mode, head.version)) if head.version else None)


def get_public_site_content(session, mode):
    head = session.get(SiteContentHead, mode)
    if not head or not head.approved_version:
        return None
    row = session.get(SiteContentVersion, (mode, head.approved_version))
    try:
        decision = approved_policy(session, mode, row.policy_versions, "public_site")
        policy = SitePolicy.model_validate(decision.payload["site"])
        if policy.content_ref != "sha256:" + row.content_sha256 or row.status != "approved":
            return None
    except (PolicyGateError, ValidationError, KeyError):
        return None
    return view(row)


def update_site_content(session, actor, mode, dto):
    authorize_admin(session, actor)
    digest = content_digest(dto.content)
    versions = {**dto.policy_versions, "D-11": dto.policy_version}
    status = "draft"
    try:
        decision = approved_policy(session, mode, versions, "public_site")
        policy = SitePolicy.model_validate(decision.payload["site"])
        if policy.content_ref == "sha256:" + digest:
            status = "approved"
    except (PolicyGateError, ValidationError, KeyError):
        pass
    version = dto.expected_version + 1
    values = {"version": version}
    if status == "approved":
        values["approved_version"] = version
    # Atomic compare and swap serializes concurrent different administrators too.
    changed = session.execute(
        update(SiteContentHead)
        .where(SiteContentHead.mode == mode, SiteContentHead.version == dto.expected_version)
        .values(**values)
    )
    if changed.rowcount != 1:
        raise HTTPException(409)
    row = SiteContentVersion(
        mode=mode,
        version=version,
        content=dto.content.model_dump(),
        content_sha256=digest,
        status=status,
        policy_version=dto.policy_version,
        policy_versions=versions,
        actor_id=str(actor.user_id),
        created_at=now(),
    )
    session.add(row)
    audit_admin(
        session,
        actor.user_id,
        "site_content_update",
        f"{mode}:{version}",
        "官网内容版本维护",
        {
            "before_version": dto.expected_version,
            "after_version": version,
            "content_sha256": digest,
            "status": status,
            "policy_version": dto.policy_version,
        },
    )
    session.flush()
    return view(row)


def case_policy(session, mode, case_id, versions, work_id, owner_id, authorization_ref):
    decision = approved_policy(session, mode, versions, f"case.{case_id}.published")
    policy = CasePolicy.model_validate(decision.payload["cases"][case_id])
    if (
        policy.source_work_ref != work_id
        or policy.owner_ref != owner_id
        or policy.authorization_ref != authorization_ref
        or policy.execution is None
    ):
        raise PolicyGateError()
    return policy


def admin_case(row):
    return s.AdminCaseView(
        id=row.id,
        work_id=row.work_id,
        owner_id=row.owner_id,
        authorization_ref=row.authorization_ref,
        policy_version=row.policy_versions["D-11"],
        withdrawal_policy_version=row.withdrawal_policy_version,
        state=row.state,
    )


def list_admin_cases(session, actor, mode):
    authorize_admin(session, actor)
    return [
        admin_case(row)
        for row in session.scalars(
            select(PublicCase)
            .where(PublicCase.mode == mode)
            .order_by(PublicCase.created_at.desc())
            .limit(100)
        )
    ]


async def publish_case(session, actor, settings, dto, staged_copies):
    authorize_admin(session, actor)
    if not settings.storage_persistent:
        raise PolicyGateError()
    work_id = str(dto.work_id)
    # Stable case identity lets the independent D-11 approval name the exact source.
    if session.get(PublicCase, work_id):
        raise HTTPException(409)
    work = session.scalar(select(Work).where(Work.id == work_id).with_for_update())
    if not work or work.deleted_at:
        raise HTTPException(404)
    versions = {**dto.policy_versions, "D-11": dto.policy_version}
    policy = case_policy(
        session, settings.mode, work_id, versions, work.id, work.user_id, dto.authorization_ref
    )
    # Ordinary content-access grants are neither consulted nor accepted here.
    task = session.get(GenerationTask, work.task_id)
    snapshot = session.get(TaskSnapshot, work.task_id)
    agent = session.get(AgentRecord, (task.agent_id, task.agent_version)) if task else None
    if (
        not task
        or task.state != "SUCCEEDED"
        or task.user_id != work.user_id
        or not snapshot
        or not agent
        or any(
            a.get("mode") not in ("staging", "production") or a.get("test_only") is not False
            for a in (snapshot.agent_snapshot, agent.snapshot)
        )
    ):
        raise PolicyGateError()
    items = list(session.scalars(select(WorkItem).where(WorkItem.work_id == work.id)))
    if not items or len(items) > 20:
        raise HTTPException(422)
    store = LocalStore(settings.storage_root)
    row = PublicCase(
        id=work_id,
        mode=settings.mode,
        work_id=work_id,
        owner_id=work.user_id,
        authorization_ref=dto.authorization_ref,
        policy_versions=versions,
        state="published",
        actor_id=str(actor.user_id),
        created_at=now(),
    )
    session.add(row)
    session.flush()
    total = 0
    for item in items:
        file = session.scalar(
            select(File)
            .where(
                File.id == item.file_id,
                File.version == item.file_version,
                File.user_id == work.user_id,
                File.state == "durable",
                File.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if not file or file.actual_mime not in (
            "text/plain",
            "image/png",
            "image/jpeg",
            "image/webp",
            "video/mp4",
        ):
            raise HTTPException(422)
        total += file.actual_bytes
        if total > policy.execution.max_total_bytes:
            raise HTTPException(422)
        # Copy uses a separate random namespace under the configured persistent disk.
        with store.read(file.internal_path) as source:
            staged = await store.stage(source, uuid4(), file.actual_bytes)
        staged_copies.append(staged)
        if staged.sha256 != file.sha256 or staged.actual_bytes != file.actual_bytes:
            raise HTTPException(422)
        store.commit(staged)
        session.add(
            PublicCaseCopy(
                id=str(uuid4()),
                case_id=row.id,
                internal_path=staged.key,
                media_type=file.actual_mime,
                actual_bytes=file.actual_bytes,
                sha256=file.sha256,
            )
        )
    audit_admin(
        session,
        actor.user_id,
        "site_case_publish",
        row.id,
        "按独立公开授权发布副本",
        {"policy_version": dto.policy_version, "copy_count": len(items), "state": "published"},
    )
    session.flush()
    return admin_case(row)


def public_cases(session, mode):
    result = []
    for row in session.scalars(
        select(PublicCase)
        .where(PublicCase.mode == mode, PublicCase.state == "published")
        .order_by(PublicCase.created_at.desc())
        .limit(100)
    ):
        try:
            case_policy(
                session,
                mode,
                row.id,
                row.policy_versions,
                row.work_id,
                row.owner_id,
                row.authorization_ref,
            )
        except (PolicyGateError, ValidationError, KeyError):
            continue
        copies = session.scalars(select(PublicCaseCopy).where(PublicCaseCopy.case_id == row.id))
        result.append(
            s.PublicCaseView(
                id=row.id,
                items=[
                    s.PublicCopyView(
                        id=c.id,
                        media_type=c.media_type,
                        url=f"/api/v1/site/cases/{row.id}/copies/{c.id}",
                    )
                    for c in copies
                ],
            )
        )
    return result


def read_public_copy(session, settings, case_id, copy_id):
    row = session.scalar(
        select(PublicCase)
        .where(
            PublicCase.id == str(case_id),
            PublicCase.mode == settings.mode,
            PublicCase.state == "published",
        )
        .with_for_update()
    )
    if not row:
        raise HTTPException(404)
    case_policy(
        session,
        settings.mode,
        row.id,
        row.policy_versions,
        row.work_id,
        row.owner_id,
        row.authorization_ref,
    )
    copy = session.scalar(
        select(PublicCaseCopy).where(
            PublicCaseCopy.id == str(copy_id), PublicCaseCopy.case_id == row.id
        )
    )
    if not copy:
        raise HTTPException(404)
    try:
        with LocalStore(settings.storage_root).read(copy.internal_path) as source:
            data = source.read(copy.actual_bytes + 1)
    except OSError:
        raise HTTPException(404) from None
    if len(data) != copy.actual_bytes or hashlib.sha256(data).hexdigest() != copy.sha256:
        raise HTTPException(404)
    return data, copy.media_type


def withdraw_case(session, actor, mode, case_id, policy_version):
    authorize_admin(session, actor)
    row = session.scalar(
        select(PublicCase)
        .where(PublicCase.id == str(case_id), PublicCase.mode == mode)
        .with_for_update()
    )
    if not row:
        raise HTTPException(404)
    if row.withdrawal_policy_version and row.withdrawal_policy_version != policy_version:
        raise HTTPException(409)
    versions = {**row.policy_versions, "D-11": policy_version}
    case_policy(session, mode, row.id, versions, row.work_id, row.owner_id, row.authorization_ref)
    if row.state == "published":
        row.state, row.withdrawn_at = "cleanup_pending", now()
        row.withdrawal_policy_version = policy_version
        audit_admin(
            session,
            actor.user_id,
            "site_case_withdraw",
            row.id,
            "撤回公开展示授权",
            {"policy_version": policy_version, "state": "cleanup_pending"},
        )
        session.flush()
    return admin_case(row)


def cleanup_case(session, actor, settings, case_id):
    """Retryable after the withdrawal commit; never touches source File rows or paths."""
    authorize_admin(session, actor)
    row = session.scalar(
        select(PublicCase)
        .where(PublicCase.id == str(case_id), PublicCase.mode == settings.mode)
        .with_for_update()
    )
    if not row or row.state != "cleanup_pending":
        return admin_case(row) if row else None
    case_policy(
        session,
        settings.mode,
        row.id,
        {**row.policy_versions, "D-11": row.withdrawal_policy_version},
        row.work_id,
        row.owner_id,
        row.authorization_ref,
    )
    store = LocalStore(settings.storage_root)
    copies = list(session.scalars(select(PublicCaseCopy).where(PublicCaseCopy.case_id == row.id)))
    for copy in copies:
        try:
            store.discard(StagedFile(copy.internal_path, copy.actual_bytes, copy.sha256))
        except OSError:
            return admin_case(row)
        session.delete(copy)
    row.state = "withdrawn"
    audit_admin(
        session,
        actor.user_id,
        "site_case_cleanup",
        row.id,
        "清理已撤回的公开副本",
        {"policy_version": row.withdrawal_policy_version, "state": "withdrawn"},
    )
    session.flush()
    return admin_case(row)
