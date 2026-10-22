"""Applicable D-10 byte accounting and file validation, without software quotas."""

from typing import Annotated

from pydantic import Field, ValidationError

from app.policies.schemas import StorageAccountingPolicy, Text, UploadPolicy
from app.policies.service import PolicyGateError, PolicyService

Bytes = Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]


class CapacityPolicy(StorageAccountingPolicy):
    reservation_seconds: Annotated[int, Field(strict=True, ge=1, le=2147483647)]
    reclamation_ref: Text
    alert_ref: Text


def capacity_policy(session, version, mode, *, purpose="generation"):
    record = PolicyService(session)._read("D-10", version)
    if record is None or record.mode != mode or (mode != "mock" and record.status != "confirmed"):
        raise PolicyGateError()
    try:
        sections = (
            [record.payload["upload"]]
            if purpose == "upload"
            else [
                record.payload[key] for key in ("generation", "capacity") if key in record.payload
            ]
        )
        if not sections:
            raise PolicyGateError()
        policies = []
        for section in sections:
            values = {key: section[key] for key in CapacityPolicy.model_fields}
            policies.append(CapacityPolicy.model_validate(values))
        return policies[0]
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
