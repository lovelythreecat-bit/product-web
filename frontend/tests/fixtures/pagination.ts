/** TEST_ONLY: actual pages, synthetic read responses, no server writes. */
import { createApp } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from '../../src/App.vue'
import UsersView from '../../src/features/admin/UsersView.vue'
import TasksView from '../../src/features/admin/TasksView.vue'
import CreditsView from '../../src/features/admin/CreditsView.vue'
import AuditView from '../../src/features/admin/AuditView.vue'
import AccountView from '../../src/features/account/AccountView.vue'
import WorksView from '../../src/features/works/WorksView.vue'
import { session } from '../../src/features/auth/session'
import '../../src/styles/element-components'
import '../../src/styles/tokens.css'
import '../../src/styles/element-theme.css'

const params = new URLSearchParams(location.search)
const requests: string[] = []
Object.assign(window, { paginationRequests: requests, paginationFailNext: false })
const at = '2026-10-21T00:00:00Z'
const balances = { available: 100, frozen: 8, consumed: 20 }
const user = (id: string) => ({ id, account_normalized: '测试商家_' + id, nickname: '店主', role: 'user', status: 'active', auth_version: 0, profile_version: '0'.repeat(64), created_at: at, ...balances })
const ledger = (id: string) => ({ ledger_id: id, account: '测试商家', kind: 'admin_grant', amount: 10, task_id: null, reason: '测试流水_' + id, created_at: at, balances_before: balances, balances_after: balances })
const task = (id: string) => ({ id, user_id: 'u1', account: '测试商家_' + id, state: 'SUCCEEDED', settlement_state: 'CONSUMED', agent_id: 'text', elapsed_seconds: 3, fixed_credits: 8 })
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })
window.fetch = async (input, init) => {
  const url = new URL(typeof input === 'string' ? input : input instanceof Request ? input.url : input.href, location.origin)
  requests.push(url.pathname + url.search)
  if (init?.method && init.method !== 'GET') return json({ detail: 'TEST_ONLY writes blocked' }, 409)
  const path = url.pathname
  if (path === '/api/v1/me') return json({ user_id: 'admin', account: '测试管理员', role: 'admin', status: 'active', nickname: '测试商家' })
  if (path === '/api/v1/account') return json({ ...balances, credited_total: 128 })
  if (path.endsWith('/agents')) return json([{ agent_id: 'text', name: '文案', kind: 'copy', enabled: true }])
  if (path === '/api/v1/admin/users') return json({ items: [user('u1')], next_cursor: null })
  const total = params.has('empty') ? 0 : url.searchParams.has('q') || url.searchParams.has('start_time') ? 23 : 123
  const pageSize = Number(url.searchParams.get('limit') || 20)
  const page = Math.min(Number(url.searchParams.get('page') || 1), Math.max(1, Math.ceil(total / pageSize)))
  const mockWindow = window as unknown as { paginationFailNext: boolean }
  if (mockWindow.paginationFailNext) { mockWindow.paginationFailNext = false; return json({ detail: 'TEST_ONLY request failed' }, 503) }
  await new Promise(resolve => setTimeout(resolve, 120))
  const make = path.endsWith('/managed-users') ? user : path.endsWith('/ledger') ? ledger : path.endsWith('/tasks') ? task : path.endsWith('/works')
    ? (id: string) => ({ work_id: id, task_id: id, conversation_id: id, kind: 'copy', name: '测试作品_' + id, created_at: at, items: [] })
    : (id: string) => ({ id, action: 'admin_credit_grant', actor_id: null, object_id: id, reason: '测试操作_' + id, created_at: at, changes: {} })
  return json({ items: Array.from({ length: Math.max(0, Math.min(pageSize, total - (page - 1) * pageSize)) }, (_, i) => make(String((page - 1) * pageSize + i + 1))), next_cursor: null, total, page, page_size: pageSize, consumption: { copy: 5, image: 8, video: 20, other: 0 } })
}
await session.restore()
const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/admin/users', component: UsersView }, { path: '/admin/tasks', component: TasksView },
  { path: '/admin/credits', component: CreditsView }, { path: '/admin/logs', component: AuditView },
  { path: '/account', component: AccountView }, { path: '/works', component: WorksView },
] })
await router.push(params.get('route') || '/admin/users')
createApp(App).use(router).mount('#app')
