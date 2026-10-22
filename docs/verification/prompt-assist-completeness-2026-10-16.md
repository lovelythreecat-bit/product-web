# AI 帮我完善：指令完整性修复

日期：2026-10-16。范围：创作工作台指令辅助的服务端输出质量，不改页面字段、采用／撤回操作或生成计费。

## 问题与依据

用户反馈完善后的正文出现“待用户补充”。代码核查发现，真实模型的系统提示明确要求“缺少事实时写明待用户补充”，把不编造商品事实错误落实成待填模板；服务层还无条件将材质、功效、价格、优惠列为缺失信息，即使当前创作并不需要这些字段。旧测试同样默认期待这些可选字段缺失。

本次按用户反馈修正：辅助应利用已有资料完成创作指令；商品事实不足时省略未知事实，主动完善表达、结构、构图或镜头安排。所选能力真正必需的资料仍通过既有 `missing_facts` 独立提示，不混入指令正文，也不虚构材质、价格、功效等事实。

## 修改

- `backend/app/assist/provider.py`：明确输出完整可执行正文，不输出待填项或问题清单；保留原意和已选参数，不将素材数量误作素材内容。缺少具体主体资料时使用“提供的商品”指代。
- 对常见中文待填／追问表述及 TODO／TBD 检查，命中时自动重试一次；仍不合格返回既有 503，不回填半成品。重试共用原总超时和响应体大小限制，不自动创建生成任务。
- 检查覆盖“无需补充／不需要用户补充”的否定语句、中文邻接英文标记、“请提供商品材质”等边界。规则用于检测已覆盖的常见模式，不代表穷尽所有自然语言表达。
- `backend/app/assist/service.py`：删除四个硬编码可选商品字段，继续提示能力声明的必填商品字段、必填参数、必要素材及原始指令。
- 确定性测试 provider 同步去除要求用户补全的固定文案；单元和集成测试更新对应预期。

## 验证

使用项目 `backend/.venv/Scripts/python.exe`，在 `backend` 目录执行。Windows 沙箱内 asyncio 创建回环 socketpair 挂起，定位堆栈后在允许本地套接字的执行环境中运行，未关闭生产 TLS 校验或更改事件循环。

1. 测试先行复现：首轮 17 项失败，原因分别为无条件可选字段提示、半成品原样返回以及未拒绝持续待填结果。初步修复后 35 项通过。
2. 独立评审发现否定语句误判及两种漏检，补回归后确认 8 项失败，再修复规则。
3. 最终专项命令：`python -X utf8 -m pytest tests/unit/test_live_prompt_assist.py tests/integration/test_prompt_assist.py -q`，结果 **47 passed, 32 skipped**。覆盖文案／图片／视频、合格结果仅调用一次、质量重试、持续待填拒绝、重试共享总超时、必要字段提示、幂等重放及原有配置／错误处理。32 项数据库集成测试因未配置隔离测试数据库跳过，不能据此声称数据库集成通过。
4. 最终全量后端命令：`python -X utf8 -m pytest -q --tb=line`，结果 **473 passed, 471 skipped, 3 failed**。三项失败均位于未改动的任务测试样本，缺少任务投影现已要求的时间字段，与本次辅助逻辑无调用依赖，未扩展本次修复范围：
   - `tests/unit/test_display_numbers.py::test_task_projection_preserves_number_across_state_changes_and_replay`：样本无 `created_at`。
   - `tests/unit/test_display_numbers.py::test_task_detail_contains_persisted_owned_conversation_number`：任务样本无 `created_at`／`updated_at`。
   - `tests/unit/test_generation_parameters.py::test_original_admitted_intent_replays_without_using_new_prices`：任务样本无 `created_at`／`updated_at`。
5. 涉及的四个 Python 文件 `ruff check` 通过，已跟踪修改的 `git diff --check` 通过。独立只读复核确认上述评审发现已修复，无本次范围的阻断项。

未调用管理员配置的真实模型，未进行运行站点联调、服务重启或生产发布。本记录证明代码及模拟模型响应的处理行为，不替代真实模型效果验收。
