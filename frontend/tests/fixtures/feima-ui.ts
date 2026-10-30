/** TEST_ONLY: real page components; synthetic read data, all writes blocked. Not a build entry. */
import { createApp } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import App from '../../src/App.vue'
import HomeView from '../../src/features/site/HomeView.vue'
import WorkspaceView from '../../src/features/workspace/WorkspaceView.vue'
import LoginView from '../../src/features/auth/LoginView.vue'
import RegisterView from '../../src/features/auth/RegisterView.vue'
import WorksView from '../../src/features/works/WorksView.vue'
import AccountView from '../../src/features/account/AccountView.vue'
import UsersView from '../../src/features/admin/UsersView.vue'
import { session } from '../../src/features/auth/session'
import { setTheme } from '../../src/styles/theme'
import '../../src/styles/element-components'
import '../../src/styles/tokens.css'
import '../../src/styles/element-theme.css'
import '../../src/features/workspace/workspace.css'
import '../../src/styles/themes.css'

const params = new URLSearchParams(location.search)
const route = params.get('route') || '/'
setTheme(params.get('theme') === 'dark' ? 'dark' : 'light')
const at = '2026-10-30T01:32:00Z'
const quote = { credits: 10, agent_version: 'text-agent-v1', spec_id: 'text', spec_version: 'v1', price_version: 'v1', input_digest: 'TEST_ONLY', policy_versions: {} }
const product = { name: '轻量缓震运动鞋', product_type: 'shoes_bags', category: '运动鞋', brand: '示例品牌', material: '针织鞋面', color: '奶油白', description: '轻量鞋身、透气面料，日常行走缓震。', size: '36–44' }
const text = '每一步，都轻一点。\n\n早高峰的赶路，午后的一小段散步，\n把日常交给一双轻盈的鞋。\n\n柔软的针织鞋面，贴合双脚，也留出呼吸的空间。\n缓震中底接住每一次落地，让出门这件小事，多一点自在。\n\n轻装出发，走自己的节奏。\n\n奶油白配色，搭配牛仔裤、运动裤都干净利落。\n从通勤到周末，一双鞋，陪你走过日常的不同场景。\n\n选一双舒服的鞋，去看看今天的风景。'
const task = (id: string) => ({ task_id: id, state: 'SUCCEEDED', settlement_state: 'CONSUMED', state_version: 1, quote, work_ids: ['work-' + id], created_at: at, updated_at: at })
const tasks = [task('TEST_ONLY-shoes'), task('TEST_ONLY-bag')]
const detail = (id: string) => ({ task: tasks.find(t => t.task_id === id) || tasks[0], conversation_id: 'TEST_ONLY', agent_id: 'text-agent', policy_versions: {}, input: { product_version: 'TEST_ONLY-product', product: id.endsWith('bag') ? { ...product, name: '日常通勤帆布包' } : product, parameters: { copy_type: '宣传文案', platform: '小红书', tone: '自然' }, material_versions: [], instruction: '为这款商品写一篇宣传文案，突出真实卖点，语气自然，有生活感。' } })
const work = (id: string) => ({ work_id: 'work-' + id, task_id: id, conversation_id: 'TEST_ONLY', kind: 'copy', name: '轻量缓震运动鞋', created_at: at, items: [{ file_id: 'file-' + id, media_type: 'text/plain', text }], source: { ...detail(id), materials: [], ledger_ids: [], credit_reservation_id: 'TEST_ONLY' } })
const balances = { available: 286, frozen: 0, consumed: 20, credited_total: 306 }
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })
const requests: string[] = []
Object.assign(window, { feimaFixtureRequests: requests })
window.fetch = async (resource, init) => {
  const path = new URL(typeof resource === 'string' ? resource : resource instanceof Request ? resource.url : resource.href, location.origin).pathname
  requests.push(`${init?.method || 'GET'} ${path}`)
  if (init?.method && init.method !== 'GET') return json({ error: { code: 'TEST_ONLY', message: '界面验证阻止所有真实写入。' } }, 409)
  if (path === '/api/v1/me') return route === '/' || route.includes('login') || route.includes('register') ? json({}, 401) : json({ user_id: 'TEST_ONLY', account: '示例商家', nickname: '林', role: 'admin', status: 'active', shop_name: '示例店铺', category: '鞋靴箱包' })
  if (path === '/api/v1/site/brand') return json({ name: '飞马', version: 1 })
  if (path === '/api/v1/site/content') return json({ content: null })
  if (path === '/api/v1/site/cases' || path === '/api/v1/quick-generation') return json([])
  if (path === '/api/v1/account') return json(balances)
  if (path === '/api/v1/agents') return json([{ agent_id: 'text-agent', kind: 'copy', name: '文案', enabled: true, version: 'text-agent-v1', protocol_version: 'text-agent-v1', input_support: { product_required_fields: ['name'], min_materials: 0, max_materials: 20, instruction_required: false } }])
  if (path === '/api/v1/tasks') return json({ items: tasks, next_cursor: null })
  if (path.startsWith('/api/v1/tasks/')) return json(detail(path.split('/').at(-1)!))
  if (path === '/api/v1/works') return json({ items: tasks.map(t => work(t.task_id)), total: 2, page: 1, page_size: 10, next_cursor: null })
  if (path.startsWith('/api/v1/works/')) return json(work(path.split('/').at(-1)!.replace('work-', '')))
  if (path.includes('/products/')) return json({ product_id: 'TEST_ONLY', version: 'TEST_ONLY-product', product, created_at: at })
  if (path.startsWith('/api/v1/conversations/')) return json({})
  if (path === '/api/v1/account/ledger') return json({ items: [{ ledger_id: 'TEST_ONLY-ledger', kind: 'consume', amount: 10, reason: '文案创作', created_at: at, task_id: tasks[0]!.task_id, balances_before: { ...balances, available: 296 }, balances_after: balances }], total: 1, page: 1, page_size: 20, next_cursor: null, consumption: { copy: 20, image: 0, video: 0, other: 0 } })
  if (path === '/api/v1/admin/managed-users' || path === '/api/v1/admin/users') return json({ items: [{ id: 'TEST_ONLY', account_normalized: '示例商家', nickname: '林', role: 'user', status: 'active', profile_version: '0'.repeat(64), auth_version: 0, created_at: at, ...balances }], total: 1, page: 1, page_size: 20, next_cursor: null })
  return json({ items: [], next_cursor: null })
}
class FixtureEvents { onopen: (() => void) | null = null; constructor() { queueMicrotask(() => this.onopen?.()) } addEventListener() {} removeEventListener() {} close() {} }
Object.defineProperty(window, 'EventSource', { value: FixtureEvents })
await session.restore()
const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/', component: HomeView }, { path: '/login', component: LoginView }, { path: '/register', component: RegisterView },
  { path: '/workspace/:conversationId', component: WorkspaceView }, { path: '/works', component: WorksView },
  { path: '/account', component: AccountView }, { path: '/admin/users', component: UsersView },
] })
await router.push(route)
createApp(App).use(router).mount('#app')
