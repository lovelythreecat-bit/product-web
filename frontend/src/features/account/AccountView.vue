<script setup lang="ts">
import { ElTable, ElTableColumn, type TableInstance } from 'element-plus/es/components/table/index'
import UiButton from '../../components/ui/UiButton.vue'
import UiPagination from '../../components/ui/UiPagination.vue'
import UiInput from '../../components/ui/UiInput.vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { session } from '../auth/session'
import { listLedger, type LedgerEntry, type LedgerFilters, type LedgerPage } from '../../api/account'
import { getTask } from '../../api/tasks'
import { uploadFile } from '../../api/files'
import AppDrawer from '../../components/AppDrawer.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import ChangePasswordDrawer from './ChangePasswordDrawer.vue'
import type { Schema } from '../../types/api'
const ledgerPage = ref<LedgerPage | null>(null)
const entries = computed(() => ledgerPage.value?.items ?? [])
const total = ref(0)
const ledgerTable = ref<TableInstance>()
const startDate = ref(''), endDate = ref(''), dateError = ref('')
const appliedFilters = ref<LedgerFilters>({})
const consumption = computed(() => ledgerPage.value?.consumption)
const consumptionScope = computed(() => Object.keys(appliedFilters.value).length ? '所选时间消费' : '累计分类消费')
function dateFilters(): LedgerFilters | null {
  dateError.value = ''
  for (const value of [startDate.value, endDate.value]) {
    if (!value) continue
    const parsed = new Date(value + 'T00:00:00')
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(parsed.getTime()) || parsed.getFullYear() !== Number(value.slice(0, 4)) || parsed.getMonth() + 1 !== Number(value.slice(5, 7)) || parsed.getDate() !== Number(value.slice(8, 10))) {
      dateError.value = '请选择有效日期。'; return null
    }
  }
  if (startDate.value && endDate.value && startDate.value > endDate.value) {
    dateError.value = '开始日期不能晚于结束日期。'; return null
  }
  const filters: LedgerFilters = {}
  if (startDate.value) filters.start_time = new Date(startDate.value + 'T00:00:00').toISOString()
  if (endDate.value) {
    const end = new Date(endDate.value + 'T00:00:00')
    end.setDate(end.getDate() + 1)
    filters.end_time = end.toISOString()
  }
  return filters
}
function searchLedger() {
  const filters = dateFilters()
  if (filters) void load(true, filters)
}
function clearDates() {
  if (loading.value) return
  startDate.value = ''; endDate.value = ''; dateError.value = ''; void load(true, {})
}
const profileDetailsOpen = ref(window.innerWidth > 700)
let compactProfile = window.innerWidth <= 700
function resizeProfile() {
  const compact = window.innerWidth <= 700
  if (compact !== compactProfile) { compactProfile = compact; profileDetailsOpen.value = !compact }
}
const loading = ref(false), error = ref(''), editOpen = ref(false), saving = ref(false), saveError = ref('')
const nickname = ref(''), bio = ref(''), nicknameError = ref(''), bioError = ref('')
const optionalFields = [
  { key: 'shop_name', label: '店铺名称', type: 'text', max: 80 },
  { key: 'category', label: '主营类目', type: 'text', max: 80 },
  { key: 'email', label: '联系邮箱', type: 'email', max: 120 },
  { key: 'phone', label: '联系电话', type: 'tel', max: 40 },
] as const
type OptionalKey = typeof optionalFields[number]['key']
const fields = ref<Record<OptionalKey, string>>({ shop_name: '', category: '', email: '', phone: '' })
const fieldErrors = ref<Partial<Record<OptionalKey, string>>>({})
const avatar = ref<Schema<'FileVersionRef'> | null>(null), avatarInput = ref<HTMLInputElement>()
const profileForm = ref<HTMLFormElement>()
const uploading = ref(false), avatarError = ref('')
const original = ref<Schema<'ProfileView'> | null>(null)
let editRevision = 0, editEpoch = 0
const detail = ref<LedgerEntry | null>(null), detailOpen = ref(false)
const source = ref<Schema<'TaskDetail'> | null>(null), sourceError = ref(''), sourceLoading = ref(false)
const accountOpen = ref(false), logoutError = ref('')
const passwordOpen = ref(false)
const router = useRouter()
async function logout() { logoutError.value = ''; try { if (await session.logout()) await router.replace('/login') } catch { logoutError.value = '退出未完成，请重试。' } }
let active = true
onBeforeUnmount(() => { active = false; window.removeEventListener('resize', resizeProfile) })
function resetLedgerScroll() { void nextTick(() => ledgerTable.value?.setScrollTop(0)) }
async function load(reset = false, filters = appliedFilters.value, targetPage = 1) {
  if (loading.value) return
  const version = session.epoch.value
  loading.value = true; error.value = ''
  try {
    const [page] = await Promise.all([listLedger(undefined, filters, targetPage), session.refreshAccount()])
    if (!active || version !== session.epoch.value) return
    ledgerPage.value = page
    currentPage.value = page.page ?? targetPage
    total.value = page.total
    if (reset) appliedFilters.value = { ...filters }
    resetLedgerScroll()
  } catch { if (active && version === session.epoch.value) error.value = '积分记录暂时无法读取，请重试。' }
  finally { if (active) loading.value = false }
}
const currentPage = ref(1)
function changePage(page: number) { void load(false, appliedFilters.value, page) }
onMounted(() => { void load(true); window.addEventListener('resize', resizeProfile) })
watch(editOpen, open => { if (!open) { editRevision++; uploading.value = false } })
watch(() => session.epoch.value, () => { editOpen.value = false; accountOpen.value = false; detailOpen.value = false })
function edit() {
  if (!session.profile.value) return
  original.value = { ...session.profile.value }
  editRevision++; editEpoch = session.epoch.value
  nickname.value = session.profile.value?.nickname ?? ''
  bio.value = session.profile.value?.bio ?? ''
  for (const field of optionalFields) fields.value[field.key] = original.value[field.key] ?? ''
  avatar.value = original.value.avatar ? { ...original.value.avatar } : null
  saveError.value = ''; nicknameError.value = ''; bioError.value = ''; fieldErrors.value = {}; avatarError.value = ''; uploading.value = false; editOpen.value = true
}
async function uploadAvatar(event: Event) {
  const input = event.target as HTMLInputElement, file = input.files?.[0]
  input.value = ''
  if (!file || uploading.value || saving.value) return
  avatarError.value = ''
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) { avatarError.value = '请选择 PNG、JPEG 或 WebP 图片。'; return }
  const revision = editRevision, epoch = session.epoch.value
  uploading.value = true
  try {
    const uploaded = await uploadFile(file)
    if (active && editOpen.value && revision === editRevision && epoch === session.epoch.value) avatar.value = uploaded
  } catch { if (active && editOpen.value && revision === editRevision && epoch === session.epoch.value) avatarError.value = '头像上传未完成，请重试。' }
  finally { if (revision === editRevision) uploading.value = false }
}
async function save() {
  if (saving.value || uploading.value || !original.value || editEpoch !== session.epoch.value || original.value.user_id !== session.profile.value?.user_id) return
  const nicknameChanged = nickname.value !== (original.value.nickname ?? ''), bioChanged = bio.value !== (original.value.bio ?? '')
  nicknameError.value = !nickname.value.trim() || nicknameChanged && [...nickname.value.trim()].length > 40 ? '请填写昵称，新昵称最多 40 个字符。' : ''
  bioError.value = bioChanged && [...bio.value.trim()].length > 300 ? '新的个人简介最多 300 个字符。' : ''
  fieldErrors.value = {}
  for (const field of optionalFields) if ([...fields.value[field.key].trim()].length > field.max) fieldErrors.value[field.key] = `${field.label}最多 ${field.max} 个字符。`
  const emailControl = profileForm.value?.querySelector<HTMLInputElement>('#profile-email')
  if (fields.value.email.trim() && emailControl?.validity.typeMismatch) fieldErrors.value.email = '请填写有效的联系邮箱。'
  if (nicknameError.value || bioError.value || Object.keys(fieldErrors.value).length || avatarError.value) return
  const body: Schema<'ProfileUpdate'> = {}
  if (nicknameChanged) body.nickname = nickname.value.trim()
  if (bioChanged) body.bio = bio.value.trim() || null
  for (const field of optionalFields) if (fields.value[field.key] !== (original.value[field.key] ?? '')) body[field.key] = fields.value[field.key].trim() || null
  if (avatar.value?.file_id !== original.value.avatar?.file_id || avatar.value?.version !== original.value.avatar?.version) body.avatar = avatar.value
  const revision = editRevision, epoch = session.epoch.value
  saving.value = true; saveError.value = ''
  try {
    await session.saveProfile(body)
    if (active && revision === editRevision && epoch === session.epoch.value) editOpen.value = false
  } catch { if (active && revision === editRevision && epoch === session.epoch.value) saveError.value = '保存未完成，输入已保留，请重试。' }
  finally { if (active) saving.value = false }
}
function formatTime(value: string | null | undefined) { return value ? new Date(value).toLocaleString('zh-CN') : '暂无记录' }
function profileStatus(status: string | undefined) { return status === 'active' ? '正常' : status === 'disabled' ? '已停用' : '状态待确认' }
const kinds: Record<string, string> = { signup: '注册赠送', registration_grant: '注册赠送', register_grant: '注册赠送', grant: '积分发放', admin_grant: '管理员发放', freeze: '任务冻结', consume: '任务消费', release: '冻结退回' }
const taskStates: Record<string, string> = { SUBMITTED: '已提交', QUEUED: '排队中', SUBMITTING: '正在受理', RUNNING: '生成中', INVESTIGATING: '待核查', SAVING: '正在保存', SAVE_RECOVERY: '保存恢复中', SUCCEEDED: '生成成功', FAILED: '生成失败', MANUALLY_CLOSED: '已人工关闭' }
const settlements: Record<string, string> = { FROZEN: '积分冻结', CONSUMED: '积分已消费', RELEASED: '积分已退回' }
function showDetail(entry: LedgerEntry) { source.value = null; sourceError.value = ''; detail.value = entry; detailOpen.value = true }
async function showSource(navigate = false) {
  const taskId = detail.value?.task_id, version = session.epoch.value
  if (!taskId || sourceLoading.value) return
  sourceLoading.value = true; sourceError.value = ''
  try {
    const result = await getTask(taskId)
    if (active && version === session.epoch.value && detail.value?.task_id === taskId) { source.value = result; if (navigate) await router.push('/workspace/' + result.conversation_id) }
  } catch { if (active && version === session.epoch.value) sourceError.value = '来源任务暂时无法读取，请重试。' }
  finally { sourceLoading.value = false }
}
const EntryColumn = ElTableColumn<LedgerEntry>
</script>
<template>
  <div class="account-page" aria-label="个人中心">
    <div class="account-columns">
      <section class="panel profile-panel">
        <div class="profile-heading"><UserAvatar :avatar="session.profile.value?.avatar" :name="session.profile.value?.nickname || session.profile.value?.account || '我'" :size="64" /><div><h2 data-testid="profile-nickname" :title="session.profile.value?.nickname || undefined">{{ session.profile.value?.nickname || '尚未设置昵称' }}</h2><p :title="session.profile.value?.account">{{ session.profile.value?.account }}</p><span v-if="session.profile.value" class="status-label">{{ profileStatus(session.profile.value.status) }}</span></div></div>
        <details class="profile-details" :open="profileDetailsOpen" @toggle="profileDetailsOpen = ($event.target as HTMLDetailsElement).open"><summary>个人与店铺资料</summary><dl class="profile-meta"><div v-for="field in optionalFields" :key="field.key"><dt>{{ field.key === 'shop_name' ? '店铺' : field.label }}</dt><dd>{{ session.profile.value?.[field.key] || '未填写' }}</dd></div></dl><p class="profile-bio" data-testid="profile-bio">{{ session.profile.value?.bio || '还未填写个人简介' }}</p></details>
        <div class="action-row"><UiButton type="button" class="button primary" @click="edit">编辑资料</UiButton><UiButton type="button" class="button" @click="passwordOpen = true">修改密码</UiButton><UiButton type="button" class="button" @click="accountOpen = true">账号详情</UiButton></div>
        <div class="profile-signout"><UiButton type="button" class="button" :disabled="session.busy.value" @click="logout">退出登录</UiButton><p v-if="logoutError" class="field-error" role="alert">{{ logoutError }}</p></div>
      </section>
      <section class="panel account-ledger">
        <div class="section-heading"><h2>积分账户</h2><RouterLink class="button" data-testid="account-recharge" to="/recharge">充值积分</RouterLink></div>
        <div v-if="session.account.value" class="balance-grid"><div><span>可用</span><strong data-testid="available">{{ session.account.value.available }}</strong></div><div><span>冻结</span><strong data-testid="frozen">{{ session.account.value.frozen }}</strong></div><div><span>累计消费</span><strong data-testid="consumed">{{ session.account.value.consumed }}</strong></div></div>
        <div class="section-heading ledger-heading"><h3>积分流水</h3><UiButton type="button" class="button" :disabled="loading" @click="load(true)">刷新记录</UiButton></div>
        <form class="ledger-filters" @submit.prevent="searchLedger">
          <div><label for="ledger-start-date">开始日期</label><UiInput id="ledger-start-date" v-model="startDate" type="date" :disabled="loading" :aria-invalid="!!dateError" aria-describedby="ledger-date-error" /></div>
          <div><label for="ledger-end-date">结束日期</label><UiInput id="ledger-end-date" v-model="endDate" type="date" :disabled="loading" :aria-invalid="!!dateError" aria-describedby="ledger-date-error" /></div>
          <div class="ledger-filter-actions"><UiButton type="submit" class="button primary" :disabled="loading">查询</UiButton><UiButton type="button" class="button" :disabled="loading" @click="clearDates">重置</UiButton></div>
        </form>
        <p v-if="dateError" id="ledger-date-error" class="field-error" role="alert">{{ dateError }}</p>
        <div class="consumption-summary" aria-live="polite"><span>{{ consumptionScope }}</span><span>文案 <strong>{{ consumption?.copy ?? '—' }}</strong></span><span>图片 <strong>{{ consumption?.image ?? '—' }}</strong></span><span>视频 <strong>{{ consumption?.video ?? '—' }}</strong></span><span v-if="consumption?.other">其他 <strong>{{ consumption.other }}</strong></span></div>
        <p v-if="error" class="field-error" role="alert">{{ error }}</p><p v-if="loading" class="ledger-feedback" role="status">正在读取积分记录…</p>
        <div class="ledger-table" tabindex="0" role="region" aria-label="积分流水列表" :aria-busy="loading">
          <ElTable ref="ledgerTable" :data="entries" height="100%" row-key="ledger_id" class="ui-data-table" :empty-text="loading ? '正在读取积分记录…' : '暂无积分流水。'"><EntryColumn :min-width="175"><template #header>类型 / 时间</template><template #default="{ row: entry }"><span :data-ledger-id="entry.ledger_id"><strong>{{ kinds[entry.kind] || '积分变动' }}</strong><small>{{ new Date(entry.created_at).toLocaleString('zh-CN') }}</small></span></template></EntryColumn><EntryColumn :width="84"><template #header>数量</template><template #default="{ row: entry }"><span class="ledger-amount">{{ entry.amount }}</span></template></EntryColumn><EntryColumn :min-width="155"><template #header>关联任务</template><template #default="{ row: entry }"><UiButton v-if="entry.task_id" type="button" class="ledger-source" @click="showDetail(entry); showSource(true)">{{ entry.task_name || '历史任务' }}</UiButton><span v-else>注册 / 积分发放</span></template></EntryColumn><EntryColumn :width="116"><template #header>操作</template><template #default="{ row: entry }"><UiButton type="button" class="button ledger-detail" :aria-label="'查看流水 ' + entry.ledger_id" @click="showDetail(entry)">查看详情</UiButton></template></EntryColumn></ElTable>
        </div>
        <footer class="ledger-footer"><UiPagination :page="currentPage" :total="total" :disabled="loading" label="积分流水分页" @change="changePage" />
        </footer>
      </section>
    </div>
  </div>
  <AppDrawer v-model:open="accountOpen" title="账号详情"><dl v-if="session.profile.value" class="detail-list"><dt>账号</dt><dd>{{ session.profile.value.account }}</dd><dt>角色</dt><dd>{{ session.profile.value.role === 'admin' ? '管理员' : '普通用户' }}</dd><dt>状态</dt><dd>{{ profileStatus(session.profile.value.status) }}</dd><dt>注册时间</dt><dd>{{ formatTime(session.profile.value.created_at) }}</dd><dt>最近登录</dt><dd>{{ formatTime(session.profile.value.last_login_at) }}</dd></dl></AppDrawer>
  <AppDrawer v-model:open="editOpen" title="编辑个人资料" purpose="edit">
    <form id="profile-form" ref="profileForm" class="form-stack profile-form" @submit.prevent="save" novalidate>
      <p class="profile-edit-notice">联系方式选填，不用于注册或登录验证。</p>
      <div class="avatar-edit"><UserAvatar :avatar="avatar" :name="nickname || session.profile.value?.account || '我'" :size="88" /><UiButton class="button" type="button" :disabled="saving || uploading" @click="avatarInput?.click()">{{ uploading ? '正在上传…' : '更换头像' }}</UiButton><input id="profile-avatar" ref="avatarInput" type="file" accept="image/png,image/jpeg,image/webp" hidden aria-label="上传头像" :disabled="saving || uploading" @change="uploadAvatar" /></div>
      <small>PNG、JPEG 或 WebP。保存资料后更新头像；取消不更改当前头像。</small><p v-if="avatarError" class="field-error" role="alert">{{ avatarError }}</p>
      <div><label for="profile-nickname">昵称 <span class="required-label">必填</span></label><UiInput id="profile-nickname" v-model="nickname" data-initial-focus required :maxlength="Math.max(40, [...(original?.nickname || '')].length)" :disabled="saving" :aria-invalid="!!nicknameError" aria-describedby="nickname-limit nickname-error" /><small id="nickname-limit">新昵称最多 40 个字符；已有更长昵称保持原值不受影响。</small><p id="nickname-error" role="alert" class="field-error">{{ nicknameError }}</p></div>
      <div v-for="field in optionalFields" :key="field.key"><label :for="'profile-' + field.key">{{ field.label }}</label><UiInput :id="'profile-' + field.key" v-model="fields[field.key]" :type="field.type" :maxlength="field.max" :disabled="saving" :aria-invalid="!!fieldErrors[field.key]" :aria-describedby="'profile-' + field.key + '-error'" :placeholder="field.type === 'email' || field.type === 'tel' ? '选填' : undefined" /><p :id="'profile-' + field.key + '-error'" role="alert" class="field-error">{{ fieldErrors[field.key] }}</p></div>
      <div><label for="profile-bio">个人简介</label><UiInput type="textarea" id="profile-bio" v-model="bio" rows="5" :maxlength="Math.max(300, [...(original?.bio || '')].length)" :disabled="saving" :aria-invalid="!!bioError" aria-describedby="bio-limit bio-error" /><small id="bio-limit">新的个人简介最多 300 个字符；已有更长简介保持原值不受影响。</small><p id="bio-error" role="alert" class="field-error">{{ bioError }}</p></div>
      <p v-if="saveError" role="alert" class="field-error">{{ saveError }}</p>
    </form><template #actions><UiButton type="submit" form="profile-form" class="button primary" :disabled="saving || uploading">{{ saving ? '正在保存…' : '保存资料' }}</UiButton></template>
  </AppDrawer>
  <AppDrawer v-model:open="detailOpen" title="积分流水详情"><template v-if="detail"><dl class="detail-list"><dt>流水 / 时间</dt><dd>{{ detail.ledger_id }}<br>{{ new Date(detail.created_at).toLocaleString('zh-CN') }}</dd><dt>类型 / 数量</dt><dd>{{ kinds[detail.kind] || '积分变动' }} / {{ detail.amount }} 积分</dd><dt>关联任务</dt><dd>{{ detail.task_name || (detail.task_id ? '历史任务' : '无') }}<small v-if="detail.task_id" class="ledger-task-id">{{ detail.task_id }}</small></dd><dt>说明</dt><dd>{{ detail.reason }}</dd></dl><h3>变更前</h3><dl class="detail-list"><dt>可用 / 冻结 / 已消费</dt><dd>{{ detail.balances_before.available }} / {{ detail.balances_before.frozen }} / {{ detail.balances_before.consumed }}</dd></dl><h3>变更后</h3><dl class="detail-list"><dt>可用 / 冻结 / 已消费</dt><dd>{{ detail.balances_after.available }} / {{ detail.balances_after.frozen }} / {{ detail.balances_after.consumed }}</dd></dl><UiButton v-if="detail.task_id" type="button" class="button" :disabled="sourceLoading" @click="showSource(true)">{{ sourceLoading ? '正在读取…' : '查看来源会话' }}</UiButton><p v-if="sourceError" class="field-error" role="alert">{{ sourceError }}</p><section v-if="source" data-testid="source-task"><h3>来源任务</h3><dl class="detail-list"><dt>任务编号</dt><dd>{{ source.task.task_id }}</dd><dt>创作指令</dt><dd>{{ source.input.instruction }}</dd><dt>原始报价</dt><dd>{{ source.task.quote.credits }} 积分</dd><dt>任务状态 / 结算状态</dt><dd>{{ taskStates[source.task.state] || '状态待确认' }} / {{ settlements[source.task.settlement_state] || '结算待确认' }}</dd></dl></section></template></AppDrawer>
  <ChangePasswordDrawer v-model:open="passwordOpen" />
</template>
<style scoped>
.account-page { margin-inline:auto; width:100%; max-width:1280px; height:100%; min-height:0; display:grid; grid-template-rows:minmax(0,1fr); gap:24px; }
.account-columns { display:grid; grid-template-columns:minmax(260px,.82fr) minmax(0,1.9fr); gap:24px; min-height:0; }
.account-columns>section { min-width:0; min-height:0; padding:24px; }
.profile-panel { display:flex; flex-direction:column; }
.profile-heading { display:flex; gap:16px; align-items:center; padding-bottom:24px; border-bottom:1px solid var(--color-border); flex-shrink:0; }
.profile-heading>div { min-width:0; }
.profile-heading h2 { margin:0; font-size:20px; white-space:nowrap; text-overflow:ellipsis; overflow:hidden; }
.profile-heading p { margin:2px 0 8px; font-size:13px; white-space:nowrap; text-overflow:ellipsis; overflow:hidden; }
.profile-details { flex:1; min-height:0; overflow-y:auto; margin-top:8px; }
.profile-details summary { min-height:44px; display:flex; align-items:center; cursor:pointer; font-size:15px; font-weight:600; }
.profile-details summary::after { content:''; width:7px; height:7px; border-right:1.5px solid currentColor; border-bottom:1.5px solid currentColor; transform:rotate(45deg); margin-left:auto; margin-right:4px; }
.profile-details[open] summary::after { transform:rotate(225deg); }
.profile-details summary::-webkit-details-marker { display:none; }
.profile-meta { margin:8px 0 20px; display:grid; gap:16px; font-size:14px; }
.profile-meta>div { display:grid; gap:3px; }
.profile-meta dt { color:var(--color-muted); }
.profile-meta dd { margin:0; overflow-wrap:anywhere; }
.profile-bio { white-space:pre-wrap; font-size:14px; margin:0 0 8px; padding-top:16px; border-top:1px solid var(--color-border); }
.profile-panel .action-row { display:grid; grid-template-columns:1fr 1fr; margin-top:20px; flex-shrink:0; }
.profile-panel .action-row>.primary { grid-column:1/-1; }
.profile-panel .action-row>.button { padding-inline:8px; }
.profile-form { gap:16px; }
.profile-edit-notice { margin:0; font-size:14px; }
.avatar-edit { display:flex; align-items:center; gap:16px; }
.profile-form label { font-size:14px; }
.required-label { color:var(--color-primary); font-size:12px; }
.profile-form small { font-size:12px; }
.profile-form .field-error:empty { display:none; }
.profile-signout { border-top:1px solid var(--color-border); margin-top:16px; padding-top:8px; flex-shrink:0; }
.profile-signout>.button { width:100%; background:transparent; border:0; color:var(--color-primary); }
.account-ledger { display:flex; flex-direction:column; }
.account-ledger>.section-heading { flex-shrink:0; margin-bottom:0; }
.account-ledger h2 { font-size:20px; }
.account-ledger .balance-grid { flex-shrink:0; padding:24px 0; border-bottom:1px solid var(--color-border); margin-top:8px; gap:0; }
.account-ledger .balance-grid>div { background:none; border-radius:0; padding:0 20px; }
.account-ledger .balance-grid>div:first-child { padding-left:0; }
.account-ledger .balance-grid>div+div { border-left:1px solid var(--color-border); }
.account-ledger .balance-grid strong { font-size:32px; color:var(--color-text); line-height:1.35; margin-top:4px; }
.account-ledger .balance-grid>div:first-child strong { color:var(--color-primary); }
.ledger-heading { padding:16px 0; }
.ledger-heading h3 { margin:0; font-size:16px; }
.ledger-filters { display:flex; align-items:flex-end; flex-wrap:wrap; gap:8px; margin-bottom:8px; flex-shrink:0; }
.ledger-filters>div:not(.ledger-filter-actions) { flex:1; min-width:130px; }
.ledger-filters label { display:block; font-size:12px; margin-bottom:4px; color:var(--color-muted); }
.ledger-filter-actions { display:flex; gap:8px; }
.consumption-summary { display:flex; flex-wrap:wrap; align-items:center; gap:6px 16px; flex-shrink:0; padding:4px 0 12px; font-size:13px; }
.consumption-summary>span:first-child { color:var(--color-muted); }
.consumption-summary strong { font-weight:600; font-variant-numeric:tabular-nums; }
.ledger-task-id { display:block; margin-top:4px; color:var(--color-muted); }
.ledger-feedback { margin:0 0 8px; font-size:14px; }
.ledger-table { flex:1; min-height:0; overflow:hidden; overscroll-behavior:contain; max-width:100%; border:1px solid var(--color-border); border-radius:8px; }
.ledger-table>.ui-data-table { width:100%; }
.ledger-table small { display:block; margin-top:3px; font-size:12px; white-space:nowrap; }
.ledger-table strong { font-size:14px; font-weight:500; }
.ledger-amount { font-weight:600; font-variant-numeric:tabular-nums; }
.ledger-source { height:auto; min-height:36px; white-space:normal; border:0; background:none; color:var(--color-primary); text-align:left; padding:0; max-width:150px; overflow-wrap:anywhere; text-decoration:underline; text-underline-offset:3px; }
.ledger-detail { border-color:transparent; background:transparent; color:var(--color-primary); padding-inline:8px; }
.ledger-empty { display:grid; place-content:center; height:100%; min-height:80px; margin:0; font-size:14px; }
.ledger-footer { flex-shrink:0; }
@media(min-width:701px) and (max-height:800px) {
  .account-columns>section { padding:20px; }
  .profile-heading { padding-bottom:16px; }
  .profile-meta { gap:10px; }
  .profile-meta>div { grid-template-columns:76px minmax(0,1fr); gap:8px; }
  .profile-panel .action-row { margin-top:12px; }
  .account-ledger .balance-grid { padding-block:16px; }
}
@media(min-width:701px) and (max-width:1050px) {
  .account-columns { grid-template-columns:260px minmax(0,1fr); gap:16px; }
  .account-columns>section { padding:20px; }
  .profile-heading { gap:12px; }
  .account-ledger .balance-grid>div { padding-inline:10px; }
}
@media(max-width:700px) {
  .account-page { gap:12px; }
  .account-columns { grid-template-columns:minmax(0,1fr); grid-template-rows:max-content minmax(620px,1fr); gap:12px; overflow-y:auto; }
  .account-columns>section { padding:12px; }
  .profile-panel { position:relative; max-height:40dvh; }
  .profile-heading { border:0; padding:0 64px 0 0; gap:12px; }
  .profile-heading :deep(.user-avatar) { width:44px!important; height:44px!important; font-size:20px!important; }
  .profile-heading>div { flex:1; }
  .profile-heading h2 { font-size:16px; }
  .profile-heading p { display:inline-block; max-width:calc(100% - 48px); vertical-align:middle; font-size:12px; margin:0 6px 0 0; }
  .profile-heading .status-label { padding:2px 6px; }
  .profile-signout { position:absolute; top:12px; right:8px; margin:0; padding:0; border:0; }
  .profile-signout>.button { padding-inline:6px; font-size:12px; }
  .profile-signout .field-error { position:absolute; top:44px; right:0; width:220px; padding:8px; background:var(--color-panel); z-index:2; }
  .profile-details { flex:initial; margin-top:4px; }
  .profile-details summary { min-height:32px; font-size:13px; }
  .profile-meta { grid-template-columns:1fr 1fr; gap:12px; margin-block:8px 12px; }
  .profile-bio { margin-bottom:4px; padding-top:12px; }
  .profile-panel .action-row { grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:4px; gap:6px; }
  .profile-panel .action-row>.primary { grid-column:auto; }
  .profile-panel .action-row>.button { font-size:12px; padding-inline:6px; }
  .account-ledger h2 { font-size:17px; }
  .account-ledger>.section-heading { flex-wrap:nowrap; gap:8px; }
  .account-ledger>.section-heading>.button { font-size:12px; padding-inline:10px; }
  .account-ledger .balance-grid { padding:10px 0; margin:0; }
  .account-ledger .balance-grid>div { padding-inline:12px; }
  .account-ledger .balance-grid span { font-size:12px; }
  .account-ledger .balance-grid strong { font-size:24px; margin:0; }
  .ledger-heading { padding:6px 0; }
  .ledger-heading h3 { font-size:15px; }
}
@media(max-width:700px) and (max-height:740px) {
  .account-page { gap:8px; }
  .account-columns { gap:8px; }
  .profile-heading :deep(.user-avatar) { display:none; }
  .profile-panel { max-height:34dvh; }
  .account-ledger .balance-grid { padding:6px 0; }
  .account-ledger .balance-grid strong { font-size:22px; }
}
</style>
