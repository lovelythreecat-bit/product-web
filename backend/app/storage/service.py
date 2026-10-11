"""Upload phases; the route owns short SQL transactions around network/file work.

prepare_upload and finalize_upload are synchronous shared-Session services and
never commit. upload_file performs no SQL and offloads the bounded decoder.
"""

from datetime import UTC, datetime
from uuid import uuid4

from starlette.concurrency import run_in_threadpool

from app.common.types import FileVersionRef
from app.storage.capacity import finalize_capacity, reserve_capacity
from app.storage.models import File
from app.storage.schemas import upload_policy
from app.storage.validation import validate_content, validate_name


class UploadService:
    def __init__(self, session, store, policy_version, *, mode):
        self.session, self.store = session, store
        self.policy_version, self.mode = policy_version, mode
        self.staged = None
        self.reservation_id = None
        self.file = None
        self.policy = None

    def prepare_upload(self, principal, display_name):
        self.policy = upload_policy(self.session, self.policy_version, self.mode)
        validate_name(display_name)
        self.store.require_space(self.policy.max_file_bytes)
        reservation = reserve_capacity(
            self.session,
            principal.user_id,
            "upload:" + uuid4().hex,
            self.policy.max_file_bytes,
            self.policy_version,
            mode=self.mode,
        )
        self.reservation_id = reservation.id
        # Journal precedes the caller's reservation commit, including ambiguous outcomes.
        self.staged = self.store.prepare_upload(principal.user_id, self.reservation_id)

    async def upload_file(self, principal, stream, display_name, *, declared_mime):
        if self.policy is None or self.reservation_id is None or self.staged is None:
            raise RuntimeError("Caller must persist the prepared reservation before reading input")
        self.staged = await self.store.stage(
            stream, principal.user_id, self.policy.max_file_bytes, prepared=self.staged
        )
        mime = await run_in_threadpool(
            validate_content,
            self.store.staged_path(self.staged),
            display_name,
            declared_mime,
            self.policy.allowed_types,
        )
        key = await run_in_threadpool(self.store.commit, self.staged)
        file_id, version = str(uuid4()), str(uuid4())
        self.file = File(
            id=file_id,
            version=version,
            user_id=str(principal.user_id),
            internal_path=key,
            actual_mime=mime,
            actual_bytes=self.staged.actual_bytes,
            sha256=self.staged.sha256,
            display_name=display_name,
            state="durable",
            created_at=datetime.now(UTC).replace(tzinfo=None),
            reservation_id=self.reservation_id,
        )
        return FileVersionRef(file_id=file_id, version=version)

    def finalize_upload(self):
        # The caller revalidates the live session before entering this short transaction.
        finalize_capacity(self.session, self.reservation_id, self.staged.actual_bytes)
        self.session.add(self.file)
        self.session.flush()
