import { test, expect } from '@playwright/test'
import { resolve } from 'node:path'

test('deletes recent history and regenerates into an independent task', async ({ page }, info) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => {
    class TestEvents { onopen: (() => void) | null = null; onerror = null; constructor() { queueMicrotask(() => this.onopen?.()) } addEventListener() {} close() {} }
    Object.defineProperty(window, 'EventSource', { value: TestEvents })
  })
  const quote = { credits: 8, agent_version: 'text-agent-v1', spec_id: 'text', spec_version: 'text-agent-v1', price_version: 'p1', input_digest: 'fixture', policy_versions: {} }
  const product = { product_id: 'product', version: 'pv-old', created_at: '2026-10-18T01:00:00Z', product: { name: '陶瓷马克杯', product_type: 'home', category: '家居日用', description: '杯口圆润，日常饮水使用' } }
  const task = (id: string, conversation: string, state: string, at: string) => ({ task: { task_id: id, display_number: 'T-' + id, state, state_version: 1, settlement_state: state === 'SUCCEEDED' ? 'CONSUMED' : 'FROZEN', created_at: at, updated_at: at, quote, work_ids: [] }, conversation_id: conversation, conversation_display_number: 'H-' + conversation, agent_id: 'text-agent', input: { product_version: product.version, product: product.product, instruction: '原任务的创作指令', parameters: {}, material_versions: [] }, policy_versions: {} })
  const original = task('old-task', 'original', 'SUCCEEDED', '2026-10-18T01:00:00Z')
  const originalSnapshot = JSON.stringify(original)
  const details = [original]
  const hidden = new Set<string>(), submissions: { body: any; key?: string }[] = []
  let conversations = 0
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname
    if (path === '/api/v1/me') return route.fulfill({ json: { user_id: 'history-fixture', username: '工作台验证', role: 'user', status: 'active' } })
    if (path === '/api/v1/account') return route.fulfill({ json: { available: 100 - submissions.length * 8, frozen: submissions.length * 8, consumed: 0 } })
    if (path === '/api/v1/agents') return route.fulfill({ json: [{ agent_id: 'text-agent', version: 'text-agent-v1', protocol_version: 'text-agent-v1', name: '文案', kind: 'copy', enabled: true, input_support: { product_required_fields: ['name'], min_materials: 0, max_materials: 3, instruction_required: false } }] })
    if (path === '/api/v1/conversations' && request.method() === 'POST') { conversations++; return route.fulfill({ json: { conversation_id: 'independent-' + conversations, created_at: '2026-10-18T02:00:00Z' } }) }
    if (path.includes('/products/')) return route.fulfill({ json: product })
    if (path === '/api/v1/quotes') return route.fulfill({ json: quote })
    if (path === '/api/v1/tasks' && request.method() === 'POST') {
      const body = request.postDataJSON(); submissions.push({ body, key: request.headers()['idempotency-key'] })
      const next = task('new-task', body.conversation_id, 'RUNNING', '2026-10-18T02:00:00Z'); next.input = body.input; details.unshift(next)
      return route.fulfill({ status: 201, json: { task: next.task, replayed: false } })
    }
    if (path === '/api/v1/tasks') return route.fulfill({ json: { items: details.filter(item => !hidden.has(item.task.task_id) && (!url.searchParams.get('conversation_id') || item.conversation_id === url.searchParams.get('conversation_id'))).map(item => item.task), next_cursor: null } })
    if (path.startsWith('/api/v1/tasks/')) {
      const id = path.split('/').at(-1)!
      if (request.method() === 'DELETE') { hidden.add(id); return route.fulfill({ status: 204 }) }
      return route.fulfill({ json: details.find(item => item.task.task_id === id) })
    }
    return route.fulfill({ json: { items: [], next_cursor: null } })
  })
  await page.goto('/workspace/original?task=old-task')
  await expect(page.getByLabel('创作指令', { exact: true })).toHaveValue('原任务的创作指令')
  await page.getByRole('button', { name: '基于此任务再生成', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace\/independent-1$/)
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.getByRole('button', { name: '取消', exact: true }).click()
  expect(submissions).toHaveLength(0)
  await page.getByLabel('创作指令', { exact: true }).fill('新任务单独调整的指令')
  await page.getByRole('button', { name: '确认费用并生成', exact: true }).click()
  await page.getByRole('button', { name: '确认并冻结积分', exact: true }).click()
  await expect(page).toHaveURL(/independent-1\?task=new-task$/)
  expect(conversations).toBe(1)
  expect(submissions).toHaveLength(1)
  expect(submissions[0].body.conversation_id).toBe('independent-1')
  expect(submissions[0].body.input.instruction).toBe('新任务单独调整的指令')
  expect(submissions[0].key).toBeTruthy()
  expect(JSON.stringify(original)).toBe(originalSnapshot)
  await page.goto('/workspace/original?task=old-task')
  await expect(page.getByLabel('创作指令', { exact: true })).toHaveValue('原任务的创作指令')
  const deleteButton = info.project.name === 'mobile' ? page.getByRole('button', { name: '删除所选任务', exact: true }) : page.locator('.task-history-row').filter({ has: page.locator('a[href="/workspace/original?task=old-task"]') }).getByRole('button', { name: '删除任务：陶瓷马克杯', exact: true })
  if (info.project.name === 'desktop') {
    const button = await deleteButton.boundingBox()
    const meta = await page.locator('.task-history-item[aria-current="page"] .task-meta').boundingBox()
    expect(button!.y + button!.height).toBeLessThanOrEqual(meta!.y)
  }
  await deleteButton.click()
  const dialog = page.getByRole('dialog', { name: '删除任务', exact: true })
  await expect(dialog.getByRole('button', { name: '取消', exact: true })).toBeFocused()
  await page.screenshot({ path: resolve('../docs/verification/screenshots/task-history-delete-' + info.project.name + '.png'), fullPage: true })
  await dialog.getByRole('button', { name: '确认删除', exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(page).toHaveURL(/independent-1\?task=new-task$/)
  await page.reload()
  await expect(page.locator('a[href="/workspace/original?task=old-task"]')).toHaveCount(0)
  await expect(page.locator('[data-task-id="new-task"]')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: resolve('../docs/verification/screenshots/task-history-actions-' + info.project.name + '.png'), fullPage: true })
  expect(errors).toEqual([])
})
