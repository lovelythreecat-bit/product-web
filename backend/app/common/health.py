from typing import Literal

from app.common.types import DTO


class LiveResponse(DTO):
    live: bool
    mode: Literal["mock", "staging", "production"]
    test_only: bool


class ReadyChecks(DTO):
    storage: bool
    database: bool


class ReadyResponse(DTO):
    ready: bool
    checks: ReadyChecks
    mode: Literal["mock", "staging", "production"]
    test_only: bool
