"""Read only the fixed task owner's protected material versions, outside SQL locks."""

from hashlib import sha256

from sqlalchemy import select

from app.storage.models import File, FileRef

from .text import MAX_IMAGE_BYTES


def material_loader(factory, store, task_id, user_id):
    def load(reference):
        with factory() as session:
            row = session.scalar(
                select(File)
                .join(FileRef, FileRef.file_id == File.id)
                .where(
                    File.id == str(reference["file_id"]),
                    File.version == reference["version"],
                    File.user_id == user_id,
                    File.state == "durable",
                    FileRef.user_id == user_id,
                    FileRef.version == reference["version"],
                    FileRef.ref_type == "task_input",
                    FileRef.ref_id == task_id,
                )
            )
            if row is None or row.actual_bytes > MAX_IMAGE_BYTES:
                raise ValueError("Original task material unavailable")
            path, count, digest, mime = (
                row.internal_path,
                row.actual_bytes,
                row.sha256,
                row.actual_mime,
            )
        with store.read(path) as stream:
            data = stream.read(MAX_IMAGE_BYTES + 1)
        if len(data) != count or sha256(data).hexdigest() != digest:
            raise ValueError("Original task material integrity mismatch")
        return data, mime

    return load
