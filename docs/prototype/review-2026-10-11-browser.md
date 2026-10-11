# Assessment B — 独立检测器与浏览器证据评审

日期：2026-10-11；对象：`F:/Work/电商/web/docs/prototype/index.html`；本地URL：`http://127.0.0.1:8777/`。

本评审与 Assessment A 隔离，未读取其他评审结果。先读 AGENTS.md、docs/product-design.md、原型说明及 impeccable critique 的 Assessment B 规则，并参考需求终稿的手机基本响应式、费用与异常约束。仅创建本报告、结构化证据和截图，没有修改原型源码。作者 interaction-check.js 已阅读用于理解既有覆盖，未执行，既有38项通过结果不作为本次独立证据。

## 已证实的问题

### B-1 [P1] 手机任务区被挤成零宽度，未按单列呈现

**复现**：390×844，打开 `#workspace`，使用默认青瓷马克杯数据，无需任何边界输入。任务标题与说明在表单左边变成竖排细条，任务卡内容、详情按钮和演示控制与创作表单挤在同一网格行。

**证据**：真实 Chromium/IAB DOM几何：`.workspace` 宽347px；`.feed` 的 x=14、width=0；`.composer` 的 x=32、width=329，两者 top 同为247.58（截图时因页面自动滚动，截图显示位置相应变化）。此时页面scrollWidth为375，小于视口390；所以“无整页横向溢出”不能证明响应式可用。截图：[手机默认工作台](screenshots/review-b-mobile-workspace.png)。

**原因与位置**：`style.css:89` 固定 `.workspace>.composer{grid-column:2;grid-row:1}`，`style.css:90` 固定 `.workspace>.feed{grid-column:1;grid-row:1}`，位于原有850px手机媒体规则之后。手机虽将grid-template-columns设为1fr，但子项仍占第2列、强制同一行，浏览器产生隐式列并压缩任务区。

**修复方向**：850px及以下明确把两子项都放第1列，composer第1行、feed第2行；使用实际两区宽度、上下位置与任务按钮可用性验证，而不只检查scrollWidth。

### B-2 [P2] 合法长商品名称使整页横向溢出

**复现**：工作台 → 编辑资料 → 商品名称填入120个连续`A`（正好是字段maxlength）→ 保存。

**证据**：1440px桌面scrollWidth=2566；390px手机scrollWidth=1587。文字从“商品资料”摘要越出面板，底部出现全页水平滚动。截图：[桌面长名称](screenshots/review-b-desktop-long-name.png)、[手机长名称](screenshots/review-b-mobile-long-name.png)。

**原因与位置**：`app.js:99`将合法名称放入`.summary-title`；`style.css:93`只设置字号/粗细，无长词换行。邻近`.summary-copy`已有overflow-wrap:anywhere，商品名称没有。

**修复方向**：为产品名称摘要补充长词换行并保证容器min-width；同时验证SKU、文件名、个人昵称等合法连续字符串，不通过缩小允许输入来掩盖布局问题。

### B-3 [P2] 辅助展开、后台模块切换后丢失键盘焦点

**复现与证据**：在“AI 帮我完善”按钮按Enter，建议正常出现，但document.activeElement为BODY；接着Tab跳到“可用112 · 充值积分”，需要重新经过会话和表单才能到建议。后台“用户管理”按钮按Enter后，activeElement同样为BODY；下一次Tab回到“任务与异常”，而非当前模块或其内容。

**原因与位置**：`app.js:212`的辅助分支调用render()后没有恢复/移动焦点；`app.js:202`的后台模块分支同样如此。render在`app.js:150`整体替换app.innerHTML，移除了触发按钮。Agent切换（201行）与筛选（203行）已有显式恢复focus，故这是局部不一致。

**修复方向**：辅助展开后聚焦建议编辑框或保留辅助按钮焦点；模块切换后聚焦当前模块按钮或模块标题。为会话选择（199行、157行）采用相同策略，并以键盘Enter/Tab而非只调用click验证。

### B-4 [P2，次要文案] 失败重试仍承诺“保留原成果、再次收费”

**复现**：提交文案新任务T-1044 → 演示待核查 → 保存失败待恢复 → 确定失败/释放 → “修改后重新提交” → 确认费用。此时旧任务实际“失败 · 已释放”，无正式成果，但编辑器提示“原成果保留”，确认框标题“重新生成 · 再次收费”，正文“保留原成果，创建新任务并再次收费”。

**证据**：余额在首次提交后112/0/88变104/8/88，pending/saving均保持，确定失败后恢复112/0/88；旧任务没有消费且没有成果。重试取消后任务仍为4个，账本行为正确，误导来自界面文案。

**位置**：`app.js:193` regenerate统一restoreInput；`app.js:224`将edit-task与task-regenerate共用；`app.js:97`来源提示和`app.js:167`确认文案仅判断sourceTaskId，未区分失败任务与成功作品。

**修复方向**：失败重试显示“沿用原输入，按当前报价创建新任务”；有正式成果的成功重生成才显示“原成果保留、再次收费”。

## 有界检查与正向证据

- 桌面1440×1000、手机390×844，各检查home/login/register/workspace/works/account/recharge/admin；各检查8个后台模块，共32个页面/模块观测。默认数据无整页横向溢出；已明确发现手机任务区零宽，故这项不等于页面可用通过。
- 上述默认页面/模块可见输入均有label或aria-label，页面未发现重复ID。商品编辑抽屉14字段均有可访问标签；手机固定footer实测top=767、bottom=844，位于844px视口内。
- 收费确认初始焦点在取消；Escape关闭后焦点回到生成按钮。商品保存/取消后的焦点恢复正常。只读任务详情与预览使用统一dialog；任务快照可展开，输入中的`<script>`保持字面文本，没有成为脚本节点。
- 会话C-1→C-2→C-1保留指令；Agent切换恢复触发按钮焦点。旧报价提示明确未受理，接受demo-p2后仍需第二次收费确认。
- 新任务112/0/88→104/8/88；待核查、保存失败均保留冻结且不显示直接重新生成；确定失败释放到112/0/88。失败任务详情保留p2快照及异常时间线。仅验证演示内部语义，不作为后端账本、幂等或恢复证明。
- 后台发放原因只有空格时保留抽屉与输入，显示“请填写发放原因。”；修正后出现独立后台流水180→230、原因“独立边界回归”，抽屉关闭并恢复发放按钮焦点。无真实账户被修改。
- 最终浏览器error/warn日志读取返回[]。未进行完整读屏、跨浏览器、真实上传、真实后台权限、服务端或性能验收。

结构化观测：[review-2026-10-11-browser-evidence.json](review-2026-10-11-browser-evidence.json)。

## CLI与浏览器运行记录

- **真实命令**：`C:/Users/呜啦啦/.codex/skills/impeccable/scripts/impeccable.cmd detect --json docs/prototype`。
- **实际结果**：退出码0；stdout为`[]`；stderr无输出；耗时约0.58秒。计数0；rule names为空；file locations为空。无挂起、无需要清理的CLI进程。空扫描结果不能覆盖运行时响应式和边界交互，本评审不把它解释为无缺陷。
- **Chrome首选尝试**：使用new_page打开上述URL，指定新的隔离上下文assessment-b-20261011和15000ms超时。工具返回isError和“automatic permission approval review did not finish before its deadline”，没有获得pageId。不因超时认定动作不安全，没有无限重试。
- **后续浏览器**：用cua.createBrowserTab新建Codex IAB标签页1；没有复用任何用户标签。页面可读、可点击、可截屏，浏览器visibility.get()实测false，保持后台。
- **覆盖层注入预检**：实际在cua read-only evaluate尝试设置document.title和追加script，返回`TypeError: Cannot set property title of [object Object] which has only a getter`；在设置title处失败，script未追加。没有检测器进入页面、没有用户可见[Human]覆盖层、没有浏览器端impeccable检测计数。回退证据为CLI、真实DOM观测、键盘操作及截图。
- **辅助服务**：复用父任务已有8777服务；本评审没有启动HTTP服务或impeccable live-server，没有终止父任务服务。注入能力不可用，故按规则跳过live-server。
- **清理**：已reset临时viewport并关闭独立IAB标签。三张截图、结构化证据及本报告作为交付保留；无临时脚本文件，无新后台服务。Chrome失败没有返回可清理标签ID，不作假定。
- **上下文与独立性**：父任务运行impeccable context，本评审未重复；父任务告知ignore.md不存在，本评审未读任何历史评审。A尚未完成前只通知本报告已落盘，不向父任务发送具体detector findings。

