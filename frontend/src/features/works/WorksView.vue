<script setup lang="ts">
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import UiPagination from '../../components/ui/UiPagination.vue'
import { onScopeDispose, ref, watch } from 'vue'
import type { Schema } from '../../types/api'
import { listWorks, getWork, deleteWork } from '../../api/works'
import { ApiError } from '../../api/client'
import { session } from '../auth/session'
import ResultViewer from '../../components/ResultViewer.vue'
import TextWarnings from '../../components/TextWarnings.vue'
import AppDrawer from '../../components/AppDrawer.vue'
import AppDialog from '../../components/AppDialog.vue'
import AppIcon from '../../components/AppIcon.vue'
const kind = ref<'' | 'copy' | 'image' | 'video'>(''), items = ref<Schema<'WorkView'>[]>([])
const query = ref(''), appliedQuery = ref(''), page = ref(1), total = ref(0), pageSize = 10
const loading = ref(false), error = ref(''), selected = ref<Schema<'WorkDetail'> | null>(null), detailsOpen = ref(false), deleteOpen = ref(false), deleting = ref(false)
const scrollRoot = ref<HTMLElement>()
let alive = true, revision = 0, requestedPage = 1
const epoch = session.epoch.value
const current = (stamp: number) => alive && stamp === revision && epoch === session.epoch.value
onScopeDispose(() => { alive = false; revision++ })
async function load(targetPage = page.value) {
  const stamp = ++revision
  requestedPage = targetPage
  loading.value = true; error.value = ''
  try {
    const result = await listWorks({ kind: kind.value || undefined, q: appliedQuery.value || undefined, page: targetPage, limit: pageSize })
    if (current(stamp)) {
      items.value = result.items
      total.value = result.total ?? result.items.length
      page.value = result.page ?? targetPage
      scrollRoot.value?.scrollTo?.({ top: 0 })
    }
  } catch (e) { if (current(stamp)) error.value = e instanceof ApiError ? e.message : '作品暂时无法读取。' }
  finally { if (current(stamp)) loading.value = false }
}
function search() { appliedQuery.value = query.value.trim(); void load(1) }
function resetSearch() { query.value = ''; appliedQuery.value = ''; void load(1) }
watch(kind, () => { void load(1) }, { immediate: true })
async function inspect(id: string) { const stamp = revision; try { const work = await getWork(id); if (current(stamp)) { selected.value = work; detailsOpen.value = true } } catch (e) { if (current(stamp)) error.value = e instanceof ApiError ? e.message : '作品详情无法读取。' } }
async function confirmDelete(id: string) { const stamp = revision; try { const work = await getWork(id); if (current(stamp)) { selected.value = work; deleteOpen.value = true } } catch { if (current(stamp)) error.value = '作品信息暂时无法读取，请重试。' } }
const labels: Record<string, string> = { name: '商品名称', category: '商品类目', selling_points: '商品卖点', sellingPoints: '商品卖点', description: '商品介绍', brand: '品牌', audience: '目标人群', targetAudience: '目标人群', size: '尺寸', color: '颜色', material: '材质', ratio: '画面比例', aspect_ratio: '画面比例', aspectRatio: '画面比例', resolution: '分辨率', duration: '视频时长', count: '数量', style: '风格', tone: '语气', length: '文案长度', purpose: '用途', audio: '声音', subtitles: '字幕' }
function displayRows(value: Record<string, unknown>) { return Object.entries(value).map(([key, item], index) => ({ label: labels[key] || `其他资料 ${index + 1}`, value: typeof item === 'boolean' ? item ? '是' : '否' : typeof item === 'string' || typeof item === 'number' ? String(item) : Array.isArray(item) && item.every(v => typeof v === 'string' || typeof v === 'number') ? item.join('、') : '已保留在原始任务记录中' })) }
const states: Record<string,string> = { SUBMITTED:'已提交', QUEUED:'排队中', SUBMITTING:'正在受理', RUNNING:'生成中', INVESTIGATING:'待核查', SAVING:'正在保存', SAVE_RECOVERY:'保存失败，待恢复', SUCCEEDED:'成功', FAILED:'生成失败', MANUALLY_CLOSED:'已人工关闭' }
const settlements: Record<string,string> = { FROZEN:'已冻结', CONSUMED:'已消费', RELEASED:'已释放' }
async function remove() {
  const version = selected.value?.source.policy_versions['D-09']
  if (!selected.value || !version || deleting.value) return
  deleting.value = true
  try { await deleteWork(selected.value.work_id, { policy_version: version }); if (!alive || epoch !== session.epoch.value) return; deleteOpen.value = false; detailsOpen.value = false; selected.value = null; await load() }
  catch (e) { if (alive && epoch === session.epoch.value) error.value = e instanceof ApiError ? e.message : '删除尚未完成，请核对后重试。' }
  finally { deleting.value = false }
}
</script>
<template>
  <section class="works-page" aria-label="我的作品">
  <div class="works-toolbar"><UiButton class="button works-refresh" type="button" :disabled="loading" @click="load()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1"/></svg>刷新作品</UiButton><div class="work-filters" role="group" aria-label="作品类型筛选"><UiButton v-for="option in ([['', '全部'], ['copy', '文案'], ['image', '图片'], ['video', '视频']] as const)" :key="option[0]" type="button" class="button" :aria-pressed="kind === option[0]" @click="kind = option[0]">{{ option[1] }}</UiButton></div></div>
  <form class="works-search" role="search" aria-label="查询作品" @submit.prevent="search"><label for="works-query">商品名称</label><UiInput id="works-query" v-model="query" placeholder="输入商品名称查询作品" :maxlength="120" /><UiButton class="button primary" type="submit" :disabled="loading">查询</UiButton><UiButton class="button" type="button" :disabled="loading" @click="resetSearch">重置</UiButton></form>
  <div ref="scrollRoot" class="works-scroll" role="region" aria-label="作品列表" tabindex="0" :aria-busy="loading">
  <div v-if="error" class="works-error"><p class="field-error" role="alert">{{ error }}</p><UiButton class="button" type="button" :disabled="loading" @click="load(requestedPage)">重试加载</UiButton></div>
  <div v-if="!items.length && !loading && !error" class="empty-state"><AppIcon name="works" /><h2>{{ appliedQuery ? '未找到匹配作品' : '暂无该类作品' }}</h2><p>{{ appliedQuery ? '请调整商品名称或作品类型后查询。' : '完整成果保存后会出现在这里。' }}</p></div>
  <div class="works-grid"><article v-for="work in items" :key="work.work_id" class="panel work-card" :class="{ 'copy-work-card': work.kind === 'copy' }" :data-work-id="work.work_id">
    <span class="status-label">{{ work.kind === 'copy' ? '文案' : work.kind === 'image' ? '图片' : '视频' }}</span>
    <ResultViewer :work="work" compact gallery-layout hide-copy-file-actions><template #actions><UiButton class="button" type="button" @click="inspect(work.work_id)">任务详情</UiButton><UiButton class="button danger" type="button" @click="confirmDelete(work.work_id)">删除作品</UiButton></template></ResultViewer>
    <h2>{{ work.name || (work.kind === 'copy' ? '文案作品' : work.kind === 'image' ? '图片作品' : '视频作品') }}</h2>
    <div class="work-origin"><RouterLink :to="'/workspace/' + encodeURIComponent(work.conversation_id) + '?task=' + encodeURIComponent(work.task_id)">{{ work.conversation_title ? '来源任务：' + work.conversation_title : '查看来源任务' }}</RouterLink><small>{{ new Date(work.created_at).toLocaleString('zh-CN') }}</small></div>
  </article></div>
  <p v-if="loading" class="works-loading" role="status">正在读取作品…</p>
  </div>
  <UiPagination :page="page" :page-size="pageSize" :total="total" :disabled="loading" label="作品分页" @change="load" />
  <AppDrawer v-model:open="detailsOpen" title="任务详情"><template v-if="selected"><dl class="detail-list"><dt>任务编号</dt><dd>{{ selected.task_id }}</dd><dt>作品编号</dt><dd>{{ selected.work_id }}</dd><dt>创建时间</dt><dd>{{ new Date(selected.created_at).toLocaleString('zh-CN') }}</dd><dt>任务状态 / 积分结算</dt><dd>{{ states[selected.source.task.state] || '状态待确认' }} / {{ settlements[selected.source.task.settlement_state] || '结算待确认' }}</dd><dt>原报价</dt><dd>{{ selected.source.task.quote.credits }} 积分</dd><dt>来源任务</dt><dd><RouterLink :to="'/workspace/' + encodeURIComponent(selected.conversation_id) + '?task=' + encodeURIComponent(selected.task_id)">查看来源任务</RouterLink></dd></dl>
    <TextWarnings :warnings="selected.warnings || []" />
    <details class="source-snapshot"><summary>原始输入快照</summary><h3>商品资料</h3><dl class="detail-list"><template v-for="row in displayRows(selected.source.input.product)" :key="row.label"><dt>{{ row.label }}</dt><dd>{{ row.value }}</dd></template></dl><h3>创作指令</h3><p class="source-instruction">{{ selected.source.input.instruction || '未填写' }}</p><h3>生成设置</h3><dl class="detail-list"><template v-for="row in displayRows(selected.source.input.parameters)" :key="row.label"><dt>{{ row.label }}</dt><dd>{{ row.value }}</dd></template></dl><p v-if="!Object.keys(selected.source.input.parameters).length">未设置额外参数</p><h3>来源素材</h3><ul class="source-materials"><li v-for="(item, index) in selected.source.materials" :key="item.file.file_id">参考素材 {{ index + 1 }} · {{ item.available ? '可用' : '需重新上传' }}</li></ul><p v-if="!selected.source.materials.length">无来源素材</p></details>
    <details class="source-snapshot"><summary>积分关联记录</summary><dl class="detail-list"><dt>冻结记录</dt><dd>{{ selected.source.credit_reservation_id }}</dd><dt>积分流水</dt><dd v-for="id in selected.source.ledger_ids" :key="id">{{ id }}</dd></dl></details>
  </template></AppDrawer>
  <AppDialog v-model:open="deleteOpen" title="删除作品" purpose="delete"><template v-if="selected"><p>确认删除这份{{ selected.kind === 'copy' ? '文案' : selected.kind === 'image' ? '图片' : '视频' }}作品吗？</p><p v-if="selected.name">作品名称：{{ selected.name }}</p><p>作品编号：{{ selected.work_id }}</p><p>删除后此作品与原下载链接将不可访问；来源任务与积分记录继续保留。</p><p v-if="!selected.source.policy_versions['D-09']">缺少适用删除政策，当前无法删除。</p></template><p v-if="error" class="field-error" role="alert">{{ error }}</p><template #actions><UiButton class="button danger" type="button" :disabled="deleting || !selected?.source.policy_versions['D-09']" @click="remove">{{ deleting ? '正在删除…' : '确认删除' }}</UiButton></template></AppDialog>
  </section>
</template>
<style scoped>
.works-page { flex:1; min-height:0; min-width:0; display:flex; flex-direction:column; max-width:1680px; width:100%; margin:0 auto; }
.works-refresh { background:transparent; font-size:13px; }
.works-toolbar { display:flex; flex-direction:row-reverse; align-items:center; justify-content:space-between; gap:16px; flex-shrink:0; margin:0 0 16px; }
.work-filters { display:flex; gap:4px; padding:4px; border:1px solid var(--color-border); border-radius:12px; background:var(--color-panel); }
.work-filters .button { min-width:88px; background:transparent; border-color:transparent; margin:0; font-size:14px; }
.work-filters .button[aria-pressed=true] { background:var(--color-selected); color:var(--color-primary); font-weight:600; }
.works-scroll { flex:1; min-height:0; overflow-y:auto; overscroll-behavior-y:contain; padding:2px 12px 24px 2px; scrollbar-gutter:stable; }
.works-scroll:focus-visible { outline-offset:-3px; }
.works-grid { grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr)); align-items:start; gap:24px; margin:0; }
.work-card { --work-body-height:280px; display:flex; flex-direction:column; position:relative; padding:12px; background:var(--color-panel); border-radius:14px; }
.work-card h2 { order:2; min-height:26px; flex-shrink:0; margin:16px 8px 4px; font-size:17px; line-height:1.5; overflow-wrap:anywhere; }
.work-card>.status-label { align-self:flex-start; height:26px; box-sizing:border-box; margin:0 0 8px; background:var(--color-panel); border:1px solid var(--color-border); color:var(--color-text); border-radius:6px; padding:2px 8px; }
.work-card :deep(.result-viewer) { display:contents; }
.work-card :deep(.result-body) { order:1; }
.work-card :deep(.result-actions),.work-fallback-actions { order:4; min-height:44px; flex-shrink:0; flex-wrap:wrap; align-content:flex-start; margin:12px 8px 0; padding:8px 0 0; border-top:1px solid var(--color-border); gap:0 12px; }
.work-card :deep(.result-feedback) { order:5; }
.work-card :deep(.result-feedback:empty) { display:none; }
.work-card :deep(.result-actions .button),.work-fallback-actions .button { min-height:44px; padding:8px 0; border:0; background:none; font-size:13px; margin:0; color:var(--color-muted); }
.work-card :deep(.result-actions .button:hover),.work-fallback-actions .button:hover { color:var(--color-primary); }
.work-card :deep(.result-actions .button.danger),.work-fallback-actions .button.danger { color:var(--color-danger); }
.work-card :deep(.result-actions svg) { width:16px; height:16px; }
.work-origin { order:3; display:flex; flex-direction:column; align-items:flex-start; gap:0; flex-shrink:0; margin:0 8px; font-size:12px; min-width:0; }
.work-origin small { font-variant-numeric:tabular-nums; line-height:18px; }
.work-origin a { min-height:44px; max-width:100%; display:block; line-height:44px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color:var(--color-muted); text-decoration:none; }
.work-origin a:hover { color:var(--color-primary); text-decoration:underline; }
.works-error { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:12px; padding:16px; margin-bottom:24px; border:1px solid var(--color-border); border-radius:12px; background:var(--color-panel); }
.empty-state { min-height:320px; display:flex; flex-direction:column; align-items:center; justify-content:center; }
.empty-state>svg { width:40px; height:40px; color:var(--color-muted); margin-bottom:12px; }
.empty-state h2 { margin:0 0 8px; font-size:18px; }
.empty-state p { margin:0; font-size:14px; }
.works-search { display:flex; align-items:center; gap:12px; flex-shrink:0; margin-bottom:16px; }
.works-search label { white-space:nowrap; font-size:14px; }
.works-search .ui-input-field { width:min(360px,100%); }
.works-loading { text-align:center; color:var(--color-muted); }
.source-snapshot { margin-top:16px; border-top:1px solid var(--color-border); padding-top:12px; }
.source-snapshot summary { min-height:44px; padding:10px 0; cursor:pointer; font-weight:600; }
.source-instruction { white-space:pre-wrap; }
.source-materials { padding-left:24px; }
@media(max-width:700px) {
      .works-toolbar { flex-wrap:wrap; margin-bottom:16px; gap:8px; }
  .works-search { flex-wrap:wrap; gap:8px; }
  .works-search .ui-input-field { flex:1; min-width:160px; }
  .work-filters { width:100%; }
  .work-filters .button { flex:1; min-width:0; padding:8px; }
  .works-scroll { padding-right:6px; padding-bottom:16px; }
  .works-grid { grid-template-columns:minmax(0,1fr); gap:16px; }
  .work-card { --work-body-height:260px; }
  .work-card :deep(.result-actions),.work-fallback-actions { gap:0 16px; }
}
</style>
