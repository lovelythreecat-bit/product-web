"""Explicit adapter registrations; drafts and TEST_ONLY implementations fail closed."""

from dataclasses import dataclass

from app.catalog.models import AgentRecord
from app.catalog.schemas import AgentVersion, content_digest
from app.tasks.models import TaskSnapshot

from .contracts import AgentAdapter
from .mock import MockAgentAdapter
from .mock_server import PROTOCOL
from .text import PROTOCOL as TEXT_PROTOCOL
from .text import TextAgentAdapter, TextAgentRouting


class AgentRegistry:
    def __init__(self, *, mode: str, test_only: bool, text_profiles=None,
                 session_factory=None, store=None, settings=None):
        self.mode, self.test_only = mode, test_only
        self.text_profiles = dict(text_profiles or {})
        self.session_factory, self.store = session_factory, store
        self.settings = settings
        self._adapters: dict[tuple[str, str], AgentAdapter] = {}

    @classmethod
    def from_settings(cls, settings, *, session_factory=None, store=None):
        return cls(mode=settings.mode, test_only=settings.test_only,
                   text_profiles=settings.text_agent_profiles,
                   session_factory=session_factory, store=store, settings=settings)

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
        return self.bind_version(record, task=task, routing=snapshot.routing_snapshot,
                                 session=session)

    def bind_version(self, record, *, task=None, routing=None, session=None):
        """Resolve a callback path only through the immutable catalog record."""
        version = AgentVersion.model_validate(record.snapshot)
        if (str(version.agent_id), version.version) != (record.agent_id, record.version):
            raise LookupError("Agent binding identity mismatch")
        if version.protocol_version == TEXT_PROTOCOL:
            return self._text_binding(record, version, task, routing, session)
        if version.protocol_version in {"image-agent-v1", "video-agent-v1"}:
            return self._media_binding(record, version, task, routing, session)
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

    def _text_binding(self, record, version, task, routing, session=None):
        from app.agents.model_configs import TextModelError
        from app.agents.text_runtime import DATABASE_PROFILE, resolve_text_profile

        database = (self.settings is not None and task is None) or (
            isinstance(routing, dict) and routing.get("profile") == DATABASE_PROFILE
        )
        if database:
            if session is None or self.settings is None:
                raise LookupError("Database text service is unavailable")
            try:
                profile = resolve_text_profile(session, self.settings,
                                               routing=routing if task is not None else None)
            except TextModelError:
                if task is None:
                    raise
                raise LookupError("Original text service is unavailable") from None
            profile_ref = DATABASE_PROFILE
        else:
            # Historical snapshots only. Production composition uses the DB for new tasks.
            profile = self.text_profiles.get(record.secret_ref)
            profile_ref = record.secret_ref
        if (profile is None or version.kind != "copy" or version.mode != self.mode
                or version.test_only != self.test_only
                or (not database and record.endpoint.rstrip("/") != profile.base_url)):
            raise LookupError("Text agent profile unavailable or mismatched")
        if task is not None:
            try:
                fixed = TextAgentRouting.model_validate(routing)
                if (fixed.protocol_version != TEXT_PROTOCOL or fixed.profile != profile_ref
                        or fixed.base_url != profile.base_url):
                    raise ValueError()
                profile = profile.model_copy(update={
                    "model_config_id": fixed.model_config_id,
                    "supports_images": fixed.supports_images,
                })
            except ValueError:
                raise LookupError("Original text routing unavailable") from None
        if not database and version.input_support.max_materials > (
            4 if profile.supports_images else 0
        ):
            raise LookupError("Text material capability mismatched")
        loader = None
        if task is not None and self.session_factory is not None and self.store is not None:
            from .text_materials import material_loader

            loader = material_loader(self.session_factory, self.store, task.id, task.user_id)
        adapter = TextAgentAdapter(
            profile=profile, external_submission_id=task.external_submission_id if task else None,
            material_loader=loader,
        )
        return AgentBinding(
            record.agent_id, record.version, "copy", TEXT_PROTOCOL,
            content_digest(dict(endpoint=profile.base_url, profile=profile_ref,
                                model_config_id=str(profile.model_config_id))), adapter,
        )

    def _media_binding(self, record, version, task, routing, session):
        from app.agents.media_connection import read_media_connection
        from app.agents.media_execution import (
            PROTOCOLS,
            MediaTaskStore,
            media_material_loader,
        )
        from app.agents.media_runtime import managed_media_agent_id

        kind = version.kind
        if (kind not in PROTOCOLS or version.protocol_version != PROTOCOLS[kind]
                or version.agent_id != managed_media_agent_id(self.mode, kind)
                or version.mode != self.mode or version.test_only != self.test_only
                or session is None or self.settings is None):
            raise LookupError("Media agent identity unavailable")
        if task is not None and (not isinstance(routing, dict)
                                 or routing.get("protocol_version") != PROTOCOLS[kind]):
            raise LookupError("Original media routing unavailable")
        connection = read_media_connection(
            session, self.settings, kind,
            connection_id=routing["connection_id"] if task is not None else None,
        )
        if task is not None and connection.base_url != routing.get("base_url"):
            raise LookupError("Original media origin unavailable")
        limit = routing["max_result_bytes"] if task is not None else 1
        values = dict(base_url=connection.base_url, service_key=connection.service_key,
                      max_result_bytes=limit)
        kwargs = dict(external_submission_id=task.external_submission_id if task else None)
        if task is not None:
            if self.session_factory is None or self.store is None:
                raise LookupError("Media execution storage unavailable")
            from app.dispatch.consumer import Lease

            lease = (Lease(task.id, task.lease_owner, task.fencing_token, task.lease_expires_at)
                     if task.lease_owner and task.lease_expires_at is not None else None)
            state = MediaTaskStore(self.session_factory, task.id, kind, lease=lease)
            kwargs.update(load_state=state.load, save_state=state.save,
                          material_loader=media_material_loader(
                              self.session_factory, self.store, task.id, task.user_id))
        if kind == "image":
            from app.agents.image import ImageAgentAdapter, ImageAgentProfile

            values.update(agent_config_id=(routing["agent_config_id"] if task else
                                           str(connection.default_config_id or "")),
                          image_model=(routing["image_model"] if task else connection.image_model))
            if task is not None:
                kwargs["authorize_submission_retry"] = state.can_retry_rejected_submission
            adapter = ImageAgentAdapter(profile=ImageAgentProfile(**values), **kwargs)
        else:
            from app.agents.video import VideoAgentAdapter, VideoAgentProfile

            values["video_audio_enabled"] = (routing.get("video_audio_enabled", False) if task
                                              else connection.video_audio_enabled)
            adapter = VideoAgentAdapter(profile=VideoAgentProfile(**values), **kwargs)
        return AgentBinding(record.agent_id, record.version, kind, PROTOCOLS[kind],
                            content_digest(dict(connection_id=str(connection.id),
                                                base_url=connection.base_url)), adapter)


@dataclass(frozen=True)
class AgentBinding:
    agent_id: str
    agent_version: str
    wire_agent_id: str
    protocol_version: str
    endpoint_digest: str
    adapter: AgentAdapter
