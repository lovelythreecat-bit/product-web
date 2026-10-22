"""Ordinary regeneration entitlements, serialized by the existing owner lock.

Each immutable price snapshot records its chain and the accepted free-use count.
Branches and failure successors share that chain; selecting an older result never
resets its allowance. No mutable counters or schema migration are required.
"""

from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import or_, select

from app.catalog.schemas import content_digest
from app.catalog.service import CatalogError, CatalogService
from app.conversations.service import authenticate
from app.quick_generation.models import QuickGenerationRun
from app.tasks.models import GenerationTask, TaskSnapshot
from app.tasks.schemas import RegenerationQuote, RegenerationState


def same_content(original, requested):
    def payload(value):
        if hasattr(value, 'model_dump'):
            value = value.model_dump(mode='json')
        return {key: item for key, item in value.items() if key != 'product_version'}

    return content_digest(payload(original)) == content_digest(payload(requested))


@dataclass(frozen=True)
class Decision:
    root_task_id: str
    source_task_id: str
    eligible: bool
    free_regenerations_used: int
    credits: int

    @property
    def free(self):
        return self.eligible and self.free_regenerations_used < 3

    @property
    def metadata(self):
        if not self.eligible:
            return None
        return dict(root_task_id=self.root_task_id, source_task_id=self.source_task_id,
                    free_regenerations_used=self.free_regenerations_used + int(self.free))


class RegenerationService:
    def __init__(self, session, settings=None):
        self.session, self.settings = session, settings

    def current_read(self, query):
        info = getattr(self.session, 'info', {})
        if isinstance(info, dict) and info.get('read_only_request', False):
            return query
        return query.with_for_update(read=True)

    def owned(self, principal, task_id):
        authenticate(self.session, principal)
        row = self.session.scalar(self.current_read(select(GenerationTask).where(
            GenerationTask.id == str(task_id),
            GenerationTask.user_id == str(principal.user_id),
        )).execution_options(populate_existing=True))
        if row is None:
            raise HTTPException(404)
        return row, self.session.get(TaskSnapshot, row.id)

    def is_quick(self, row):
        return self.session.scalar(self.current_read(select(QuickGenerationRun.id).where(
            QuickGenerationRun.conversation_id == row.conversation_id,
            QuickGenerationRun.user_id == row.user_id,
        ))) is not None

    def state(self, row, snapshot):
        if snapshot.agent_snapshot.get('kind') not in {'copy', 'image'} or self.is_quick(row):
            return None
        root = snapshot.price_snapshot.get('regeneration', {}).get('root_task_id', row.id)
        counts = self.session.scalars(self.current_read(select(
            TaskSnapshot.price_snapshot['regeneration']['free_regenerations_used'].as_integer()
        ).where(
            TaskSnapshot.user_id == row.user_id,
            TaskSnapshot.price_snapshot['regeneration']['root_task_id'].as_string() == root,
        ))).all()
        used = min(3, max([0, *[value for value in counts if value is not None]]))
        return RegenerationState(root_task_id=root, free_regenerations_used=used,
                                 free_regenerations_remaining=3 - used)

    def decision(self, principal, source_id, agent_id, input, standard_credits):
        row, snapshot = self.owned(principal, source_id)
        if row.state != 'SUCCEEDED':
            raise HTTPException(409, detail='请选择已完成的任务重新生成。')
        state = self.state(row, snapshot)
        eligible = bool(state and str(agent_id) == row.agent_id
                        and same_content(snapshot.input_snapshot, input))
        used = state.free_regenerations_used if state else 0
        return Decision(str(state.root_task_id) if state else row.id, row.id, eligible, used,
                        0 if eligible and used < 3 else standard_credits)

    def quote(self, principal, source_id, dto):
        # Owner validation precedes catalog reads; quote and entitlement use one lock.
        self.owned(principal, source_id)
        quote = CatalogService(self.session, mode=self.settings.mode).quote_agent(
            principal, dto.input, dto.agent_id)
        decision = self.decision(principal, source_id, dto.agent_id, dto.input, quote.credits)
        return RegenerationQuote(quote=quote, credits=decision.credits,
            eligible=decision.eligible, free_regenerations_used=decision.free_regenerations_used,
            free_regenerations_remaining=3 - decision.free_regenerations_used
            if decision.eligible else 0)

    def confirm(self, principal, confirmation, agent_id, input, standard_credits):
        try:
            decision = self.decision(
                principal, confirmation.source_task_id, agent_id, input, standard_credits)
        except HTTPException as exc:
            if exc.status_code == 404:
                # No source existence disclosure; admission is definitely rejected.
                raise CatalogError('INPUT_INVALID', 404) from None
            raise
        if (decision.credits != confirmation.expected_credits
                or decision.free_regenerations_used != confirmation.expected_used):
            raise CatalogError('QUOTE_STALE', 409, current_quotes=[], current_specs=[])
        return decision

    def history(self, principal, task_id):
        from app.tasks.repository import TaskRepository

        row, snapshot = self.owned(principal, task_id)
        state = self.state(row, snapshot)
        if state is None:
            return []
        root = str(state.root_task_id)
        ids = self.session.scalars(select(GenerationTask.id).join(
            TaskSnapshot, TaskSnapshot.task_id == GenerationTask.id,
        ).where(
            GenerationTask.user_id == str(principal.user_id),
            GenerationTask.id != row.id,
            GenerationTask.state == 'SUCCEEDED',
            GenerationTask.created_at <= row.created_at,
            or_(GenerationTask.id == root,
                TaskSnapshot.price_snapshot['regeneration']['root_task_id'].as_string() == root),
        ).order_by(GenerationTask.created_at.desc(), GenerationTask.id.desc())).all()
        repository = TaskRepository(self.session)
        return [repository.read_task(principal, id, include_regeneration=False).model_copy(
            update={'regeneration': state}) for id in ids]
