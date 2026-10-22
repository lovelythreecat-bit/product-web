# 图片素材分析重复编号合并（2026-10-20）

## 本次要求与范围

按用户确认的方案：重复编号下的兼容内容合并保留，不因为简单重复让整次素材分析失败。修改在同级 `imageAgent` 项目，Web 界面、收费和任务重提行为未改动。

涉及文件：

- `imageAgent/src/image_agent/analysis_merge.py`：素材分析专用的归一化。
- `imageAgent/src/image_agent/models.py`：在原有可选事实清理之前调用合并；证据允许同一素材有多条观察。
- `imageAgent/tests/test_analysis_duplicate_merge.py`：24 项新增回归。

## 行为

- 重复的主体、素材和元素引用按原顺序去重。
- 同一编号的兼容素材摘要、事实描述、元素描述、约束指令和问题消息合并，关联视图、事实、证据及选项取并集。原输入不原地修改，保存后重新读取结果保持稳定。
- 同一张素材的不同观察及其 `source_type` 都保留，避免把同图多条证据误判为实体编号冲突。完全相同的证据不重复保存。
- 同一元素同时列为必需和偏好时保留必需；同时选中和排除仍判为冲突。
- 不覆盖互相冲突的原素材 SHA-256、主体归属、来源语义、元素类别、商品匹配结果；返回具体冲突字段，沿用现有模型修正流程。这里的合并不推断两种互斥身份其实是同一件商品。
- 重复事实的置信度取较低值，不通过合并提高置信度；缺省外观属性不会被另一条功能宣称覆盖。
- 请求素材 ID、图片审核计数等其他契约继续使用原有严格校验。

## 失败事实

只读核对本机数据库：任务 `T20261020-000009`（详情图）与 `T20261020-000011`（主图）在 `analyze_materials / MaterialAnalysis` 失败，错误为 `duplicate IDs`，各有 `vision_calls=4 / image_calls=0`。这两条旧任务没有保存失败的原始模型响应，不能声称已经按原响应复放验证。同期长图 `T20261020-000010` 在本轮操作前已成功完成。

## 验证

- 修改前：新增同步用例 **17 failed / 1 passed**，复现重复引用直接失败、重复事实只保留首条、同图多证据失败等行为。
- 最终实际目录新增回归：**24 passed / 3.16s**。包括真实 `VisionClient` 解析、状态赋值、主图和详情图完整管线；只有外部模型及出图边界受控。验证两段描述同时进入生成提示并保存到真实运行目录的 `result.json`。
- 安装至实际图片 Agent 后：新增回归、原 `test_models.py`、`test_direct_delivery.py` 合计 **59 passed / 8.98s**，包含长图直接交付、恢复和 HTTP 任务发布。
- 扩展素材分析/选择/视觉/补全回归：**176 passed / 6 failed**。六项在修改前源码上同样失败（另 2 项参数用例通过），未将其记作本次修复通过：
  - `test_vision_resilience.py::test_discovery_root_validation_feedback_names_the_broken_reference`
  - `test_vision_resilience.py::test_fresh_discovery_corrects_missing_semantic_provenance[verifiability]`
  - `test_vision_resilience.py::test_fresh_discovery_corrects_missing_semantic_provenance[source_type]`
  - `test_vision_resilience.py::test_fresh_discovery_corrects_missing_semantic_provenance[unknown]`
  - `test_vision_completion.py::test_fresh_identity_blocker_is_not_forced_ready_to_fill_missing_plan[missing_evidence]`
  - `test_vision_completion.py::test_fresh_unknown_provenance_still_exhausts_without_becoming_valid`
- 改动文件 Ruff 检查通过。

扩展全量已启动但中止，不能视为全量通过。进度中完整报告 432 项，14 项失败；其余尾部进度没有完整总结。原始命令工作目录为 Web，并且后续修改前副本的桌面测试受 Tk 安装缺文件影响，因此不能仅凭这次全量进度判断桌面失败的产品原因。按测试收集顺序关联的失败项保存在 `.tmp/image-id-merge-20261020/partial-failures.json`：

- `test_desktop.py::test_request_maps_materials_and_rejects_invalid_combinations`
- `test_desktop.py::test_credentials_are_per_service_without_mutating_config_or_environment`
- `test_desktop_product_long_image.py::test_create_passes_analysis_selection_for_mixed_long`
- `test_desktop_ui.py::test_failed_analysis_explains_reason_instead_of_only_failed_status`
- `test_desktop_ui.py::test_analyze_runs_in_worker_and_displays_result`
- `test_desktop_ui.py::test_white_background_selects_required_platform_and_analyzes[False]`
- `test_desktop_ui.py::test_white_background_selects_required_platform_and_analyzes[True]`
- `test_desktop_ui.py::test_worker_error_masks_session_key_and_preserves_form`
- `test_desktop_ui.py::test_cancel_keeps_ui_responsive_until_cleanup`
- `test_desktop_ui.py::test_clarification_resumes_with_selected_snapshot`
- `test_desktop_ui.py::test_desktop_generates_and_saves_through_real_pipeline`
- `test_desktop_ui.py::test_resume_uses_current_config_without_requiring_current_materials`
- `test_desktop_ui.py::test_start_new_task_drops_previous_candidate_binding`
- `test_long_image_completion.py::test_legacy_evidence_completion_preserves_real_source_failure[missing_evidence-needs_input-1]`

针对上述 14 项的修改前副本复跑为 4 failed / 10 setup errors，后者均为 `tkinter.TclError`（运行时缺 `tk8.6/listbox.tcl`），不能将这 10 项声称为相同产品失败已复现。完整记录保存在 `.tmp/image-id-merge-20261020/baseline-partial.log`。桌面和现有可选事实规则没有扩大修复范围。

## 本机生效

源文件安装前核对 `models.py` 与本轮原始副本的 SHA-256 一致，避免覆盖并行改动；本轮实际差异仅为合并入口、重复证据引用处理和移除未使用 import。原文件备份在 `.tmp/image-id-merge-20261020/installed-backups/`。

本机时间 16:07:55（UTC+8）确认图片队列无 queued/running 任务后，仅重载本项目图片 API；`/health/ready` 检查通过。源文件摘要与健康证据保存在 `.tmp/image-id-merge-20261020/runtime-health.json`。没有自动重提旧任务，也没有新增真实付费生成。本轮受控回归不能代表真实模型整体成功率已获得保证。
