"""Explicit adapter registrations; drafts and TEST_ONLY implementations fail closed."""

from dataclasses import dataclass

from app.catalog.models import AgentRecord
from app.catalog.schemas import AgentVersion, content_digest
from app.tasks.models import TaskSnapshot

from .contracts import AgentAdapter
from .mock import MockAgentAdapter
from .mock_server import PROTOCOL


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

    def bind_task(self, session, task):
        """Resolve only the fixed server-side catalog version, never user routing fields."""
        record = session.get(AgentRecord, (task.agent_id, task.agent_version))
        snapshot = session.get(TaskSnapshot, task.id)
        if record is None or snapshot is None or snapshot.agent_snapshot != record.snapshot:
            raise LookupError("Agent binding unavailable")
        return self.bind_version(record)

    def bind_version(self, record):
        """Resolve a callback path only through the immutable catalog record."""
        version = AgentVersion.model_validate(record.snapshot)
        if (str(version.agent_id), version.version) != (record.agent_id, record.version):
            raise LookupError("Agent binding identity mismatch")
        if (
            self.mode != "mock"
            or not self.test_only
            or version.mode != "mock"
            or not version.test_only
            or version.protocol_version != PROTOCOL
        ):
            raise LookupError("No confirmed upstream integration enabled")
        adapter = MockAgentAdapter(
            agent_id=version.kind,
            base_url=record.endpoint,
            mode=self.mode,
            test_only=self.test_only,
        )
        return AgentBinding(
            record.agent_id,
            record.version,
            version.kind,
            version.protocol_version,
            content_digest(record.endpoint),
            adapter,
        )


@dataclass(frozen=True)
class AgentBinding:
    agent_id: str
    agent_version: str
    wire_agent_id: str
    protocol_version: str
    endpoint_digest: str
    adapter: AgentAdapter
