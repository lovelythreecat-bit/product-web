"""Owner-only resource boundary registry. Administrative content grants belong to T19.

Existing routes enforce these same database ownership facts independently. This
registry does not mint transferable credentials or replace download validation.
"""

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.catalog.service import CatalogService
from app.conversations.models import Conversation, Message, Product, ProductVersion
from app.storage.models import File
from app.tasks.models import GenerationTask
from app.works.models import Work

# Actual public surfaces, including resources embedded in another owned response.
RESOURCE_ROUTES = {
    "conversation": ("GET /api/v1/conversations", "GET /api/v1/conversations/{id}"),
    "task": ("GET /api/v1/tasks", "GET /api/v1/tasks/{id}", "GET /api/v1/conversations/{id}"),
    "message": ("GET /api/v1/conversations/{id}", "GET /api/v1/works/{id}"),
    "product": ("POST /api/v1/products/versions", "GET /api/v1/products/versions/{version}"),
    "product_version": (
        "GET /api/v1/products/versions/{version}",
        "GET /api/v1/tasks/{id}",
        "GET /api/v1/works/{id}",
    ),
    "material": ("GET /api/v1/files/{file_id}/content", "POST /api/v1/tasks"),
    "file": ("GET /api/v1/files/{file_id}/content",),
    "file_version": (
        "GET /api/v1/files/{file_id}/content",
        "GET /api/v1/works/{id}",
        "POST /api/v1/tasks",
    ),
    "work": ("GET /api/v1/works", "GET /api/v1/works/{id}"),
}

_MODELS = {
    "conversation": Conversation,
    "task": GenerationTask,
    "message": Message,
    "product": Product,
    "product_version": ProductVersion,
    "material": File,
    "file": File,
    "file_version": File,
    "work": Work,
}


@dataclass(frozen=True)
class ResourceGrant:
    resource_type: str
    resource_id: UUID
    user_id: UUID
    version: str | None = None


def authorize_resource(session, principal, resource_type, resource_id, *, version=None):
    """Recheck the live session and persistent owner; never grant an admin bypass."""
    CatalogService(session)._principal(principal)
    model = _MODELS.get(resource_type)
    if model is None or (resource_type == "file_version" and version is None):
        raise HTTPException(404)
    try:
        resource_id = str(UUID(str(resource_id)))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(404) from None
    identity = model.version if model is ProductVersion else model.id
    predicates = [identity == resource_id, model.user_id == str(principal.user_id)]
    if model is File:
        predicates += [File.state == "durable", File.deleted_at.is_(None)]
        if version is not None:
            predicates.append(File.version == str(version))
    row = session.scalar(select(model).where(*predicates).execution_options(populate_existing=True))
    if row is None:
        raise HTTPException(404)
    return ResourceGrant(
        resource_type,
        UUID(resource_id),
        UUID(row.user_id),
        row.version if model in (File, ProductVersion) else None,
    )
