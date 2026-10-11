"""Strict request/receipt contracts for owner deletion and administrative status CAS."""

from typing import Literal
from uuid import UUID

from app.common.types import DTO, NonNegativeInt
from app.policies.schemas import Version


class DeleteRequest(DTO):
    policy_version: Version


class DeleteReceipt(DTO):
    id: UUID
    deleted: Literal[True]
    policy_version: Version


class AccountStatusRequest(DeleteRequest):
    status: Literal["active", "disabled"]
    expected_auth_version: NonNegativeInt


class AccountStatusReceipt(DeleteRequest):
    user_id: UUID
    status: Literal["active", "disabled"]
    auth_version: NonNegativeInt
