"""Text draft and generation entry points must agree without touching a database."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.assist.service import validate_draft_parameters
from app.catalog.schemas import AgentVersion, single_spec
from app.catalog.service import CatalogError, CatalogService
from app.common.types import InputSnapshot


def text_agent():
    return AgentVersion(
        agent_id=uuid4(), version="text-agent-v1", kind="copy", name="文本创作",
        mode="mock", test_only=True, enabled=True, protocol_version="text-agent-v1",
        secret_configured=True, policy_versions={}, input_support=dict(
            product_required_fields=["name"], instruction_required=False,
            min_materials=0, max_materials=4,
        ),
    )


def test_text_quote_keeps_requirements_in_digest_and_rejects_malformed_values(monkeypatch):
    from app.catalog import parameters

    selected = text_agent()
    monkeypatch.setattr(parameters, "read_parameters", lambda *a, **kw: SimpleNamespace(
        version=str(uuid4()), text_price=8,
    ))
    catalog = CatalogService(None, mode="mock")
    monkeypatch.setattr(catalog, "_principal", lambda *a: None)
    monkeypatch.setattr(catalog, "_current_agent", lambda *a: selected)
    value = InputSnapshot(
        product_version="v1", product={"name": "商品"}, instruction="", material_versions=[],
        parameters={"copy_type": "直播口播", "max_chars": 120},
    )
    first = catalog.quote_agent(None, value, selected.agent_id)
    assert first.credits == 8
    value.parameters["max_chars"] = 121
    second = catalog.quote_agent(None, value, selected.agent_id)
    assert first.input_digest != second.input_digest
    for invalid in ({"max_chars": True}, {"max_chars": 0}, {"unexpected": "x"}):
        value.parameters = invalid
        with pytest.raises(CatalogError):
            catalog.quote_agent(None, value, selected.agent_id)


def test_prompt_assist_accepts_same_text_requirements_and_rejects_invalid_ones():
    selected = text_agent()
    request = SimpleNamespace(parameters={
        "copy_type": "选购指南", "platform": "自定义平台", "audience": "新手",
        "tone": "专业", "max_chars": 200, "extra_instructions": "先讲适用场景",
    })
    validate_draft_parameters(request, selected, single_spec(selected))
    for invalid in ({"max_chars": 0}, {"max_chars": "200"}, {"tone": False}, {"other": "x"}):
        request.parameters = invalid
        with pytest.raises(HTTPException) as error:
            validate_draft_parameters(request, selected, single_spec(selected))
        assert error.value.status_code == 422
