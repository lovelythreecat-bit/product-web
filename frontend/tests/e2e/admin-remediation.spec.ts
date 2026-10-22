import { test, expect } from '@playwright/test'
import { resolve } from 'node:path'

const at = '2026-10-17T00:00:00Z'
const balances = { available: 100, frozen: 8, consumed: 20 }
const user = (id: string) => ({ id, account_normalized: '商家_' + id, nickname: '店主', role: id === 'admin' ? 'admin' : 'user', status: 'active', auth_version: 0, profile_version: '0'.repeat(64), created_at: at, shop_name: '家居生活馆', category: '家居', email: null, phone: null, last_login_at: at, task_count: 3, ...balances })
const ledger = (id: string) => ({ ledger_id: id, user_id: 'u1', account: '商家_u1', operator: 'admin', kind: 'admin_grant', amount: 10, task_id: null, grant_id: id, reservation_id: null, reason: '测试积分', created_at: at, balances_before: balances, balances_after: { ...balances, available: 110 } })
const task = (id: string) => ({ id, user_id: 'u1', account: '商家_u1', state: 'SUCCEEDED', settlement_state: 'CONSUMED', state_version: 1, agent_id: 'text-agent', agent_version: 'v1', elapsed_seconds: 3, fixed_credits: 8, price_version: 'p1', diagnostic_code: null, investigation_status: null, investigation_owner: null, investigation_deadline: null, created_at: at, updated_at: at, work_ids: [], timeline: [] })

test('admin pagination keeps the shell, filters and footer fixed on all four list pages', async ({ page }, info) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url()), path = url.pathname
    const second = Number(url.searchParams.get('page') || 1) > 1
    const makePage = (make: (id: string) => unknown) => ({ items: second ? [make('page-2')] : Array.from({ length: 20 }, (_, i) => make('row-' + i)), next_cursor: second ? null : 'next-page', total: 21, page: second ? 2 : 1, page_size: 20 })
    if (path === '/api/v1/me') return route.fulfill({ json: { user_id: 'admin', account: '测试管理员', role: 'admin', status: 'active' } })
    if (path === '/api/v1/account') return route.fulfill({ json: { ...balances, credited_total: 128 } })
    if (path.endsWith('/agents')) return route.fulfill({ json: [{ agent_id: 'text-agent', version: 'v1', name: '文案 Agent', kind: 'copy', enabled: true }] })
    if (path.endsWith('/tasks')) return route.fulfill({ json: makePage(task) })
    if (path.endsWith('/managed-users') || path.endsWith('/users')) return route.fulfill({ json: makePage(user) })
    if (path.endsWith('/ledger')) return route.fulfill({ json: makePage(ledger) })
    if (path.endsWith('/audit')) return route.fulfill({ json: makePage(id => ({ id, action: 'admin_credit_grant', actor_id: 'admin', object_id: id, reason: '测试操作', created_at: at, changes: { amount: 10 } })) })
    return route.fulfill({ json: { items: [], next_cursor: null } })
  })
  for (const [route, title] of [['tasks', '任务与异常'], ['users', '用户管理'], ['credits', '积分管理'], ['logs', '操作日志']]) {
    await page.goto('/admin/' + route)
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible()
    await expect(page.locator('.admin-list-table .el-table__body-wrapper tbody tr')).toHaveCount(20)
    await expect(page.getByRole('link', { name: '官网内容', exact: true })).toHaveCount(0)
    await expect(page.getByRole('link', { name: '运营总览', exact: true })).toBeVisible()
    const pagination = page.locator('.admin-pagination')
    await expect(pagination).toBeVisible()
    const before = await pagination.boundingBox()
    const dimensions = await page.evaluate(() => {
      const elements = ['html', 'body', '.app-shell', '.shell-body', '#main-content', '.admin-list-page', '.admin-list-panel']
      return elements.map(selector => { const node = document.querySelector<HTMLElement>(selector)!; return { selector, client: node.clientHeight, scroll: node.scrollHeight, width: node.scrollWidth, box: node.clientWidth } })
    })
    for (const node of dimensions) {
      expect(node.scroll, JSON.stringify(node)).toBeLessThanOrEqual(node.client + 2)
      expect(node.width, JSON.stringify(node)).toBeLessThanOrEqual(node.box + 2)
    }
    const scroller = page.locator('.admin-list-table .el-scrollbar__wrap').first()
    expect(await scroller.evaluate(el => el.scrollHeight > el.clientHeight && el.clientHeight > 60)).toBe(true)
    await scroller.evaluate(el => { el.scrollTop = 300 })
    expect(await scroller.evaluate(el => el.scrollTop)).toBeGreaterThan(0)
    expect((await pagination.boundingBox())!.y).toBe(before!.y)
    await pagination.getByRole('button', { name: '下一页', exact: true }).click()
    await expect(page.locator('.admin-list-table .el-table__body-wrapper tbody tr')).toHaveCount(1)
    await expect(pagination).toContainText('2')
    await pagination.getByRole('button', { name: '上一页', exact: true }).click()
    await expect(page.locator('.admin-list-table .el-table__body-wrapper tbody tr')).toHaveCount(20)
    await page.screenshot({ path: resolve('../.agent-runs/admin-remediation-2026-10-17/evidence/' + route + '-' + info.project.name + '.png') })
  }
  expect(errors).toEqual([])
})

test('user actions separate information, paged ledger, editing, password and signed credit adjustment', async ({ page }, info) => {
  const errors: string[] = [], writes: { method: string; path: string; body: any }[] = []
  page.on('pageerror', error => errors.push(error.message))
  let merchant = user('u1'), removed = false
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname
    if (path === '/api/v1/me') return route.fulfill({ json: { user_id: 'admin', account: '测试管理员', role: 'admin', status: 'active' } })
    if (path === '/api/v1/account') return route.fulfill({ json: { ...balances, credited_total: 128 } })
    if (request.method() !== 'GET') {
      const body = request.postDataJSON()
      writes.push({ method: request.method(), path, body })
      if (path.endsWith('/credit-adjustments')) { merchant.available += body.delta; return route.fulfill({ json: { ...body, user_id: 'u1', actor_id: 'admin', ledger_id: 'adjustment' } }) }
      if (path.endsWith('/password-reset')) { merchant.auth_version++; return route.fulfill({ json: merchant }) }
      if (request.method() === 'DELETE') { removed = true; return route.fulfill({ status: 204 }) }
      merchant = { ...merchant, ...body, account_normalized: body.account, auth_version: merchant.auth_version + 1 }
      return route.fulfill({ json: merchant })
    }
    if (path.endsWith('/managed-users') || path.endsWith('/users')) return route.fulfill({ json: { items: removed ? [user('admin')] : [merchant, user('admin')], next_cursor: null, total: removed ? 1 : 2, page: 1, page_size: 20 } })
    if (path.endsWith('/ledger')) return route.fulfill({ json: { items: Number(url.searchParams.get('page') || 1) > 1 ? [ledger('second-ledger')] : Array.from({ length: 20 }, (_, i) => ledger('entry-' + i)), next_cursor: Number(url.searchParams.get('page') || 1) > 1 ? null : 'ledger-next', total: 21, page: Number(url.searchParams.get('page') || 1), page_size: 20 } })
    if (path.includes('/managed-users/')) return route.fulfill({ json: merchant })
    return route.fulfill({ json: { items: [], next_cursor: null } })
  })
  await page.goto('/admin/users')
  const rows = page.locator('.admin-list-table .el-table__body-wrapper tbody tr')
  await expect(rows).toHaveCount(2)
  await expect(rows.nth(1).getByRole('button', { name: '删除', exact: true })).toBeDisabled()
  await rows.first().getByRole('button', { name: '查看', exact: true }).click()
  let dialog = page.getByRole('dialog', { name: '用户信息', exact: true })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByText('家居生活馆', { exact: true })).toBeVisible()
  await expect(dialog.getByRole('button', { name: /积分调整|编辑|重置密码/ })).toHaveCount(0)
  await dialog.locator('.overlay-actions').getByRole('button', { name: '关闭', exact: true }).click()

  await rows.first().getByRole('button', { name: '积分流水', exact: true }).click()
  dialog = page.getByRole('dialog', { name: '积分流水 · 商家_u1', exact: true })
  await expect(dialog.locator('.el-table__body-wrapper tbody tr')).toHaveCount(20)
  const ledgerScroll = dialog.locator('.el-scrollbar__wrap').first()
  expect(await ledgerScroll.evaluate(el => el.scrollHeight > el.clientHeight && el.clientHeight > 60)).toBe(true)
  expect(await dialog.locator('.overlay-content').evaluate(el => el.scrollHeight <= el.clientHeight + 2)).toBe(true)
  await dialog.locator('.overlay-actions').getByRole('button', { name: '下一页', exact: true }).hover()
  const footerBefore = await dialog.locator('.overlay-actions').boundingBox()
  await ledgerScroll.evaluate(el => { el.scrollTop = 240 })
  expect((await dialog.locator('.overlay-actions').boundingBox())!.y).toBe(footerBefore!.y)
  await dialog.getByRole('button', { name: '下一页', exact: true }).click()
  await expect(dialog.locator('.el-table__body-wrapper tbody tr')).toHaveCount(1)
  await page.screenshot({ path: resolve('../.agent-runs/admin-remediation-2026-10-17/evidence/user-ledger-' + info.project.name + '.png') })
  await dialog.locator('.overlay-actions').getByRole('button', { name: '关闭', exact: true }).click()

  await rows.first().getByRole('button', { name: '编辑', exact: true }).click()
  dialog = page.getByRole('dialog', { name: '编辑用户', exact: true })
  await dialog.getByLabel('昵称', { exact: true }).fill('新的昵称')
  await dialog.getByLabel('操作原因', { exact: true }).fill('核对资料后修改')
  await dialog.getByRole('button', { name: '保存', exact: true }).click()
  await expect(dialog).not.toBeVisible()
  await expect(rows.first()).toContainText('新的昵称')

  await rows.first().getByRole('button', { name: '重置密码', exact: true }).click()
  dialog = page.getByRole('dialog', { name: '重置密码', exact: true })
  await dialog.getByLabel('新密码', { exact: true }).fill('TestOnly_newPassword17')
  await dialog.getByLabel('确认新密码', { exact: true }).fill('TestOnly_newPassword17')
  await dialog.getByLabel('重置原因', { exact: true }).fill('核验账户后重置')
  await dialog.getByRole('button', { name: '确认重置', exact: true }).click()
  await expect(dialog).not.toBeVisible()

  await rows.first().getByRole('button', { name: '积分调整', exact: true }).click()
  dialog = page.getByRole('dialog', { name: '积分调整', exact: true })
  await dialog.getByLabel('调整积分', { exact: true }).fill('-5')
  await dialog.getByLabel('调整原因', { exact: true }).fill('测试扣减')
  await dialog.getByRole('button', { name: '继续', exact: true }).click()
  const confirmation = page.getByRole('dialog', { name: '确认积分调整', exact: true })
  await expect(confirmation.getByRole('button', { name: '取消', exact: true })).toBeFocused()
  await confirmation.getByRole('button', { name: '确认调整', exact: true }).click()
  await expect(confirmation).not.toBeVisible()
  expect(writes.find(write => write.path.endsWith('/credit-adjustments'))!.body.delta).toBe(-5)

  await rows.first().getByRole('button', { name: '删除', exact: true }).click()
  dialog = page.getByRole('dialog', { name: '删除用户', exact: true })
  await expect(dialog.getByRole('button', { name: '取消', exact: true })).toBeFocused()
  await dialog.getByLabel('删除原因', { exact: true }).fill('测试删除')
  await dialog.getByRole('button', { name: '确认删除', exact: true }).click()
  await expect(rows).toHaveCount(1)
  expect(writes.map(write => write.method)).toEqual(['PATCH', 'POST', 'POST', 'DELETE'])
  expect(errors).toEqual([])
})

test('operations overview visualizes real agent breakdowns and switches trend metrics', async ({ page }, info) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/me') return route.fulfill({ json: { user_id: 'admin', account: '测试管理员', role: 'admin', status: 'active' } })
    if (path === '/api/v1/account') return route.fulfill({ json: { ...balances, credited_total: 128 } })
    if (path.endsWith('/agents')) return route.fulfill({ json: ['copy', 'image', 'video'].map((kind, i) => ({ agent_id: kind + '-agent', version: 'v1', name: ['文案 Agent', '图片 Agent', '视频 Agent'][i], kind, enabled: true })) })
    if (path.endsWith('/statistics')) return route.fulfill({ json: {
      generated_count: 120, succeeded_count: 90, terminal_count: 100, success_rate: 0.9, credits_consumed: 800, credits_frozen: 40, credits_released: 60, signup_credits: 1000, admin_granted_credits: 200, unsettled_count: 20, supplier_cost_status: 'unavailable', supplier_usage_status: 'unavailable', payment_revenue_status: 'not_supported', state_counts: { SUCCEEDED: 90, FAILED: 7, MANUALLY_CLOSED: 3, RUNNING: 20 }, trend_days: 14, trend_timezone: 'UTC',
      daily_trend: Array.from({ length: 14 }, (_, i) => ({ date: '2026-10-' + String(i + 4).padStart(2, '0'), task_count: (i * 3) % 12, credits_consumed: (i * 15) % 90 })),
      by_agent: ['copy', 'image', 'video'].map((kind, i) => ({ agent_id: kind + '-agent', task_count: [60, 40, 20][i], succeeded_count: [50, 30, 10][i], failed_count: [3, 2, 2][i], manually_closed_count: 1, terminal_count: [54, 33, 13][i], success_rate: [50 / 54, 30 / 33, 10 / 13][i], unsettled_count: [6, 7, 7][i], credits_consumed: [200, 300, 300][i], credits_frozen: [10, 15, 15][i], credits_released: 20 })),
    } })
    return route.fulfill({ json: { items: [], next_cursor: null } })
  })
  await page.goto('/admin/usage')
  await expect(page.getByRole('heading', { name: '运营总览', exact: true })).toBeVisible()
  await expect(page.getByRole('img', { name: '任务量日趋势，详细数值见每日数据' })).toBeVisible()
  await page.getByRole('button', { name: '消费积分', exact: true }).click()
  await expect(page.getByRole('img', { name: '消费积分日趋势，详细数值见每日数据' })).toBeVisible()
  const dateBoxes = await page.locator('.trend-chart text').evaluateAll(nodes => nodes
    .filter(node => /^\d{2}\/\d{2}$/.test(node.textContent || ''))
    .map(node => { const box = node.getBoundingClientRect(); return { left: box.left, right: box.right } }))
  for (let index = 1; index < dateBoxes.length; index++) expect(dateBoxes[index].left - dateBoxes[index - 1].right).toBeGreaterThanOrEqual(3)
  for (const name of ['文案 Agent', '图片 Agent', '视频 Agent']) await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: resolve('../.agent-runs/admin-remediation-2026-10-17/evidence/usage-' + info.project.name + '.png'), fullPage: true })
  expect(errors).toEqual([])
})
