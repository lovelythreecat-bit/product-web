<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { session } from '../auth/session'
import { listLedger } from '../../api/account'
import { getTask } from '../../api/tasks'
import AppDrawer from '../../components/AppDrawer.vue'
import type { Schema } from '../../types/api'
const entries = ref<Schema<'LedgerEntryView'>[]>([])
const cursor = ref<string | null>(null)
const loading = ref(false), error = ref(''), editOpen = ref(false), saving = ref(false), saveError = ref('')
const nickname = ref(''), bio = ref(''), nicknameError = ref(''), bioError = ref('')
const detail = ref<Schema<'LedgerEntryView'> | null>(null), detailOpen = ref(false)
const source = ref<Schema<'TaskDetail'> | null>(null), sourceError = ref(''), sourceLoading = ref(false)
let active = true
onBeforeUnmount(() => { active = false })
async function load(reset = false) {
  if (loading.value) return
  const version = session.epoch.value
  loading.value = true; error.value = ''
  try {
    const [page] = await Promise.all([listLedger(reset ? undefined : cursor.value ?? undefined), session.refreshAccount()])
    if (!active || version !== session.epoch.value) return
    entries.value = reset ? page.items : [...entries.value, ...page.items.filter(row => !entries.value.some(old => old.ledger_id === row.ledger_id))]
    cursor.value = page.next_cursor
  } catch { if (active && version === session.epoch.value) error.value = '积分记录暂时无法读取，请重试。' }
  finally { if (active) loading.value = false }
}
onMounted(() => load(true))
function edit() {
  nickname.value = session.profile.value?.nickname ?? ''
  bio.value = session.profile.value?.bio ?? ''
  saveError.value = ''; nicknameError.value = ''; bioError.value = ''; editOpen.value = true
}
async function save() {
  if (saving.value) return
  nicknameError.value = nickname.value && (!nickname.value.trim() || [...nickname.value].length > 80) ? '昵称须为 1–80 个字符，不能仅为空格。' : ''
  bioError.value = [...bio.value].length > 500 ? '个人简介最多 500 个字符。' : ''
  if (nicknameError.value || bioError.value) return
  saving.value = true; saveError.value = ''
  try {
    await session.saveProfile({ nickname: nickname.value || null, bio: bio.value || null })
    if (active) editOpen.value = false
  } catch { if (active) saveError.value = '保存未完成，输入已保留，请重试。' }
  finally { if (active) saving.value = false }
}
const kinds: Record<string, string> = { signup: '注册赠送', registration_grant: '注册赠送', register_grant: '注册赠送', grant: '积分发放', admin_grant: '管理员发放', freeze: '任务冻结', consume: '任务消费', release: '冻结退回' }
const taskStates: Record<string, string> = { SUBMITTED: '已提交', QUEUED: '排队中', SUBMITTING: '正在受理', RUNNING: '生成中', INVESTIGATING: '待核查', SAVING: '正在保存', SAVE_RECOVERY: '保存恢复中', SUCCEEDED: '生成成功', FAILED: '生成失败', MANUALLY_CLOSED: '已人工关闭' }
const settlements: Record<string, string> = { FROZEN: '积分冻结', CONSUMED: '积分已消费', RELEASED: '积分已退回' }
function showDetail(entry: Schema<'LedgerEntryView'>) { source.value = null; sourceError.value = ''; detail.value = entry; detailOpen.value = true }
async function showSource() {
  const taskId = detail.value?.task_id, version = session.epoch.value
  if (!taskId || sourceLoading.value) return
  sourceLoading.value = true; sourceError.value = ''
  try {
    const result = await getTask(taskId)
    if (active && version === session.epoch.value && detail.value?.task_id === taskId) source.value = result
  } catch { if (active && version === session.epoch.value) sourceError.value = '来源任务暂时无法读取，请重试。' }
  finally { sourceLoading.value = false }
}
</script>
<template>
  <div class="account-page">
    <section class="page-heading"><p class="eyebrow">我的账户</p><h1>个人中心</h1><p>管理个人资料，查看积分与每一笔变动。</p></section>
    <section class="panel profile-panel"><div class="section-heading"><h2>个人资料</h2><button type="button" class="button" @click="edit">编辑资料</button></div><dl class="profile-summary"><dt>账号</dt><dd>{{ session.profile.value?.account }}</dd><dt>昵称</dt><dd data-testid="profile-nickname">{{ session.profile.value?.nickname || '尚未设置' }}</dd><dt>个人简介</dt><dd data-testid="profile-bio">{{ session.profile.value?.bio || '补充一段简介，让创作更有方向。' }}</dd></dl></section>
    <section class="panel"><div class="section-heading"><h2>我的积分</h2><RouterLink class="button" data-testid="account-recharge" to="/recharge">充值积分</RouterLink></div><div v-if="session.account.value" class="balance-grid"><div><span>可用积分</span><strong data-testid="available">{{ session.account.value.available }}</strong></div><div><span>冻结积分</span><strong data-testid="frozen">{{ session.account.value.frozen }}</strong></div><div><span>已消费积分</span><strong data-testid="consumed">{{ session.account.value.consumed }}</strong></div></div><p v-if="session.account.value">累计入账 {{ session.account.value.credited_total }} 积分</p><p>冻结积分用于正在处理的任务；每笔变动可在流水中查看。</p></section>
    <section class="panel"><div class="section-heading"><h2>积分流水</h2><button type="button" class="button" :disabled="loading" @click="load(true)">刷新记录</button></div><p v-if="error" class="field-error" role="alert">{{ error }}</p><p v-if="loading" role="status">正在读取积分记录…</p><p v-if="!loading && !error && !entries.length">暂无积分流水。</p><ul class="ledger-list"><li v-for="entry in entries" :key="entry.ledger_id"><div><strong>{{ kinds[entry.kind] || entry.kind }}</strong><p>{{ entry.reason }}</p><small>{{ new Date(entry.created_at).toLocaleString('zh-CN') }}</small></div><strong class="ledger-amount">{{ entry.amount }} 积分</strong><button type="button" class="button" :aria-label="'查看流水 ' + entry.ledger_id" @click="showDetail(entry)">详情</button></li></ul><button v-if="cursor" type="button" class="button" :disabled="loading" @click="load()">加载更多流水</button></section>
  </div>
  <AppDrawer v-model:open="editOpen" title="编辑个人资料" purpose="edit"><form id="profile-form" class="form-stack" @submit.prevent="save" novalidate><div><label for="profile-nickname">昵称</label><input id="profile-nickname" v-model="nickname" data-initial-focus :disabled="saving" aria-describedby="nickname-limit nickname-error"><small id="nickname-limit">最多 80 个字符，可留空</small><p id="nickname-error" role="alert" class="field-error">{{ nicknameError }}</p></div><div><label for="profile-bio">个人简介</label><textarea id="profile-bio" v-model="bio" rows="7" :disabled="saving" aria-describedby="bio-limit bio-error" /><small id="bio-limit">最多 500 个字符</small><p id="bio-error" role="alert" class="field-error">{{ bioError }}</p></div><p v-if="saveError" role="alert" class="field-error">{{ saveError }}</p></form><template #actions><button type="submit" form="profile-form" class="button primary" :disabled="saving">{{ saving ? '正在保存…' : '保存资料' }}</button></template></AppDrawer>
  <AppDrawer v-model:open="detailOpen" title="积分流水详情"><template v-if="detail"><dl class="detail-list"><dt>流水编号</dt><dd>{{ detail.ledger_id }}</dd><dt>业务类型</dt><dd>{{ kinds[detail.kind] || detail.kind }}</dd><dt>金额</dt><dd>{{ detail.amount }} 积分</dd><dt>说明</dt><dd>{{ detail.reason }}</dd><dt>变动前（可用 / 冻结 / 已消费）</dt><dd>{{ detail.balances_before.available }} / {{ detail.balances_before.frozen }} / {{ detail.balances_before.consumed }}</dd><dt>变动后（可用 / 冻结 / 已消费）</dt><dd>{{ detail.balances_after.available }} / {{ detail.balances_after.frozen }} / {{ detail.balances_after.consumed }}</dd><dt>关联任务</dt><dd>{{ detail.task_id || '无' }}</dd><dt>发放记录</dt><dd>{{ detail.grant_id || '无' }}</dd><dt>冻结记录</dt><dd>{{ detail.reservation_id || '无' }}</dd></dl><button v-if="detail.task_id" type="button" class="button" :disabled="sourceLoading" @click="showSource">{{ sourceLoading ? '正在读取…' : '查看来源任务' }}</button><p v-if="sourceError" class="field-error" role="alert">{{ sourceError }}</p><section v-if="source" data-testid="source-task"><h3>来源任务</h3><dl class="detail-list"><dt>任务编号</dt><dd>{{ source.task.task_id }}</dd><dt>创作指令</dt><dd>{{ source.input.instruction }}</dd><dt>原始报价</dt><dd>{{ source.task.quote.credits }} 积分</dd><dt>任务状态 / 结算状态</dt><dd>{{ taskStates[source.task.state] || source.task.state }} / {{ settlements[source.task.settlement_state] || source.task.settlement_state }}</dd></dl></section></template></AppDrawer>
</template>
