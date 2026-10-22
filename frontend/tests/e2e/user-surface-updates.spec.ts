import { expect, test } from '@playwright/test'
import { selectOption } from './ui-controls'

test('works and account keep their controls fixed without duplicate titles while lists scroll and paginate', async ({ page }, info) => {
  const errors: string[] = [], workRequests: string[] = [], ledgerRequests: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  const work = (index: number) => ({
    work_id: 'work-' + index, task_id: 'task-' + index, conversation_id: 'demo', kind: 'copy',
    name: index === 0 ? '秋日新品 · 通勤外套宣传文案' : '商品创作文案 ' + (index + 1), conversation_title: '秋日上新', created_at: '2026-10-18T01:00:00Z',
    items: [{ file_id: 'file-' + index, text: '轻装出发，从容通勤。\n柔软面料与简洁剪裁，让每天的穿搭多一种选择。\n保留商品真实特点，表达自然舒适。\n面向日常通勤，兼顾轻便与实用。' }],
  })
  const ledger = (index: number) => ({ ledger_id: 'ledger-' + index, kind: index % 2 ? 'freeze' : 'consume', amount: 8, task_id: 'task-' + index, reason: '文案创作', created_at: '2026-10-18T01:00:00Z', balances_before: { available: 100, frozen: 8, consumed: 0 }, balances_after: { available: 92, frozen: 0, consumed: 8 } })
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url()), path = url.pathname
    if (path === '/api/v1/me') return route.fulfill({ json: { user_id: 'fixture-user', account: 'merchant_demo', nickname: '映作体验店', bio: '让好商品被看见。', shop_name: '映作好物店', category: '服饰箱包', email: 'merchant@example.com', phone: '13800000000', role: 'user', status: 'active' } })
    if (path === '/api/v1/account') return route.fulfill({ json: { available: 286, frozen: 16, consumed: 98, credited_total: 400 } })
    if (path === '/api/v1/works') {
      workRequests.push(url.search)
      return route.fulfill({ json: Number(url.searchParams.get('page') || 1) > 1 ? { items: Array.from({ length: 10 }, (_, i) => work(i + 10)), next_cursor: null, total: 20, page: 2, page_size: 10 } : { items: Array.from({ length: 10 }, (_, i) => work(i)), next_cursor: 'work-page-2', total: 20, page: 1, page_size: 10 } })
    }
    if (path === '/api/v1/account/ledger') {
      ledgerRequests.push(url.search)
      return route.fulfill({ json: Number(url.searchParams.get('page') || 1) > 1 ? { items: [ledger(99)], next_cursor: null, total: 21, page: 2, page_size: 20 } : { items: Array.from({ length: 20 }, (_, i) => ledger(i)), next_cursor: 'ledger-page-2', total: 21, page: 1, page_size: 20 } })
    }
    return route.fulfill({ json: { items: [], next_cursor: null } })
  })
  await page.goto('/works')
  await expect(page.locator('[data-work-id]')).toHaveCount(10)
  await expect(page.getByRole('button', { name: '继续创作', exact: true })).toHaveCount(0)
  await expect(page.locator('.app-header a[href="/recharge"]')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '我的作品', exact: true })).toHaveCount(0)
  const worksHeading = page.getByRole('group', { name: '作品类型筛选', exact: true })
  const beforeWorks = await worksHeading.boundingBox()
  const worksScroll = page.getByRole('region', { name: '作品列表', exact: true })
  await page.getByRole('button', { name: '下一页', exact: true }).click()
  await expect(page.locator('[data-work-id="work-10"]')).toBeVisible()
  await expect(page.locator('[data-work-id]')).toHaveCount(10)
  expect(await worksHeading.boundingBox()).toEqual(beforeWorks)
  expect(workRequests).toHaveLength(2)
  expect(workRequests[1]).toContain('page=2')
  expect(await page.evaluate(() => ({ top: window.scrollY, overflow: document.documentElement.scrollHeight > innerHeight + 1, horizontal: document.documentElement.scrollWidth > innerWidth }))).toEqual({ top: 0, overflow: false, horizontal: false })
  await worksScroll.evaluate(el => { el.scrollTop = 0 })
  await page.screenshot({ path: info.outputPath('works.png'), fullPage: true })

  await page.getByRole('link', { name: '个人中心', exact: true }).click()
  await expect(page.getByRole('heading', { name: '个人中心', exact: true })).toHaveCount(0)
  const accountHeading = page.locator('.ledger-heading')
  const beforeAccount = await accountHeading.boundingBox()
  const ledgerRegion = page.getByRole('region', { name: '积分流水列表', exact: true })
  await expect(ledgerRegion.getByRole('button', { name: '查看流水 ledger-0', exact: true })).toBeVisible()
  expect(await ledgerRegion.evaluate(el => el.scrollHeight > el.clientHeight)).toBe(true)
  await ledgerRegion.evaluate(el => { el.scrollTop = el.scrollHeight })
  expect(await accountHeading.boundingBox()).toEqual(beforeAccount)
  await page.getByRole('button', { name: '下一页', exact: true }).click()
  await expect(page.getByRole('button', { name: '查看流水 ledger-99', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '查看流水 ledger-0', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '下一页', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: '上一页', exact: true }).click()
  await expect(page.getByRole('button', { name: '查看流水 ledger-0', exact: true })).toBeVisible()
  expect(ledgerRequests).toHaveLength(3)
  expect(await page.evaluate(() => ({ top: window.scrollY, overflow: document.documentElement.scrollHeight > innerHeight + 1, horizontal: document.documentElement.scrollWidth > innerWidth }))).toEqual({ top: 0, overflow: false, horizontal: false })
  await page.screenshot({ path: info.outputPath('account.png'), fullPage: true })
  expect(errors).toEqual([])
})

test('selected tasks stay read-only and regeneration first opens an editable independent draft', async ({ page }, info) => {
  const errors: string[] = [], quotes: any[] = [], submits: any[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => {
    class Events { onopen: (() => void) | null = null; constructor() { queueMicrotask(() => this.onopen?.()) } addEventListener() {} close() {} }
    Object.defineProperty(window, 'EventSource', { value: Events })
  })
  const quote = { credits: 8, agent_version: 'text-agent-v1', spec_id: 'text', spec_version: 'text-agent-v1', price_version: 'p1', input_digest: 'test-only', policy_versions: {} }
  const task = (id: string, hour: number) => ({ task_id: id, state: 'SUCCEEDED', settlement_state: 'CONSUMED', state_version: 1, quote, work_ids: ['work-' + id], created_at: `2026-10-18T0${hour}:00:00Z`, updated_at: `2026-10-18T0${hour}:00:00Z` })
  const tasks = [task('task-newest', 2), task('task-old', 1)]
  const detail = (id: string) => ({ task: tasks.find(item => item.task_id === id)!, conversation_id: 'demo', agent_id: 'text-agent', policy_versions: {}, input: { product_version: 'pv-' + id, product: { name: id === 'task-old' ? '轻量通勤外套' : '针织保暖围巾', product_type: 'clothing', brand: '映作', category: '服饰', fabric: '棉 95%、氨纶 5%', description: '柔软透气，轻便易收纳', sellingPoints: '柔软透气，轻便易收纳', warranty: '支持按实际售后政策处理' }, instruction: id + '原始指令', parameters: { tone: '亲切' }, material_versions: [] } })
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname
    if (path === '/api/v1/me') return route.fulfill({ json: { user_id: 'fixture-task-user', account: 'merchant_demo', nickname: '映作体验店', role: 'user', status: 'active' } })
    if (path === '/api/v1/account') return route.fulfill({ json: { available: 286, frozen: 0, consumed: 16 } })
    if (path === '/api/v1/agents') return route.fulfill({ json: [{ agent_id: 'text-agent', kind: 'copy', name: '文案', version: 'text-agent-v1', protocol_version: 'text-agent-v1', enabled: true, input_support: { product_required_fields: ['name'], min_materials: 0, max_materials: 3, instruction_required: false } }] })
    if (path === '/api/v1/conversations' && request.method() === 'POST') return route.fulfill({ json: { conversation_id: request.postDataJSON().title === '新任务' ? 'new-empty' : 'new-draft', title: '新任务', created_at: '2026-10-18T03:00:00Z' } })
    if (path.startsWith('/api/v1/conversations/')) return route.fulfill({ json: {} })
    if (path.includes('/products/')) return route.fulfill({ json: { product_id: 'product', version: path.split('/').at(-1), product: { name: '版本接口的另一份资料' }, created_at: '2026-10-18T00:00:00Z' } })
    if (path === '/api/v1/quotes') { quotes.push(request.postDataJSON()); return route.fulfill({ json: quote }) }
    if (path === '/api/v1/tasks') {
      if (request.method() === 'POST') submits.push(request.postDataJSON())
      return route.fulfill({ json: { items: url.searchParams.get('conversation_id')?.startsWith('new-') ? [] : tasks, next_cursor: null } })
    }
    if (path.startsWith('/api/v1/tasks/')) return route.fulfill({ json: detail(path.split('/').at(-1)!) })
    if (path.startsWith('/api/v1/works/')) {
      const id = path.split('/').at(-1)!.replace('work-', ''), source = detail(id)
      return route.fulfill({ json: { work_id: 'work-' + id, task_id: id, conversation_id: 'demo', kind: 'copy', created_at: source.task.created_at, items: [{ file_id: 'file-' + id, text: '轻装出发，从容通勤。\n柔软面料贴合日常，简洁剪裁留住自在。\n以商品的真实特点，表达每一次轻松出行。' }], source: { ...source, input: source.input, materials: [], ledger_ids: [], credit_reservation_id: 'reservation' } } })
    }
    return route.fulfill({ json: { items: [], next_cursor: null } })
  })
  await page.goto('/workspace/demo?task=task-old')
  await expect(page.locator('.product-details')).toContainText('轻量通勤外套')
  await expect(page.locator('.product-details')).not.toContainText('版本接口的另一份资料')
  await expect(page.locator('.product-details dt').filter({ hasText: '商品卖点与说明' })).toHaveCount(1)
  await expect(page.locator('.product-details dt').filter({ hasText: '历史核心卖点' })).toHaveCount(0)
  await expect(page.locator('.shell-sidebar a[href="/works"]')).toHaveCount(0)
  await expect(page.getByLabel('创作指令', { exact: true })).toHaveValue('task-old原始指令')
  await expect(page.getByLabel('创作指令', { exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: '文案', exact: true })).toBeDisabled()
  await expect(page.locator('.task-footer')).toContainText('本次费用 8 积分')
  await page.getByRole('button', { name: '基于此任务再生成', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace\/new-draft$/)
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByLabel('创作指令', { exact: true })).toBeEnabled()
  await expect(page.getByLabel('创作指令', { exact: true })).toHaveValue('task-old原始指令')
  await expect(page.locator('.product-details')).toContainText('轻量通勤外套')
  expect(submits).toHaveLength(0)
  await page.getByLabel('创作指令', { exact: true }).fill('独立草稿的新要求')
  await page.getByRole('button', { name: '确认费用并生成', exact: true }).click()
  const confirmation = page.getByRole('dialog', { name: '重新生成 · 再次收费', exact: true })
  await expect(confirmation).toBeVisible()
  expect(quotes.at(-1).input.product.name).toBe('轻量通勤外套')
  expect(quotes.at(-1).input.instruction).toBe('独立草稿的新要求')
  await page.keyboard.press('Escape'); await expect(confirmation).toBeVisible()
  await confirmation.getByRole('button', { name: '取消', exact: true }).click()
  expect(submits).toHaveLength(0)
  const selectTask = async (id: string) => {
    if (info.project.name === 'mobile') await selectOption(page.getByRole('combobox', { name: '最近任务', exact: true }), id)
    else await page.locator(`.task-history-item[href="/workspace/demo?task=${id}"]`).click()
  }
  await selectTask('task-newest')
  await expect(page.locator('.product-details')).toContainText('针织保暖围巾')
  await expect(page.getByLabel('创作指令', { exact: true })).toBeDisabled()
  await selectTask('task-old'); await expect(page.getByLabel('创作指令', { exact: true })).toHaveValue('task-old原始指令')
  await selectTask('task-newest'); await expect(page.getByLabel('创作指令', { exact: true })).toHaveValue('task-newest原始指令')
  await page.screenshot({ path: info.outputPath('workspace.png'), fullPage: true })
  await page.getByRole('button', { name: '新建任务', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace\/new-empty$/)
  await expect(page.getByRole('button', { name: '文案', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('button', { name: '确认费用并生成', exact: true })).toBeVisible()
  expect(errors).toEqual([])
})
