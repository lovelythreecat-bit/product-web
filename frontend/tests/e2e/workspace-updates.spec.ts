import { selectOption } from './ui-controls'
import { test, expect } from '@playwright/test'
import { resolve } from 'node:path'

test('workspace supports typed products, direct assistance, scene parameters and owner failure choices', async ({ page }, info) => {
  const errors: string[] = [], writes: { path: string; body: any; key?: string }[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => {
    // This test exercises the mounted UI against deterministic HTTP fixtures, without a DB.
    class TestEvents { onopen: (() => void) | null = null; onerror = null; constructor() { queueMicrotask(() => this.onopen?.()) } addEventListener() {} close() {} }
    Object.defineProperty(window, 'EventSource', { value: TestEvents })
  })
  let product = { product_id: 'product', version: 'v1', created_at: '2026-10-16T01:00:00Z', product: { name: '轻量通勤外套', product_type: 'clothing', category: '服饰内衣', fabric: '棉 95%、氨纶 5%', sellingPoints: '轻便易收纳，适合日常通勤' } as Record<string, unknown> }
  const quote = { credits: 8, agent_version: 'text-agent-v1', spec_id: 'text', spec_version: 'text-agent-v1', price_version: 'p1', input_digest: 'test-only', policy_versions: {} }
  const task = (id: string, at: string, state = 'FAILED', settlement = 'FROZEN') => ({ task_id: id, display_number: 'T20261016-00000' + id.slice(-1), state, settlement_state: settlement, state_version: 1, created_at: at, updated_at: at, quote, work_ids: [], investigation_reason: null })
  const tasks = [task('task-2', '2026-10-16T02:00:00Z'), task('task-1', '2026-10-16T01:00:00Z')]
  const detail = (item: typeof tasks[number]) => ({ task: item, conversation_id: 'demo', conversation_display_number: 'H20261016-000001', agent_id: 'text-agent', input: { product_version: product.version, product: product.product, instruction: '介绍商品的真实特点', parameters: { copy_type: '宣传文案' }, material_versions: [] }, policy_versions: {} })
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname
    if (request.method() !== 'GET') writes.push({ path, body: request.postDataJSON(), key: request.headers()['idempotency-key'] })
    if (path === '/api/v1/me') return route.fulfill({ json: { user_id: 'fixture-user', username: '工作台预览', role: 'user', status: 'active' } })
    if (path === '/api/v1/account') {
      const frozen = tasks.filter(item => item.settlement_state === 'FROZEN').length * 8
      return route.fulfill({ json: { available: 100 - frozen, frozen, consumed: 0 } })
    }
    if (path === '/api/v1/agents') return route.fulfill({ json: [{ agent_id: 'text-agent', version: 'text-agent-v1', protocol_version: 'text-agent-v1', name: '文案', kind: 'copy', enabled: true, input_support: { product_required_fields: ['name'], min_materials: 0, max_materials: 3, instruction_required: false } }] })
    if (path === '/api/v1/conversations') return route.fulfill({ json: { items: [{ conversation_id: 'demo', display_number: 'H20261016-000001', title: '通勤外套创作', created_at: '2026-10-16T01:00:00Z' }], next_cursor: null } })
    if (path.startsWith('/api/v1/conversations/')) return route.fulfill({ json: {} })
    if (path.includes('/products/')) {
      if (request.method() === 'POST') product = { ...product, version: 'v2', product: request.postDataJSON().product }
      return route.fulfill({ json: product })
    }
    if (path === '/api/v1/quotes') return route.fulfill({ json: quote })
    if (path === '/api/v1/assist/prompts') return route.fulfill({ json: { proposed: '轻装出发，从容通勤。柔软面料与轻便设计，陪你自在穿行每一天。', missing_facts: [] } })
    if (path === '/api/v1/tasks') return route.fulfill({ json: { items: tasks, next_cursor: null } })
    if (path.endsWith('/release')) {
      const item = tasks.find(value => path.includes(value.task_id))!; item.settlement_state = 'RELEASED'; item.state_version++
      return route.fulfill({ json: item })
    }
    if (path.endsWith('/retry')) {
      const item = tasks.find(value => path.includes(value.task_id))!; item.settlement_state = 'RELEASED'; item.state_version++
      const successor = task('task-3', '2026-10-16T03:00:00Z', 'QUEUED'); tasks.unshift(successor)
      return route.fulfill({ json: { task: successor, replayed: false } })
    }
    if (path.startsWith('/api/v1/tasks/')) {
      const item = tasks.find(value => path.endsWith('/' + value.task_id))!
      if (item.task_id === 'task-2') await new Promise(ok => setTimeout(ok, 80))
      return route.fulfill({ json: detail(item) })
    }
    return route.fulfill({ json: { items: [], next_cursor: null } })
  })
  await page.goto('/workspace/demo')
  await expect(page.locator('[data-task-id]').first()).toHaveAttribute('data-task-id', 'task-2')
  await expect(page.getByText(/生成时间/).first()).toBeVisible()
  await expect(page.getByRole('button', { name: '编辑资料', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '文案', exact: true }).click()
  await page.getByLabel('文案类型', { exact: true }).fill('直播口播')
  await page.getByLabel('目标平台', { exact: true }).fill('抖音')
  await page.getByLabel('目标人群', { exact: true }).fill('通勤者')
  await page.getByLabel('语气', { exact: true }).fill('亲切')
  await page.getByLabel('最大字符数', { exact: true }).fill('120')
  await page.getByLabel('额外协作要求', { exact: true }).fill('先讲场景，再讲面料')
  await page.getByLabel('创作指令', { exact: true }).fill('保持事实准确')
  await page.getByRole('button', { name: 'AI 帮我完善', exact: true }).click()
  await expect(page.getByLabel('创作指令', { exact: true })).toHaveValue(/轻装出发/)
  expect(writes.find(write => write.path.endsWith('/assist/prompts'))?.body.parameters).toMatchObject({ copy_type: '直播口播', platform: '抖音', audience: '通勤者', tone: '亲切', max_chars: 120, extra_instructions: '先讲场景，再讲面料' })
  await page.getByRole('button', { name: '撤回辅助，恢复原指令' }).click()
  await expect(page.getByLabel('创作指令', { exact: true })).toHaveValue('保持事实准确')
  await page.getByRole('button', { name: '编辑资料', exact: true }).click()
  await expect(page.getByLabel('面料成分', { exact: true })).toHaveValue('棉 95%、氨纶 5%')
  await selectOption(page.getByLabel('商品类型', { exact: false }), 'digital')
  await expect(page.getByLabel('存储容量', { exact: true })).toBeVisible()
  await expect(page.getByLabel('面料成分', { exact: true })).toBeVisible() // Saved facts remain editable as existing information.
  await selectOption(page.getByLabel('商品类型', { exact: false }), 'clothing')
  await page.screenshot({ path: resolve('../docs/verification/screenshots/task-results-2026-10-17-product-types-' + info.project.name + '.png') })
  await page.getByRole('button', { name: '保存商品资料', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  if (info.project.name === 'mobile') await selectOption(page.getByRole('combobox', { name: '最近任务', exact: true }), 'task-1')
  else await page.locator('.task-history-item[href="/workspace/demo?task=task-1"]').click()
  const older = page.locator('[data-task-id="task-1"]')
  await older.getByRole('button', { name: '释放积分', exact: true }).click()
  await page.getByRole('dialog', { name: '确认释放积分', exact: true }).locator('[data-confirm-failed-action]').click()
  await expect(older.getByRole('button', { name: '释放积分', exact: true })).toHaveCount(0)
  if (info.project.name === 'mobile') await selectOption(page.getByRole('combobox', { name: '最近任务', exact: true }), 'task-2')
  else await page.locator('.task-history-item[href="/workspace/demo?task=task-2"]').click()
  const newest = page.locator('[data-task-id="task-2"]')
  await newest.getByRole('button', { name: '重试', exact: true }).click()
  await page.getByRole('dialog', { name: '确认重试', exact: true }).locator('[data-confirm-failed-action]').click()
  await expect(page.locator('[data-task-id]').first()).toHaveAttribute('data-task-id', 'task-3')
  await expect(page).toHaveURL(/task=task-3/)
  await expect(page.getByText('正在核对原任务，生成会继续进行。', { exact: true })).toHaveCount(0)
  expect(writes.filter(write => /\/(retry|release)$/.test(write.path))).toHaveLength(2)
  expect(writes.filter(write => /\/(retry|release)$/.test(write.path)).every(write => !!write.key)).toBe(true)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(100)
  await page.screenshot({ path: resolve('../docs/verification/screenshots/task-results-2026-10-17-updates-' + info.project.name + '.png'), fullPage: true })
  expect(errors).toEqual([])
})
