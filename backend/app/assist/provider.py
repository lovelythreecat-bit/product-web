"""Explicit asynchronous assistance boundary. No live supplier has been approved.

The deterministic implementation only formats user-supplied data; it does not
inspect image/video bytes, call business Agents, or claim factual AI verification.
T23 must supply a separately reviewed live protocol and factual-evidence checks.
"""

import json
from typing import Protocol

from pydantic import Field

from app.assist.schemas import AssistRequest
from app.catalog.schemas import AgentVersion, SpecVersion
from app.common.types import DTO

TEST_SCHEME = "TEST_ONLY_draft_no_meter_v1"


class ProviderRequest(DTO):
    draft: AssistRequest
    agent: AgentVersion
    spec: SpecVersion


class ProviderResponse(DTO):
    proposed: str = Field(min_length=1, max_length=100000)


class PromptAssistProvider(Protocol):
    async def prepare(self, request: ProviderRequest) -> ProviderResponse: ...


class MockPromptAssistProvider:
    async def prepare(self, request: ProviderRequest) -> ProviderResponse:
        draft = request.draft
        focus = {
            "copy": "整理表达目的、受众、语气、结构及长度；未提供的要求请补充。",
            "image": "整理构图、背景、光线、主体、风格及参考素材关系；未提供的要求请补充。",
            "video": "整理画面、镜头与节奏，沿用所选视频规格；未提供的要求请补充。",
        }[request.agent.kind]
        return ProviderResponse(
            proposed="\n".join(
                [
                    "[TEST_ONLY 确定性辅助草案]",
                    f"所选能力：{request.agent.name} / {request.spec.name}",
                    focus,
                    "用户原文：" + draft.original,
                    "用户提供的商品资料："
                    + json.dumps(draft.product, ensure_ascii=False, sort_keys=True),
                    "保留参数：" + json.dumps(draft.parameters, ensure_ascii=False, sort_keys=True),
                    f"本人可用素材数：{len(draft.material_versions)}",
                    "仅使用已提供事实；缺失事实须补充，不推断材质、功效、价格或优惠。",
                ]
            )
        )
