import { expect, test } from '@playwright/test'
import { resolve } from 'node:path'
import { selectOption } from './ui-controls'

test('reasoning effort saves, reloads and resets through the existing model drawer', async ({ page }, info) => {
  const row = { id: '00000000-0000-4000-8000-000000000001', name: 'TEST_ONLY 文本模型', provider: 'openai_chat', base_url: 'https://models.example/v1', model: 'test-model', supports_images: false, timeout_seconds: 60, temperature: null, max_tokens: null, reasoning_effort: 'low' as string | null, enabled: true, has_api_key: true, revision: 3 }
  const writes: unknown[] = []
  await page.route('**/api/v1/admin/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/text-service-connection')) return route.fulfill({ json: { base_url: 'http://127.0.0.1:8000', has_service_key: true, revision: 1 } })
    if (path.endsWith('/text-default-model')) return route.fulfill({ json: { model_config_id: row.id, revision: 1, connection_revision: 1, generation_policy_configured: true } })
    if (path.endsWith('/text-model-configs/' + row.id)) {
      if (route.request().method() === 'PATCH') {
        const config = route.request().postDataJSON().config
        writes.push(config.reasoning_effort); row.reasoning_effort = config.reasoning_effort; row.revision++
      }
      return route.fulfill({ json: row })
    }
    return route.fulfill({ json: path.endsWith('/text-model-configs') ? { items: [row], next_cursor: null } : [] })
  })
  await page.goto('/tests/fixtures/agent-configs.html')
  await page.getByRole('button', { name: '配置模型', exact: true }).click()
  const control = page.getByRole('combobox', { name: '推理强度', exact: true })
  const value = page.locator('select[data-select-id="text-model-reasoning"]')
  await expect(value).toHaveValue('low')
  await selectOption(control, 'high')
  await page.getByRole('button', { name: '保存模型配置', exact: true }).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await page.reload()
  await page.getByRole('button', { name: '配置模型', exact: true }).click()
  await expect(value).toHaveValue('high')
  await control.scrollIntoViewIfNeeded()
  await page.screenshot({ path: resolve('../docs/verification/screenshots/text-reasoning-2026-10-18-' + info.project.name + '.png') })
  await selectOption(control, '')
  await page.getByRole('button', { name: '保存模型配置', exact: true }).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await page.reload()
  await page.getByRole('button', { name: '配置模型', exact: true }).click()
  await expect(value).toHaveValue('')
  expect(writes).toEqual(['high', null])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('saved warnings appear only in task details across workspace and works', async ({ page }, info) => {
  const errors: string[] = [], generationPosts: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => {
    class Events { onopen: (() => void) | null = null; constructor() { queueMicrotask(() => this.onopen?.()) } addEventListener() {} close() {} }
    Object.defineProperty(window, 'EventSource', { value: Events })
  })
  const quote = { credits: 8, agent_version: 'v1', spec_id: 'copy', spec_version: 'v1', price_version: 'p1', input_digest: 'fixture', policy_versions: {} }
  const task = { task_id: 'copy-task', display_number: 'T20261018-000001', state: 'SUCCEEDED', settlement_state: 'CONSUMED', state_version: 6, quote, work_ids: ['copy-work'], created_at: '2026-10-18T06:00:00Z' }
  const source = { task, conversation_id: 'warnings', agent_id: 'copy-agent', input: { product_version: 'pv1', product: { name: '陶瓷杯' }, instruction: '', parameters: {}, material_versions: [] }, policy_versions: {}, materials: [], ledger_ids: [] }
  const work = { work_id: 'copy-work', task_id: task.task_id, conversation_id: 'warnings', kind: 'copy', items: [{ file_id: 'copy-file', text: '让日常饮水，多一点从容。\n简洁杯身，适合办公与居家场景。' }], warnings: ['商品材质信息尚待核实，请确认后再发布。', '请核实是否具备耐热检测依据。'], created_at: task.created_at, source }
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (route.request().method() === 'POST' && path === '/api/v1/tasks') generationPosts.push(path)
    if (path === '/api/v1/me') return route.fulfill({ json: { user_id: 'warning-owner', role: 'user', status: 'active', username: '提示预览' } })
    if (path === '/api/v1/account') return route.fulfill({ json: { available: 100, frozen: 0, consumed: 8 } })
    if (path === '/api/v1/agents') return route.fulfill({ json: [{ agent_id: 'copy-agent', version: 'v1', name: '文案', kind: 'copy', enabled: true, protocol_version: 'text-agent-v1', input_support: { product_required_fields: ['name'], min_materials: 0, max_materials: 4, instruction_required: false } }] })
    if (path === '/api/v1/tasks') return route.fulfill({ json: { items: [task], next_cursor: null } })
    if (path === '/api/v1/tasks/copy-task') return route.fulfill({ json: source })
    if (path === '/api/v1/works/copy-work') return route.fulfill({ json: work })
    if (path === '/api/v1/works') return route.fulfill({ json: { items: [work], next_cursor: null } })
    if (path.includes('/products/')) return route.fulfill({ json: { product_id: 'product', version: 'pv1', product: { name: '陶瓷杯' } } })
    if (path === '/api/v1/quotes') return route.fulfill({ json: quote })
    if (path === '/api/v1/conversations') return route.fulfill({ json: { items: [{ conversation_id: 'warnings', title: '陶瓷杯', created_at: task.created_at }], next_cursor: null } })
    return route.fulfill({ json: {} })
  })
  await page.goto('/workspace/warnings?task=copy-task')
  await expect(page.locator('.task-history .copy-result')).toContainText('让日常饮水')
  await expect(page.locator('.task-history')).not.toContainText('待核实')
  await page.reload()
  await page.getByRole('button', { name: '任务详情', exact: true }).click()
  const details = page.getByRole('dialog', { name: '任务详情', exact: true })
  const notice = details.getByRole('complementary', { name: '待核实提示' })
  await expect(notice).toContainText('请核实是否具备耐热检测依据')
  await notice.scrollIntoViewIfNeeded()
  await page.screenshot({ path: resolve('../docs/verification/screenshots/task-detail-warnings-2026-10-18-' + info.project.name + '.png') })
  await details.getByRole('contentinfo').getByRole('button', { name: '关闭', exact: true }).click()
  await expect(details).not.toBeVisible()
  await page.getByRole('button', { name: '预览', exact: true }).click()
  const preview = page.getByRole('dialog', { name: '作品预览' })
  await expect(preview.getByRole('complementary', { name: '待核实提示' })).toHaveCount(0)
  await expect(preview.locator('.copy-result')).not.toContainText('尚待核实')
  await preview.getByRole('contentinfo').getByRole('button', { name: '关闭', exact: true }).click()
  await page.goto('/works')
  await expect(page.locator('.works-grid .copy-result')).toContainText('让日常饮水')
  await expect(page.locator('.works-grid')).not.toContainText('待核实')
  await page.getByRole('button', { name: '任务详情', exact: true }).click()
  await expect(details.getByRole('complementary', { name: '待核实提示' })).toContainText('商品材质信息尚待核实')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  expect(generationPosts).toEqual([])
  expect(errors).toEqual([])
})
