"""Caller-owned transactions and immediate owner checks, including administrators."""

from datetime import UTC
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.catalog.schemas import content_digest
from app.catalog.service import CatalogService
from app.common.pagination import page_rows
from app.common.types import CursorPage
from app.conversations.models import Conversation, Message, Product, ProductVersion
from app.conversations.schemas import (
    ConversationCreate,
    ConversationSummary,
    MessageView,
    ProductVersionView,
)
from app.ledger.service import now


def authenticate(session, principal):
    CatalogService(session)._principal(principal)


def owned_conversation(session, user_id, conversation_id):
    row = session.scalar(
        select(Conversation)
        .where(Conversation.id == str(conversation_id), Conversation.user_id == str(user_id))
        .with_for_update(read=True)
    )
    if row is None:
        raise HTTPException(404)
    return row


def conversation_view(row):
    return ConversationSummary(
        conversation_id=row.id, title=row.title, created_at=row.created_at.replace(tzinfo=UTC)
    )


def product_view(row):
    return ProductVersionView(
        product_id=row.product_id,
        version=row.version,
        product=row.product,
        created_at=row.created_at.replace(tzinfo=UTC),
    )


class ConversationService:
    def __init__(self, session):
        self.session = session

    def create_conversation(self, principal, title):
        authenticate(self.session, principal)
        dto = ConversationCreate(title=title)
        row = Conversation(
            id=str(uuid4()), user_id=str(principal.user_id), title=dto.title, created_at=now()
        )
        self.session.add(row)
        self.session.flush()
        return conversation_view(row)

    def list_conversations(self, principal, cursor=None, limit=20):
        authenticate(self.session, principal)
        rows, next_cursor = page_rows(
            self.session,
            Conversation,
            [Conversation.user_id == str(principal.user_id)],
            cursor,
            limit,
        )
        return CursorPage[ConversationSummary](
            items=[conversation_view(r) for r in rows], next_cursor=next_cursor
        )

    def create_product_version(self, principal, dto):
        authenticate(self.session, principal)
        # Ensure JSON is canonicalizable before any write (NaN/Infinity are not valid facts).
        try:
            content_digest(dto.product)
        except (ValueError, TypeError):
            raise HTTPException(422) from None
        if dto.product_id:
            product = self.session.scalar(
                select(Product).where(
                    Product.id == str(dto.product_id), Product.user_id == str(principal.user_id)
                )
            )
            if product is None:
                raise HTTPException(404)
        else:
            product = Product(id=str(uuid4()), user_id=str(principal.user_id))
            self.session.add(product)
            self.session.flush()
        row = ProductVersion(
            version=str(uuid4()),
            product_id=product.id,
            user_id=str(principal.user_id),
            product=dto.product,
            created_at=now(),
        )
        self.session.add(row)
        self.session.flush()
        return product_view(row)

    def read_product_version(self, principal, version):
        authenticate(self.session, principal)
        row = self.session.scalar(
            select(ProductVersion).where(
                ProductVersion.version == str(version),
                ProductVersion.user_id == str(principal.user_id),
            )
        )
        if row is None:
            raise HTTPException(404)
        return product_view(row)

    def read_conversation(self, principal, id, *, task_cursor=None, message_cursor=None, limit=20):
        from app.conversations.schemas import ConversationView
        from app.tasks.repository import TaskRepository
        from app.works.lifecycle import history_content

        authenticate(self.session, principal)
        row = owned_conversation(self.session, principal.user_id, id)
        messages, next_cursor = page_rows(
            self.session,
            Message,
            [Message.user_id == str(principal.user_id), Message.conversation_id == str(id)],
            message_cursor,
            limit,
        )
        return ConversationView(
            conversation=conversation_view(row),
            tasks=TaskRepository(self.session).list_tasks(principal, id, task_cursor, limit),
            messages=CursorPage[MessageView](
                items=[
                    MessageView(
                        message_id=m.id,
                        task_id=m.task_id,
                        kind=m.kind,
                        role=m.role,
                        content=history_content(self.session, m),
                        created_at=m.created_at.replace(tzinfo=UTC),
                    )
                    for m in messages
                ],
                next_cursor=next_cursor,
            ),
        )
