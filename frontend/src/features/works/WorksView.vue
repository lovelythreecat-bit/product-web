<script setup lang="ts">
import { onScopeDispose, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { Schema } from '../../types/api'
import { listWorks, getWork, deleteWork } from '../../api/works'
import { createConversation, getProductVersion } from '../../api/conversations'
import { ApiError } from '../../api/client'
import { session } from '../auth/session'
import { setSourceDraft } from '../workspace/drafts'
import ResultViewer from '../../components/ResultViewer.vue'
import AppDrawer from '../../components/AppDrawer.vue'
import AppDialog from '../../components/AppDialog.vue'
const router = useRouter()
const kind = ref<'' | 'copy' | 'image' | 'video'>(''), items = ref<Schema<'WorkView'>[]>([]), cursor = ref<string>()
const loading = ref(false), error = ref(''), selected = ref<Schema<'WorkDetail'> | null>(null), detailsOpen = ref(false), deleteOpen = ref(false), deleting = ref(false)
let alive = true, revision = 0
const epoch = session.epoch.value
const current = (stamp: number) => alive && stamp === revision && epoch === session.epoch.value
onScopeDispose(() => { alive = false; revision++ })
async function load(more = false) {
  const stamp = ++revision; loading.value = true; error.value = ''
  try { const page = await listWorks({ kind: kind.value || undefined, cursor: more ? cursor.value : undefined }); if (current(stamp)) { items.value = more ? [...items.value, ...page.items.filter(x => !items.value.some(y => x.work_id === y.work_id))] : page.items; cursor.value = page.next_cursor ?? undefined } }
  catch (e) { if (current(stamp)) error.value = e instanceof ApiError ? e.message : '作品暂时无法读取。' }
  finally { if (current(stamp)) loading.value = false }
}
watch(kind, () => { items.value = []; cursor.value = undefined; void load() }, { immediate: true })
async function inspect(id: string) { const stamp = revision; try { const work = await getWork(id); if (current(stamp)) { selected.value = work; detailsOpen.value = true } } catch (e) { if (current(stamp)) error.value = e instanceof ApiError ? e.message : '作品详情无法读取。' } }
async function regenerate(id: string) {
  const stamp = revision
  try { const work = await getWork(id), product = await getProductVersion(work.source.input.product_version); if (!current(stamp)) return; const conversation = await createConversation({ title: '重新创作 · ' + String(product.product.name || '商品') }); if (!current(stamp)) return; setSourceDraft(conversation.conversation_id, work, product); await router.push('/workspace/' + conversation.conversation_id) }
  catch (e) { if (current(stamp)) error.value = e instanceof ApiError ? e.message : '来源资料暂时无法读取。' }
}
async function remove() {
  const version = selected.value?.source.policy_versions['D-09']
  if (!selected.value || !version || deleting.value) return
  deleting.value = true
  try { await deleteWork(selected.value.work_id, { policy_version: version }); if (!alive || epoch !== session.epoch.value) return; deleteOpen.value = false; detailsOpen.value = false; selected.value = null; await load() }
  catch (e) { if (alive && epoch === session.epoch.value) error.value = e instanceof ApiError ? e.message : '删除尚未完成，请核对后重试。' }
  finally { deleting.value = false }
}
</script>
<template><header class="page-heading"><h1>我的作品</h1><p>已保存的完整成果，随时回看与继续创作。</p></header><div class="works-toolbar"><label for="work-filter">作品类型</label><select id="work-filter" v-model="kind"><option value="">全部作品</option><option value="copy">文案</option><option value="image">图片</option><option value="video">视频</option></select><button class="button" type="button" :disabled="loading" @click="load()">刷新作品</button></div><p v-if="error" class="field-error" role="alert">{{ error }}</p><div v-if="!items.length && !loading" class="panel empty-state"><h2>完整作品将在这里保存</h2><p>任务完整成功后，可在这里预览、下载并再次创作。</p><RouterLink class="button primary" to="/workspace">开始创作</RouterLink></div><div class="works-grid"><article v-for="work in items" :key="work.work_id" class="panel work-card" :data-work-id="work.work_id"><h2>{{ work.kind === 'copy' ? '文案作品' : work.kind === 'image' ? '图片作品' : '视频作品' }}</h2><small>{{ work.created_at.slice(0, 16).replace('T', ' ') }}</small><ResultViewer :work="work" /><div class="action-row"><button class="button" type="button" @click="regenerate(work.work_id)">重新生成</button><button class="button" type="button" @click="inspect(work.work_id)">作品详情</button></div></article></div><button v-if="cursor" class="button" type="button" :disabled="loading" @click="load(true)">加载更多作品</button><p v-if="loading" role="status">正在读取作品…</p><AppDrawer v-model:open="detailsOpen" title="作品详情"><template v-if="selected"><dl class="detail-list"><dt>作品编号</dt><dd>{{ selected.work_id }}</dd><dt>来源任务</dt><dd>{{ selected.task_id }}</dd><dt>来源会话</dt><dd><RouterLink :to="'/workspace/' + selected.conversation_id">{{ selected.conversation_id }}</RouterLink></dd><dt>原输入快照</dt><dd><pre>{{ JSON.stringify(selected.source.input, null, 2) }}</pre></dd><dt>原报价</dt><dd><pre>{{ JSON.stringify(selected.source.task.quote, null, 2) }}</pre></dd><dt>冻结记录</dt><dd>{{ selected.source.credit_reservation_id }}</dd><dt>积分流水</dt><dd v-for="id in selected.source.ledger_ids" :key="id">{{ id }}</dd><dt>来源素材</dt><dd><pre>{{ JSON.stringify(selected.source.materials, null, 2) }}</pre></dd></dl><button class="button danger" type="button" :disabled="!selected.source.policy_versions['D-09']" @click="deleteOpen = true">删除作品</button><p v-if="!selected.source.policy_versions['D-09']">缺少适用删除政策，当前无法删除。</p></template></AppDrawer><AppDialog v-model:open="deleteOpen" title="删除作品" purpose="delete"><p>删除后此作品与原下载链接将不可访问；来源任务与积分记录继续保留。</p><p>{{ selected?.work_id }}</p><p v-if="error" class="field-error" role="alert">{{ error }}</p><template #actions><button class="button danger" type="button" :disabled="deleting || !selected?.source.policy_versions['D-09']" @click="remove">确认删除作品</button></template></AppDialog></template>
