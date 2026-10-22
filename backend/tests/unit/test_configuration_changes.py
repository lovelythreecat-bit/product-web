"""Configuration saves no longer require a user-supplied change reason."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.admin.schemas import RegistrationConfigUpdate
from app.admin.text_model_schemas import TextModelCreate, TextModelUpdate
from app.agents.service_connection import TextServiceConnectionUpdate
from app.agents.text_runtime import TextDefaultModelUpdate
from app.catalog.schemas import PriceDraft
from app.ledger.service import set_registration_credit_config


@pytest.mark.parametrize("schema,payload", [
    (RegistrationConfigUpdate, dict(expected_version=None, amount=0, policy_version="test")),
    (TextModelCreate, dict(config=dict(name="test", base_url="https://example.com/v1",
                                     model="test", api_key="test-key"))),
    (TextModelUpdate, dict(expected_revision=1, config=dict(name="updated"))),
    (TextServiceConnectionUpdate, dict(expected_revision=0, base_url="https://example.com")),
    (TextDefaultModelUpdate, dict(model_config_id=str(uuid4()), expected_revision=0,
                                 expected_connection_revision=0)),
    (PriceDraft, dict(spec_id=str(uuid4()), version="v1", enabled=True,
                     credits=0, policy_version="test")),
])
def test_change_requests_omit_reason_and_ignore_legacy_reason(schema, payload):
    value = schema.model_validate(payload)
    assert "reason" not in value.model_dump()
    assert "reason" not in schema.model_json_schema()["properties"]
    for legacy in ("", " ", "x" * 501, None, {"old": "client"}):
        assert schema.model_validate(payload | {"reason": legacy}) == value
    with pytest.raises(ValidationError):
        schema.model_validate(payload | {"unexpected": True})


def test_registration_service_saves_without_reason_and_keeps_audit_metadata():
    session = MagicMock()
    session.scalar.return_value = None
    with patch("app.ledger.service.PolicyService") as policy, \
            patch("app.ledger.service.audit_credit_config") as audit:
        policy.return_value._read.return_value.payload = {"registration": {"credits": 0}}
        result = set_registration_credit_config(session, mode="mock", expected_version=None,
                                                amount=0, policy_version="test")
    assert result.amount == 0
    assert result.reason == "更新注册赠送配置"
    assert audit.call_args.args[2] == result.version
    assert audit.call_args.args[4:] == (0, "test")
