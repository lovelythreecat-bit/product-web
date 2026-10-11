"""Explicit adapter registrations; drafts and TEST_ONLY implementations fail closed."""

from .contracts import AgentAdapter


class AgentRegistry:
    def __init__(self, *, mode: str, test_only: bool):
        self.mode, self.test_only = mode, test_only
        self._adapters: dict[tuple[str, str], AgentAdapter] = {}

    def register(self, adapter: AgentAdapter, *, confirmed_protocol: bool = False) -> None:
        if adapter.test_only:
            if self.mode != "mock" or not self.test_only:
                raise ValueError("TEST_ONLY adapters require mock mode and TEST_ONLY=true")
        elif not confirmed_protocol:
            raise ValueError("Real adapter requires confirmed D-01 protocol; draft is unavailable")
        key = adapter.agent_id, adapter.protocol_version
        if key in self._adapters:
            raise ValueError("Agent protocol already registered")
        self._adapters[key] = adapter

    def get(self, agent_id: str, protocol_version: str) -> AgentAdapter:
        try:
            return self._adapters[agent_id, protocol_version]
        except KeyError:
            raise LookupError("Agent protocol is not enabled") from None
