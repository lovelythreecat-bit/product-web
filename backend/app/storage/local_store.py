"""Private local disk with random paths, bounded streaming and recovery journals.

A journal survives until the caller confirms its DB commit. After ambiguous DB
commit failures it MUST be retained and reconciled against MySQL; never blindly
remove a potentially referenced file. No automatic expiry or physical GC here.
"""

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.storage.capacity import StorageError
from app.storage.validation import FileValidationError


@dataclass(frozen=True)
class StagedFile:
    key: str
    actual_bytes: int
    sha256: str
    reservation_id: str | None = None


class LocalStore:
    def __init__(self, root):
        if root is None or not Path(root).is_absolute():
            raise StorageError("FEATURE_NOT_ENABLED", 403)
        self.root = Path(root)
        self._check(self.root)
        if not self.root.is_dir():
            raise StorageError("FEATURE_NOT_ENABLED", 403)

    def _check(self, path):
        for part in (path, *path.parents):
            if part.is_symlink() or part.is_junction():
                raise HTTPException(422)
        if path != self.root and not path.is_relative_to(self.root):
            raise HTTPException(422)
        return path

    def _path(self, key, suffix):
        if not re.fullmatch(r"[a-f0-9]{32}/[a-f0-9]{32}", key):
            raise HTTPException(422)
        return self._check(self.root / (key + suffix))

    def free_bytes(self):
        return shutil.disk_usage(self.root).free

    def require_space(self, estimated_bytes):
        if self.free_bytes() < estimated_bytes:
            raise StorageError()

    def _sync_directory(self, path):
        if os.name != "nt":
            fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    def _journal(self, staged, state):
        target = self._path(staged.key, ".journal")
        temporary = self._path(staged.key, ".journal-tmp")
        payload = {
            "key": staged.key,
            "state": state,
            "bytes": staged.actual_bytes,
            "sha256": staged.sha256,
            "reservation_id": staged.reservation_id,
        }
        with temporary.open("x", encoding="utf-8") as f:
            json.dump(payload, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, target)
        self._sync_directory(target.parent)

    def prepare_upload(self, user_id, reservation_id):
        staged = StagedFile(UUID(str(user_id)).hex + "/" + uuid4().hex, 0, "", reservation_id)
        self._path(staged.key, ".part").parent.mkdir(exist_ok=True)
        try:
            self._journal(staged, "reservation_pending")
            return staged
        except BaseException:
            self.discard(staged)
            raise

    def mark_aborted(self, staged):
        self._journal(staged, "aborted_before_completion")

    async def stage(self, stream, user_id, max_bytes, *, prepared=None):
        key = prepared.key if prepared else UUID(str(user_id)).hex + "/" + uuid4().hex
        path = self._path(key, ".part")
        path.parent.mkdir(exist_ok=True)
        self._check(path.parent)
        self.require_space(max_bytes)
        digest, count = hashlib.sha256(), 0
        staged = prepared or StagedFile(key, 0, "")
        try:
            self._journal(staged, "staging")
            with path.open("xb") as f:

                async def chunks():
                    if hasattr(stream, "__aiter__"):
                        async for chunk in stream:
                            yield chunk
                    else:
                        while chunk := stream.read(65536):
                            yield chunk

                async for chunk in chunks():
                    if not isinstance(chunk, bytes):
                        raise HTTPException(422)
                    count += len(chunk)
                    if count > max_bytes:
                        raise FileValidationError("size")
                    self.require_space(len(chunk))
                    digest.update(chunk)
                    f.write(chunk)
                if count == 0:
                    raise FileValidationError("empty")
                f.flush()
                os.fsync(f.fileno())
            staged = StagedFile(key, count, digest.hexdigest(), staged.reservation_id)
            self._journal(staged, "staged")
            return staged
        except BaseException:
            if prepared is None:
                self.discard(staged)
            else:
                # The durable reservation may need a later idempotent release.
                # Keep its journal until the caller confirms the release commit.
                self._path(key, ".part").unlink(missing_ok=True)
            raise

    def staged_path(self, staged):
        return self._path(staged.key, ".part")

    def commit(self, staged):
        source, target = self.staged_path(staged), self._path(staged.key, ".blob")
        if target.exists():
            raise StorageError("IDEMPOTENCY_CONFLICT")
        # Recovery information is fsynced before publishing. Rename stays on this filesystem.
        self._journal(staged, "publishing")
        os.replace(source, target)
        self._sync_directory(target.parent)
        return staged.key

    def acknowledge(self, staged):
        self._path(staged.key, ".journal").unlink(missing_ok=True)
        self._sync_directory(self._path(staged.key, ".blob").parent)

    def discard(self, staged):
        # Only for a definitely uncommitted operation owned by this caller.
        for suffix in (".part", ".blob", ".journal-tmp", ".journal"):
            self._path(staged.key, suffix).unlink(missing_ok=True)

    def read(self, key):
        path = self._path(key, ".blob")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        return os.fdopen(os.open(path, flags), "rb")
