# 前端公共控件

2026-10-16：用户确认将基础控件统一为 Element Plus，保留 V2 奶油米色与陶土橙、现有页面布局及业务流程。

## 复用入口

| 场景 | 实现 |
| --- | --- |
| 文本、密码、数字、日期、多行输入 | `frontend/src/components/ui/UiInput.vue` |
| 可选择建议、也可直接填写的文本 | `UiInput` 的 `suggestions`，内部使用 `ElAutocomplete` |
| 固定枚举、动态选项 | `frontend/src/components/ui/UiSelect.vue`，内部使用 `ElSelect` / `ElOption` |
| 操作按钮 | `frontend/src/components/ui/UiButton.vue`，内部使用 `ElButton` |
| 编辑与只读抽屉 | `AppDrawer.vue` → `AppOverlay.vue` → `ElDrawer` |
| 预览、费用与删除确认 | `AppDialog.vue` → `AppOverlay.vue` → `ElDialog` |
| 表格 | `ElTable` / `ElTableColumn`；业务列使用与接口对应的行类型 |
| 分页 | `UiPagination.vue` → `ElPagination`；统一总数、上一页、数字页码、下一页、跳页，保留各列表原每页条数 |
| 单选、多选 | `ElRadio` / `ElCheckbox` |

颜色、圆角、字体等以 `frontend/src/styles/tokens.css` 为产品来源，由 `element-theme.css` 映射到 Element Plus。`element-components.ts` 按需引入组件及其依赖样式；代码从 `element-plus/es/components/.../index` 引入实际使用的组件。应用入口通过 `ElConfigProvider` 使用中文语言包。

不新增第二套输入、选择、按钮或弹层实现。商品卡片、任务卡片、成果预览与首页宣传构图继续使用现有业务组件。原生文件输入保留现有上传契约，由公共按钮触发。

## 使用约定

```vue
<label for="product-name">商品名称</label>
<UiInput id="product-name" v-model="name" required />

<label for="copy-tone">语气</label>
<UiInput id="copy-tone" v-model="tone" :suggestions="['自然', '专业']" />

<label for="config-state">配置状态</label>
<UiSelect id="config-state" v-model="enabled" required>
  <option value="" disabled>请选择状态</option>
  <option :value="true">启用</option>
  <option :value="false">停用</option>
</UiSelect>

<UiButton type="submit" form="product-form" class="button primary">保存</UiButton>
<UiButton type="button" class="button">取消</UiButton>
```

- `UiButton.type` 沿用 HTML 的 `button` / `submit` / `reset`，默认 `submit` 兼容既有表单。取消、关闭、切换等非提交动作显式写 `type="button"`。弹层内提交按钮显式关联 `form`，因为弹层传送到 body。
- `UiInput` 保留 `v-model.number`、空值、原生必填及范围校验，以及现有处理器需要的 DOM `input` / `change` 事件。校验错误仍归具体业务字段管理，不额外创建第二套表单状态。
- `UiSelect` 接收原有 `option` 插槽，将文字和真实值交给 Element Plus；布尔值不转换成字符串。隐藏的原生 select 仅负责表单归属与约束校验，不承担可见交互，不进入 Tab 顺序或辅助技术树。
- 禁用继承祖先 `fieldset`，提交期间不能通过可见选择器或事件桥接继续写入。工作台媒体单选同时显式接收冻结状态。
- 字段标签、`aria-describedby`、`aria-invalid`、禁用、必填及无默认值语义必须继续保留。不要把可自定义文本改成固定枚举，也不要给未填写字段添加默认业务值。
- 公共弹层保留固定标题/操作区、内容区滚动、焦点隔离和关闭后焦点恢复；弹窗与右侧抽屉均禁止 Escape 关闭，通过关闭、取消或业务操作退出。抽屉内下拉选项仍可用 Escape 收起，但不能连带关闭抽屉。收费/删除确认默认聚焦取消，编辑优先聚焦 `data-initial-focus` 字段，手机抽屉占满视口。右侧抽屉规则由用户于 2026-10-18 明确要求。
- 桌面工作台继续沿用已确认的紧凑按钮尺寸，手机和触屏操作范围至少 44px。全局原生控件样式排除 Element Plus 内部元素，局部页面不重写库内部结构。

## 验证入口

- `frontend/tests/unit/ui-controls.spec.ts`：数值、布尔值、空值、必填约束、fieldset 冻结、表单关联及焦点暴露。
- `frontend/playwright.ui.config.ts`：桌面/手机工作台、后台、媒体流程与基础控件真实浏览器回归，使用 TEST_ONLY 合成接口数据。
- 浏览器选择器通过 `tests/e2e/ui-controls.ts` 点击可见选项；原生 `selectOption()` 不能用于 Element Plus 的可见 combobox。
- 组件单测隔离业务弹层容器；公共弹层专门测试与浏览器回归使用实际 Element Plus 门户及焦点管理。

## 分页（2026-10-21）

所有列表分页使用 `UiPagination`，传入 `page`、服务端 `total`、`pageSize`（默认 20）、`disabled`（请求期间）和可访问 `label`，监听 `change` 请求目标页。成功收到结果后再提交页码与总数；请求失败保留原列表、页码与已应用筛选。不要添加页面私有分页按钮或重写内部样式；响应式规则由组件统一处理。作品每页条数沿用作品页当前设置，其他列表 20 条。

管理后台相关列表及账户流水支持 `page` 参数；不可与 `cursor` 混用。响应 `NumberedPage` 提供 `total`、`page`、`page_size`，并兼容 `next_cursor`；游标请求的 `page` 为 null。总数来自与列表相同的权限及筛选条件。旧游标调用与仅“加载更多”的任务侧栏继续使用原约定。
