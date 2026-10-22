"""Every mutation shares its caller's transaction with admission and accounting.

Lock order starts with the authenticated user, then the owned run. Submitted batch
requests never change. A lost response replays the same server-owned task keys.
"""

from copy import deepcopy
from uuid import uuid4

from sqlalchemy import select

from app.catalog.schemas import content_digest
from app.catalog.service import CatalogService
from app.common.types import MAX_REFERENCE_IMAGES, FileVersionRef, InputSnapshot, SubmitTaskRequest
from app.conversations.models import ProductVersion
from app.conversations.service import ConversationService, authenticate
from app.ledger.service import now
from app.quick_generation.errors import QuickGenerationError
from app.quick_generation.models import QuickGenerationRun
from app.quick_generation.schemas import QuickDraft, QuickState, QuickSummary, QuickView
from app.storage.models import CapacityReservation, File
from app.tasks.admission import AdmissionService
from app.tasks.failed_actions import successor_key
from app.tasks.models import GenerationTask
from app.tasks.repository import TaskRepository
from app.works.models import Work, WorkItem

LABELS = {"main_image": "商品主图 · 1 张", "detail_page": "详情图 · 3 张",
          "long_image": "商品长图 · 1 张", "copy": "营销文案", "video": "视频"}


def require_complete(tasks):
    if not tasks or any(t.state != "SUCCEEDED" or t.settlement_state != "CONSUMED"
                        for t in tasks):
        raise QuickGenerationError(409, "请等待完整成果保存成功后再确认。")


def require_reference_limit(materials):
    if len(materials) > MAX_REFERENCE_IMAGES:
        raise QuickGenerationError(422, "商品参考图最多支持 4 张，请移除多余图片后再生成。")


def build_input(draft, product, kind, confirmed_copy=None, output=None, *, video_materials=None,
                confirmed_copy_types=()):
    materials = draft.material_versions
    if kind == "copy":
        parameters, instruction = draft.copy_parameters, draft.copy_instruction
    else:
        if not confirmed_copy:
            raise QuickGenerationError(409, "请先确认营销文案。")
        if kind == "image":
            if not draft.image_platform or output not in LABELS or output in {"copy", "video"}:
                raise QuickGenerationError(422, "请选择目标平台和图片内容。")
            parameters = {"platform": draft.image_platform, "output_type": output}
            detail_copy = (draft.copy_texts.get("详情介绍", "").strip()
                           if "详情介绍" in confirmed_copy_types else "")
            if list(confirmed_copy_types) == ["详情介绍"]:
                detail_copy = confirmed_copy.strip()
            instruction = detail_copy
        else:
            candidates = materials if video_materials is None else video_materials
            materials = [m for m in candidates
                         if str(m.file_id) == draft.video_first_frame_file_id]
            if len(materials) != 1:
                raise QuickGenerationError(422, "请选择可用的商品参考图或本次图片成果作为视频首帧。")
            parameters = {"first_frame_file_id": draft.video_first_frame_file_id}
            instruction = draft.video_instruction
            instruction = (instruction + "\n\n已由用户确认的营销文案（仅作为创作输入，"
                           "商品事实以商品资料和参考图为准）：\n" + confirmed_copy)
    return InputSnapshot(product_version=product.version, product=deepcopy(product.product),
                         instruction=instruction, parameters=deepcopy(parameters),
                         material_versions=materials)


def invalidate_downstream(state, old, new):
    product_changed = (old.product_version != new.product_version
                       or old.material_versions != new.material_versions)
    if product_changed:
        state["step"] = 1
        state["current"]["copy"] = None
    copy_changed = old.copy_text != new.copy_text or old.copy_texts != new.copy_texts
    if product_changed or copy_changed:
        state["confirmed_copy"] = None
        state["current"]["image"] = None
        if not product_changed:
            state["step"] = min(state["step"], 2)
    images_changed = (old.image_platform != new.image_platform
                      or old.image_outputs != new.image_outputs
                      or old.image_instruction != new.image_instruction)
    if product_changed or copy_changed or images_changed:
        state["confirmed_images"] = None
        state["current"]["video"] = None
        if images_changed and not product_changed and not copy_changed:
            state["current"]["image"] = None
            state["step"] = min(state["step"], 3)
    if (old.video_first_frame_file_id != new.video_first_frame_file_id
            or old.video_instruction != new.video_instruction):
        state["current"]["video"] = None
        state["step"] = min(state["step"], 4)
    state["pending_batch"] = None


class QuickGenerationService:
    def __init__(self, session, settings):
        self.session, self.settings = session, settings

    def owned(self, principal, run_id, *, write=False):
        authenticate(self.session, principal)
        query = select(QuickGenerationRun).where(
            QuickGenerationRun.id == str(run_id),
            QuickGenerationRun.user_id == str(principal.user_id))
        if write:
            query = query.with_for_update().execution_options(populate_existing=True)
        row = self.session.scalar(query)
        if row is None:
            raise QuickGenerationError(404)
        return row

    def product(self, principal, draft):
        product = self.session.scalar(select(ProductVersion).where(
            ProductVersion.version == draft.product_version,
            ProductVersion.user_id == str(principal.user_id)))
        if product is None:
            raise QuickGenerationError(422, "请先保存商品资料。")
        return product

    def summary(self, row):
        draft = row.state["draft"]
        product = self.session.get(ProductVersion, draft.get("product_version")) \
            if draft.get("product_version") else None
        return QuickSummary(run_id=row.id, conversation_id=row.conversation_id,
                            title=str(product.product.get("name", "快速生成"))
                            if product else "快速生成", step=row.state["step"],
                            version=row.version)

    def list(self, principal):
        authenticate(self.session, principal)
        rows = self.session.scalars(select(QuickGenerationRun).where(
            QuickGenerationRun.user_id == str(principal.user_id)).order_by(
                QuickGenerationRun.updated_at.desc(), QuickGenerationRun.id.desc()).limit(50))
        return [self.summary(row) for row in rows]

    def create(self, principal, run_id):
        authenticate(self.session, principal)
        row = self.session.get(QuickGenerationRun, str(run_id))
        if row is not None:
            if row.user_id != str(principal.user_id):
                raise QuickGenerationError(404)
            return row
        conversation = ConversationService(self.session).create_conversation(principal, "快速生成")
        state = QuickState(step=1, draft=QuickDraft(),
                           current={"copy": None, "image": None, "video": None})
        row = QuickGenerationRun(id=str(run_id), user_id=str(principal.user_id),
                                 conversation_id=str(conversation.conversation_id),
                                 version=1, state=state.model_dump(mode="json"),
                                 created_at=now(), updated_at=now())
        self.session.add(row)
        self.session.flush()
        return row

    def check_version(self, row, version):
        if row.version != version:
            raise QuickGenerationError(409, "进度已在其他窗口更新，请重新读取后继续。")

    def require_editable(self, row):
        if row.state["step"] == 5:
            raise QuickGenerationError(409, "此快速生成已完成，仅可只读查看。请新建快速生成。")

    def change(self, row, state):
        row.state = state
        row.version += 1
        row.updated_at = now()
        self.session.flush()

    def task(self, row, task_id):
        task = self.session.scalar(select(GenerationTask).where(
            GenerationTask.id == task_id, GenerationTask.user_id == row.user_id,
            GenerationTask.conversation_id == row.conversation_id))
        if task is None:
            raise QuickGenerationError(404)
        # Follow the existing failure-retry chain; never replace its original request.
        for _ in range(100):
            next_task = self.session.scalar(select(GenerationTask).where(
                GenerationTask.user_id == row.user_id,
                GenerationTask.idempotency_key == successor_key(task.id)))
            if next_task is None:
                return task
            task = next_task
        raise QuickGenerationError(409)

    def view(self, principal, row):
        tasks = {}
        for batch in row.state["batches"]:
            current = batch["id"] in row.state["current"].values()
            if not current and not (batch["kind"] == "image" and batch["submitted"]):
                continue
            for item in batch["items"]:
                if item["task_id"] and item["task_id"] not in tasks:
                    actual = self.task(row, item["task_id"])
                    # Saved image versions remain visible after replacement. Old
                    # failures are not active tasks and must not lock the workflow.
                    if not current and actual.state != "SUCCEEDED":
                        continue
                    tasks[item["task_id"]] = TaskRepository(self.session).read_task(
                        principal, actual.id)
        return QuickView(**self.summary(row).model_dump(), state=row.state, tasks=tasks)

    def current_tasks(self, row, kind):
        batch_id = row.state["current"].get(kind)
        batch = next((b for b in row.state["batches"] if b["id"] == batch_id), None)
        if not batch or not batch["submitted"]:
            return []
        return [self.task(row, item["task_id"]) for item in batch["items"]]

    def video_materials(self, row, draft):
        """Resolve one owned file without turning generated output into product input."""
        selected = draft.video_first_frame_file_id
        file = self.session.get(File, selected) if selected else None
        reference = next((ref for ref in draft.material_versions
                          if str(ref.file_id) == selected), None)
        if reference is not None:
            reservation = self.session.get(CapacityReservation, file.reservation_id) if file else None
            if (reservation is None or reservation.user_id != row.user_id
                    or not reservation.intent_id.startswith("upload:")):
                # A client-supplied reference does not establish an upload origin.
                reference = None
        if reference is None:
            confirmed = row.state["confirmed_images"]
            if not confirmed or confirmed != row.state["current"]["image"]:
                raise QuickGenerationError(422, "请从本次已确认的图片成果中选择视频首帧。")
            tasks = self.current_tasks(row, "image")
            require_complete(tasks)
            for task in tasks:
                work = self.session.scalar(select(Work).where(
                    Work.task_id == task.id, Work.user_id == row.user_id,
                    Work.conversation_id == row.conversation_id,
                    Work.deleted_at.is_(None)))
                if (work is None or work.task_id != task.id or work.user_id != row.user_id
                        or work.conversation_id != row.conversation_id
                        or work.deleted_at is not None):
                    continue
                item = self.session.scalar(select(WorkItem).where(
                    WorkItem.work_id == work.id, WorkItem.user_id == row.user_id,
                    WorkItem.file_id == selected))
                if (item is not None and item.work_id == work.id
                        and item.user_id == row.user_id and item.file_id == selected):
                    reference = FileVersionRef(file_id=item.file_id, version=item.file_version)
                    break
        if (reference is None or file is None or file.user_id != row.user_id
                or file.version != reference.version
                or file.deleted_at is not None or file.state != "durable"
                or file.actual_mime not in {"image/png", "image/jpeg", "image/webp"}
                or not 0 < file.actual_bytes <= 20 * 1024 * 1024):
            raise QuickGenerationError(422, "所选视频首帧不可用，请重新选择图片。")
        return [reference]

    def save(self, principal, row, dto):
        self.require_editable(row)
        self.check_version(row, dto.version)
        state = deepcopy(row.state)
        old = QuickDraft.model_validate(state["draft"])
        # Saved history remains readable. Oversized legacy drafts may retain or
        # remove their existing references, but cannot add or replace references.
        if (len(dto.draft.material_versions) > MAX_REFERENCE_IMAGES
                and (len(dto.draft.material_versions) > len(old.material_versions)
                     or any(ref not in old.material_versions
                            for ref in dto.draft.material_versions))):
            require_reference_limit(dto.draft.material_versions)
        if dto.draft.product_version:
            self.product(principal, dto.draft)
        # Freezing the draft also prevents losing track of active upstream requests.
        if dto.draft != old:
            for kind in ("copy", "image", "video"):
                if any(t.state not in {"SUCCEEDED", "FAILED", "MANUALLY_CLOSED"}
                       or t.state == "FAILED" and t.settlement_state == "FROZEN"
                       for t in self.current_tasks(row, kind)):
                    raise QuickGenerationError(409, "任务处理中，请等待完成或处置失败任务后修改。")
            invalidate_downstream(state, old, dto.draft)
        state["draft"] = dto.draft.model_dump(mode="json")
        self.change(row, state)

    def prepare(self, principal, row, dto):
        self.require_editable(row)
        self.check_version(row, dto.version)
        state = deepcopy(row.state)
        draft = QuickDraft.model_validate(state["draft"])
        require_reference_limit(draft.material_versions)
        product = self.product(principal, draft)
        if dto.kind != "copy" and not state["confirmed_copy"]:
            raise QuickGenerationError(409, "请先确认营销文案。")
        if dto.kind == "video" and not state["confirmed_images"]:
            raise QuickGenerationError(409, "请先确认完整图片成果。")
        previous = [task for kind in ("copy", "image", "video")
                    for task in self.current_tasks(row, kind)]
        if any(t.state not in {"SUCCEEDED", "FAILED", "MANUALLY_CLOSED"}
               or t.state == "FAILED" and t.settlement_state == "FROZEN" for t in previous):
            raise QuickGenerationError(409, "原任务尚未结束，请等待或处置失败任务。")
        catalog = CatalogService(self.session, mode=self.settings.mode)
        if dto.item_index is not None:
            if dto.kind not in {"copy", "image"} or dto.outputs is not None:
                raise QuickGenerationError(422)
            old_batch = next((b for b in state["batches"]
                              if b["id"] == state["current"][dto.kind]), None)
            if (old_batch is None or not old_batch["submitted"]
                    or dto.item_index >= len(old_batch["items"])):
                raise QuickGenerationError(409, "请选择当前已完成的创作内容。")
            item = old_batch["items"][dto.item_index]
            require_complete([self.task(row, item["task_id"])])
            request = SubmitTaskRequest.model_validate(item["request"])
            quote = catalog.quote_agent(principal, request.input, request.agent_id)
            replacement = deepcopy(item)
            replacement.update(
                request=request.model_copy(update={"confirmed_quote": quote}).model_dump(
                    mode="json"),
                task_id=None, regeneration_of=item["task_id"],
                free_regenerations_used=item.get("free_regenerations_used", 0),
                free_regeneration=item.get("free_regenerations_used", 0) < 3,
            )
            items = deepcopy(old_batch["items"])
            items[dto.item_index] = replacement
            batch = dict(id=str(uuid4()), kind=dto.kind, submitted=False,
                         draft_digest=content_digest(state["draft"]), items=items)
            state["batches"].append(batch)
            state["pending_batch"] = batch["id"]
            self.change(row, state)
            return batch
        candidates = [a for a in catalog.list_agents() if a.kind == dto.kind and a.enabled]
        if len(candidates) != 1:
            raise QuickGenerationError(409, "当前创作类型尚未配置唯一可用服务。")
        agent = candidates[0]
        copy_reads_images = True
        if dto.kind == "copy" and draft.material_versions:
            from app.agents.text import PROTOCOL as TEXT_PROTOCOL
            from app.agents.text_runtime import resolve_text_profile

            if agent.protocol_version == TEXT_PROTOCOL:
                copy_reads_images = resolve_text_profile(
                    self.session, self.settings,
                ).supports_images
        if dto.kind == "image":
            outputs = list(dict.fromkeys(draft.image_outputs))
        elif dto.kind == "copy":
            outputs = draft.copy_types or [None]
        else:
            outputs = [None]
        if not outputs:
            raise QuickGenerationError(422, "请选择至少一种图片内容。")
        # A released failure can be regenerated alone while retaining successful siblings.
        preserved = []
        previous_outputs = {}
        if dto.outputs is not None:
            requested = list(dict.fromkeys(dto.outputs))
            if dto.kind != "image" or not requested or not set(requested).issubset(outputs):
                raise QuickGenerationError(422)
            old_batch = next((b for b in state["batches"]
                              if b["id"] == state["current"]["image"]), None)
            if old_batch is None:
                raise QuickGenerationError(409)
            for item in old_batch["items"]:
                previous_output = item["request"]["input"]["parameters"]["output_type"]
                previous_outputs[previous_output] = item
                if previous_output not in requested:
                    require_complete([self.task(row, item["task_id"])])
                    preserved.append(deepcopy(item))
            outputs = requested
        items = []
        video_materials = self.video_materials(row, draft) if dto.kind == "video" else None
        confirmed_copy_batch = next((batch for batch in state["batches"]
                                     if batch["id"] == state["current"]["copy"]), None)
        confirmed_copy_types = [item["request"]["input"]["parameters"].get("copy_type")
                                for item in confirmed_copy_batch["items"]] if confirmed_copy_batch else []
        for output in outputs:
            input_snapshot = build_input(draft, product, dto.kind, state["confirmed_copy"], output,
                                         video_materials=video_materials,
                                         confirmed_copy_types=confirmed_copy_types)
            if dto.kind == "copy" and output is not None:
                input_snapshot = input_snapshot.model_copy(update={
                    "parameters": {**input_snapshot.parameters, "copy_type": output}})
            if dto.kind == "copy" and not copy_reads_images:
                # Keep the workflow's originals for later image/video steps. The
                # quoted immutable copy request contains only what this model reads.
                input_snapshot = input_snapshot.model_copy(update={"material_versions": []})
            quote = catalog.quote_agent(principal, input_snapshot, agent.agent_id)
            request = SubmitTaskRequest(conversation_id=row.conversation_id,
                                        agent_id=agent.agent_id, input=input_snapshot,
                                        confirmed_quote=quote)
            label = (output or LABELS["copy"]) if dto.kind == "copy" else LABELS[output or dto.kind]
            item = dict(label=label, request=request.model_dump(mode="json"), task_id=None)
            if output in previous_outputs:
                previous_item = previous_outputs[output]
                item.update(free_regenerations_used=previous_item.get("free_regenerations_used", 0),
                            regeneration_of=previous_item["task_id"])
            items.append(item)
        batch_items = preserved + items
        if previous_outputs:
            by_output = {item["request"]["input"]["parameters"]["output_type"]: item
                         for item in batch_items}
            batch_items = [by_output[output] for output in previous_outputs]
        batch = dict(id=str(uuid4()), kind=dto.kind, submitted=False,
                     draft_digest=content_digest(state["draft"]), items=batch_items)
        state["batches"].append(batch)
        state["pending_batch"] = batch["id"]
        self.change(row, state)
        return batch

    def submit(self, principal, row, batch_id):
        state = deepcopy(row.state)
        batch = next((b for b in state["batches"] if b["id"] == str(batch_id)), None)
        if batch is None:
            raise QuickGenerationError(404)
        if batch["submitted"]:
            return
        self.require_editable(row)
        require_reference_limit(state["draft"]["material_versions"])
        if (state["pending_batch"] != batch["id"]
                or batch["draft_digest"] != content_digest(state["draft"])):
            raise QuickGenerationError(409, "本次确认已失效，请重新核对费用。")
        # All admissions/freeze writes roll back together if any quote or gate fails.
        replaced_copy_types = []
        is_copy_regeneration = False
        for index, item in enumerate(batch["items"]):
            if item["task_id"]:
                continue
            admission_options = {}
            if item.get("free_regeneration"):
                admission_options["free_regeneration"] = True
            admitted = AdmissionService(self.session, self.settings).admit_task(
                principal, f"quick:{row.id}:{batch['id']}:{index}",
                SubmitTaskRequest.model_validate(item["request"]), **admission_options)
            item["task_id"] = str(admitted.task.task_id)
            if item.get("free_regeneration"):
                item["free_regenerations_used"] = item.get("free_regenerations_used", 0) + 1
            if batch["kind"] == "copy" and item.get("regeneration_of"):
                is_copy_regeneration = True
                replaced_copy_types.append(item["request"]["input"]["parameters"].get("copy_type"))
        batch["submitted"] = True
        state["current"][batch["kind"]] = batch["id"]
        state["pending_batch"] = None
        if batch["kind"] == "copy":
            state["step"] = 2
            if is_copy_regeneration:
                texts = state["draft"].get("copy_texts", {})
                for copy_type in replaced_copy_types:
                    texts.pop(copy_type, None)
                state["draft"]["copy_texts"] = texts
                sections = []
                for item in batch["items"]:
                    copy_type = item["request"]["input"]["parameters"].get("copy_type")
                    text = texts.get(copy_type, "").strip()
                    if text:
                        sections.append(f"【{copy_type}】\n{text}")
                state["draft"]["copy_text"] = "\n\n".join(sections)
            else:
                state["draft"]["copy_text"] = ""
                state["draft"]["copy_texts"] = {}
            state["confirmed_copy"] = state["confirmed_images"] = None
            state["current"]["image"] = state["current"]["video"] = None
        elif batch["kind"] == "image":
            state["step"] = 3
            state["confirmed_images"] = None
            state["current"]["video"] = None
        else:
            state["step"] = 4
        self.change(row, state)

    def cancel_batch(self, row, batch_id):
        self.require_editable(row)
        state = deepcopy(row.state)
        batch = next((b for b in state["batches"] if b["id"] == str(batch_id)), None)
        if batch is None:
            raise QuickGenerationError(404)
        # A concurrent submit is serialized by owned(): committed tasks are retained.
        if not batch["submitted"] and state["pending_batch"] == batch["id"]:
            state["pending_batch"] = None
            self.change(row, state)

    def advance(self, row, dto):
        self.require_editable(row)
        self.check_version(row, dto.version)
        state = deepcopy(row.state)
        if dto.action == "back":
            state["step"] = max(1, state["step"] - 1)
        elif dto.action == "confirm_copy":
            require_complete(self.current_tasks(row, "copy"))
            text = state["draft"]["copy_text"].strip()
            batch = next((b for b in state["batches"]
                          if b["id"] == state["current"]["copy"]), None)
            texts = state["draft"].get("copy_texts", {})
            if batch and (len(batch["items"]) > 1 or texts):
                sections = []
                for item in batch["items"]:
                    copy_type = item["request"]["input"]["parameters"].get("copy_type")
                    content = texts.get(copy_type, "").strip()
                    if not content:
                        raise QuickGenerationError(422, "请填写并确认每种营销文案。")
                    sections.append(f"【{copy_type}】\n{content}")
                text = "\n\n".join(sections)
                if len(text) > 100000:
                    raise QuickGenerationError(422, "营销文案总长度不能超过 100000 个字符。")
            if not text:
                raise QuickGenerationError(422, "请填写并确认营销文案。")
            state["draft"]["copy_text"] = text
            state["confirmed_copy"] = text
            state["step"] = 3
        elif dto.action == "confirm_images":
            if not state["confirmed_copy"]:
                raise QuickGenerationError(409)
            require_complete(self.current_tasks(row, "image"))
            state["confirmed_images"] = state["current"]["image"]
            state["step"] = 4
        else:
            if not state["confirmed_copy"] or not state["confirmed_images"]:
                raise QuickGenerationError(409)
            require_complete(self.current_tasks(row, "video"))
            state["step"] = 5
        state["pending_batch"] = None
        self.change(row, state)
