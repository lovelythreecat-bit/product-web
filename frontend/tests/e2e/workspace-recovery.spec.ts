import { test, expect } from '@playwright/test'
import { selectOption } from './ui-controls'

test('reopening restores a running task and a new conversation can submit independently', async ({ page }) => {
  const posts: string[] = [], errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => {
    class Events { onopen: (() => void) | null = null; constructor() { queueMicrotask(() => this.onopen?.()) } addEventListener() {} close() {} }
    Object.defineProperty(window, 'EventSource', { value: Events })
  })
  const quote = { credits: 8, agent_version: 'text-agent-v1', spec_id: 'text', spec_version: 'text-agent-v1', price_version: 'p1', input_digest: 'fixture', policy_versions: {} }
  let product = { product_id: 'product', version: 'pv1', created_at: '2026-10-16T01:00:00Z', product: { name: '原商品', product_type: 'home' } }
  const task = (id: string) => ({ task_id: id, state: 'RUNNING', settlement_state: 'FROZEN', state_version: 1, quote, work_ids: [], created_at: '2026-10-16T01:00:00Z', updated_at: '2026-10-16T01:00:00Z' })
  const tasks = [{ ...task('original-task'), conversation: 'original' }]
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname
    if (request.method() === 'POST') posts.push(path)
    if (path === '/api/v1/me') return route.fulfill({ json: { user_id: 'recovery-user', username: '恢复测试', role: 'user', status: 'active' } })
    if (path === '/api/v1/account') return route.fulfill({ json: { available: 100, frozen: 8 * tasks.length, consumed: 0 } })
    if (path === '/api/v1/agents') return route.fulfill({ json: [{ agent_id: 'text-agent', version: 'text-agent-v1', protocol_version: 'text-agent-v1', name: '文案', kind: 'copy', enabled: true, input_support: { product_required_fields: ['name'], min_materials: 0, max_materials: 3, instruction_required: false } }] })
    if (path === '/api/v1/conversations') {
      if (request.method() === 'POST') return route.fulfill({ json: { conversation_id: 'second', title: '新会话', created_at: '2026-10-16T02:00:00Z' } })
      return route.fulfill({ json: { items: [{ conversation_id: 'original', title: '原会话', created_at: '2026-10-16T01:00:00Z' }, { conversation_id: 'second', title: '新会话', created_at: '2026-10-16T02:00:00Z' }], next_cursor: null } })
    }
    if (path.startsWith('/api/v1/conversations/')) return route.fulfill({ json: {} })
    if (path.includes('/products/')) {
      if (request.method() === 'POST') product = { ...product, version: 'pv2', product: request.postDataJSON().product }
      return route.fulfill({ json: product })
    }
    if (path === '/api/v1/quotes') return route.fulfill({ json: quote })
    if (path === '/api/v1/tasks') {
      if (request.method() === 'POST') {
        const body = request.postDataJSON()
        expect(body.conversation_id).toBe('second')
        const added = { ...task('second-task'), conversation: 'second' }
        tasks.unshift(added)
        return route.fulfill({ status: 201, json: { task: added, replayed: false } })
      }
      const conversation = url.searchParams.get('conversation_id')
      return route.fulfill({ json: { items: tasks.filter(item => !conversation || item.conversation === conversation), next_cursor: null } })
    }
    if (path.startsWith('/api/v1/tasks/')) {
      const item = tasks.find(item => path.endsWith(item.task_id))!
      return route.fulfill({ json: { task: item, conversation_id: item.conversation, agent_id: 'text-agent', input: { product_version: product.version, product: product.product, instruction: '原任务要求', parameters: {}, material_versions: [] }, policy_versions: {} } })
    }
    return route.fulfill({ json: { items: [], next_cursor: null } })
  })
  await page.goto('/workspace')
  await expect(page).toHaveURL(/\/workspace\/original$/)
  await expect(page.locator('[data-task-id="original-task"]')).toContainText('生成中')
  await page.reload()
  await expect(page.locator('[data-task-id="original-task"]')).toContainText('生成中')
  await page.goto('/account')
  await page.getByRole('link', { name: '创作工作台', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace\/original$/)
  await expect(page.locator('[data-task-id="original-task"]')).toBeVisible()
  expect(posts.filter(path => path === '/api/v1/tasks')).toHaveLength(0)
  await page.getByRole('button', { name: '文案', exact: true }).click()
  await expect(page.getByLabel('文案类型', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '新建任务', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace\/second$/)
  await expect(page.getByLabel('文案类型', { exact: true })).toBeVisible()
  await expect(page.getByLabel('创作指令', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '填写资料', exact: true }).click()
  await expect(page.locator('#product-model')).toHaveCount(0)
  await page.getByLabel('商品名称', { exact: true }).fill('第二个商品')
  await selectOption(page.getByLabel('商品类型', { exact: false }), 'home')
  await page.getByLabel('商品卖点与说明', { exact: true }).fill('350ml，奶油白釉面')
  await page.getByRole('button', { name: '保存商品资料', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.getByRole('button', { name: '确认费用并生成', exact: true }).click()
  await page.getByRole('dialog', { name: '确认本次生成' }).getByRole('button', { name: '确认并冻结积分' }).click()
  await expect(page.locator('[data-task-id="second-task"]')).toContainText('生成中')
  expect(tasks.every(item => item.state === 'RUNNING')).toBe(true)
  expect(posts.filter(path => path === '/api/v1/tasks')).toHaveLength(1)
  await page.goto('/workspace/original')
  await expect(page.locator('[data-task-id="original-task"]')).toContainText('生成中')
  expect(errors).toEqual([])
})
