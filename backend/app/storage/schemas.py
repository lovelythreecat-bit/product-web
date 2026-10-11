"""Applicable D-10 fields only; unknown or contradictory quotas stay closed."""

from typing import Annotated

from pydantic import Field, ValidationError

from app.policies.schemas import PolicyData, Text, UploadPolicy
from app.policies.service import PolicyGateError, PolicyService

Bytes = Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]


class CapacityPolicy(PolicyData):
    account_quota_bytes: Bytes
    server_budget_bytes: Bytes
    reservation_seconds: Annotated[int, Field(strict=True, ge=1, le=2147483647)]
    reclamation_ref: Text
    alert_ref: Text


def capacity_policy(session, version, mode, *, purpose="generation"):
    record = PolicyService(session)._read("D-10", version)
    if record is None or record.mode != mode or (mode != "mock" and record.status != "confirmed"):
        raise PolicyGateError()
    try:
        sections = [
            record.payload[key] for key in ("generation", "capacity") if key in record.payload
        ]
        if not sections:
            raise PolicyGateError()
        upload = record.payload.get("upload")
        policies = []
        for section in sections:
            if purpose == "upload":
                values = {
                    key: section[key] for key in ("account_quota_bytes", "server_budget_bytes")
                }
                for key in ("reservation_seconds", "reclamation_ref", "alert_ref"):
                    values[key] = upload[key]
            else:
                values = {key: section[key] for key in CapacityPolicy.model_fields}
            policies.append(CapacityPolicy.model_validate(values))
        if any(
            (p.account_quota_bytes, p.server_budget_bytes)
            != (policies[0].account_quota_bytes, policies[0].server_budget_bytes)
            for p in policies[1:]
        ):
            raise PolicyGateError()
        policy = policies[0]
        if upload is not None and "account_quota_bytes" in upload:
            # Uploaded and generated files share one account quota. Their reservation
            # lifetimes and release evidence may differ by operation.
            if upload["account_quota_bytes"] != policy.account_quota_bytes:
                raise PolicyGateError()
        return policy
    except (KeyError, TypeError, AttributeError, ValidationError):
        raise PolicyGateError() from None


def upload_policy(session, version, mode):
    service = PolicyService(session)
    service.require_feature("upload", mode, {"D-10": version})
    capacity_policy(session, version, mode, purpose="upload")
    policy = UploadPolicy.model_validate(service._read("D-10", version).payload["upload"])
    if policy.max_file_bytes > 2**63 - 1:
        raise PolicyGateError()
    return policy
