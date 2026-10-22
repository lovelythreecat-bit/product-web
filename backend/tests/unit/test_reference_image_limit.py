"""New requests enforce four references without invalidating saved history."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.catalog.schemas import AgentVersion, content_digest
from app.catalog.service import CatalogError, CatalogService
from app.common.types import InputSnapshot
from app.quick_generation.schemas import QuickDraft, QuickPrepare, QuickSave, QuickState
from app.quick_generation.service import QuickGenerationService


def references(count):
    return [{"file_id": str(uuid4()), "version": "v1"} for _ in range(count)]


def quick_row(count):
    return SimpleNamespace(version=1, state=QuickState(
        step=1, draft=QuickDraft(material_versions=references(count)),
        current={"copy": None, "image": None, "video": None},
    ).model_dump(mode="json"))


@pytest.mark.parametrize("count", [0, 4, 5])
def test_normal_quote_caps_references_even_when_agent_supports_more(monkeypatch, count):
    from app.catalog import parameters

    selected = AgentVersion(
        agent_id=uuid4(), version="v1", kind="copy", name="文本", mode="mock",
        test_only=True, enabled=True, protocol_version="v1", policy_versions={},
        secret_configured=True, input_support=dict(product_required_fields=["name"],
            instruction_required=False, min_materials=0, max_materials=20),
    )
    monkeypatch.setattr(parameters, "read_parameters", lambda *a, **kw: SimpleNamespace(
        version=str(uuid4()), text_price=1))
    catalog = CatalogService(None, mode="mock")
    monkeypatch.setattr(catalog, "_current_agent", lambda *a: selected)
    value = InputSnapshot(product_version="p1", product={"name": "商品"}, instruction="",
                          parameters={}, material_versions=references(count))
    if count > 4:
        with pytest.raises(CatalogError):
            catalog._agent_quote(value, selected.agent_id)
    else:
        assert catalog._agent_quote(value, selected.agent_id).quote.credits == 1


def test_quick_save_rejects_fifth_reference_without_changing_draft():
    row = quick_row(4)
    original = deepcopy(row.state)
    draft = QuickDraft.model_validate(row.state["draft"])
    draft.material_versions.append(QuickDraft(material_versions=references(1)).material_versions[0])
    service = QuickGenerationService(Mock(), None)
    with pytest.raises(HTTPException) as error:
        service.save(None, row, QuickSave(version=1, draft=draft))
    assert error.value.status_code == 422
    assert row.state == original and row.version == 1


def test_legacy_draft_can_be_read_saved_and_reduced_without_truncation():
    row = quick_row(20)
    service = QuickGenerationService(Mock(), None)
    draft = QuickState.model_validate(row.state).draft
    service.save(None, row, QuickSave(version=1, draft=draft))
    assert len(row.state["draft"]["material_versions"]) == 20
    draft.material_versions.pop()
    service.save(None, row, QuickSave(version=2, draft=draft))
    assert len(row.state["draft"]["material_versions"]) == 19


def test_legacy_draft_cannot_replace_an_image_above_limit():
    row = quick_row(5)
    draft = QuickDraft.model_validate(row.state["draft"])
    draft.material_versions[0] = QuickDraft(material_versions=references(1)).material_versions[0]
    with pytest.raises(HTTPException) as error:
        QuickGenerationService(Mock(), None).save(None, row, QuickSave(version=1, draft=draft))
    assert error.value.status_code == 422


def test_legacy_oversized_draft_cannot_prepare_even_text_only_generation(monkeypatch):
    row = quick_row(5)
    service = QuickGenerationService(Mock(), SimpleNamespace(mode="mock"))
    product_reads = Mock(side_effect=AssertionError("No product read before reference validation"))
    monkeypatch.setattr(service, "product", product_reads)
    with pytest.raises(HTTPException) as error:
        service.prepare(None, row, QuickPrepare(version=1, kind="copy"))
    assert error.value.status_code == 422
    assert row.version == 1 and row.state["batches"] == []


def test_old_unsubmitted_batch_cannot_bypass_reference_limit():
    row = quick_row(5)
    row.state["pending_batch"] = "pending"
    row.state["batches"] = [{"id": "pending", "kind": "copy", "submitted": False,
                             "draft_digest": content_digest(row.state["draft"]), "items": []}]
    with pytest.raises(HTTPException) as error:
        QuickGenerationService(Mock(), None).submit(None, row, "pending")
    assert error.value.status_code == 422
    assert row.version == 1


def test_already_submitted_legacy_batch_can_replay_without_new_admission():
    row = quick_row(20)
    row.state["batches"] = [{"id": "accepted", "submitted": True}]
    QuickGenerationService(Mock(), None).submit(None, row, "accepted")
    assert row.version == 1 and len(row.state["draft"]["material_versions"]) == 20
