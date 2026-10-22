import { expect, test } from '@playwright/test'
import { readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { randomUUID } from 'node:crypto'

test('UI ledger follows stable server cursor across new entries and opens owner task source', async ({ page, browser }, info) => {
  test.setTimeout(120000)
  const root = process.env.BROWSER_RUNTIME_DIR!
  const meta = JSON.parse(await readFile(resolve(root, 'metadata.json'), 'utf8'))
  const control = JSON.parse(await readFile(resolve(root, 'control.json'), 'utf8'))
  const command = async (path: string, body: object) => {
    const r = await fetch(control.url + path, { method: 'POST', headers: { Authorization: control.token, 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    expect(r.status).toBe(200); return r.json()
  }
  await page.goto('/register')
  await page.getByLabel('账号', { exact: true }).fill(meta.account_prefix + 'ledger_' + randomUUID().slice(0, 8))
  await page.getByLabel('密码', { exact: true }).fill('TEST_ONLY_ledger_password')
  await page.getByLabel('确认密码', { exact: true }).fill('TEST_ONLY_ledger_password')
  await page.getByRole('button', { name: '创建账号', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  const setup = await page.evaluate(async meta => {
    const c = '/src/api/conversations.ts', q = '/src/api/catalog.ts'
    const conv = await import(c), catalog = await import(q)
    const conversation = await conv.createConversation({ title: 'TEST_ONLY ledger source' })
    const product = await conv.createProductVersion({ product: { name: 'TEST_ONLY ledger cup' } })
    const input = { product_version: product.version, product: product.product, instruction: 'TEST_ONLY ledger source snapshot', parameters: {}, material_versions: [] }
    const confirmed_quote = await catalog.quote({ agent_id: meta.agents.copy, input })
    return { conversation_id: conversation.conversation_id, agent_id: meta.agents.copy, input, confirmed_quote }
  }, meta)
  const submit = () => page.evaluate(async body => { const p = '/src/api/tasks.ts'; return (await (await import(p)).submitTask(crypto.randomUUID(), body)).task.task_id }, setup)
  const ids: string[] = [], persisted: unknown[] = []
  for (let i = 0; i < 11; i++) {
    const id = await submit(); ids.push(id)
    await command('/register', { task_id: id, paused: true })
    let record = await command('/drive', { task_id: id })
    for (let j = 0; j < 3 && record.state !== 'SUCCEEDED'; j++) record = await command('/drive', { task_id: id })
    expect(record.state).toBe('SUCCEEDED'); persisted.push(record)
  }
  await page.getByRole('link', { name: '个人中心', exact: true }).click()
  await expect(page.locator('.ledger-table tbody tr')).toHaveCount(20)
  const original = await page.evaluate(async () => { const p = '/src/api/account.ts'; const api = await import(p); const first = await api.listLedger(); return { first, second: await api.listLedger(first.next_cursor), account: await api.getAccount() } })
  expect(original.first.items).toHaveLength(20)
  expect(original.second.items).toHaveLength(3)
  const newTask = await submit()
  await command('/register', { task_id: newTask, paused: true })
  await page.getByRole('button', { name: '加载更多流水', exact: true }).click()
  await expect(page.locator('.ledger-table tbody tr')).toHaveCount(23)
  const rendered = await page.getByRole('button', { name: /^查看流水 / }).evaluateAll(nodes => nodes.map(n => n.getAttribute('aria-label')!.slice(5)))
  expect(rendered).toEqual([...original.first.items, ...original.second.items].map((x: any) => x.ledger_id))
  expect(new Set(rendered).size).toBe(23)
  const balances = await page.evaluate(async () => { const p = '/src/api/account.ts'; return (await import(p)).getAccount() })
  await expect(page.getByTestId('available')).toHaveText(String(balances.available))
  await expect(page.getByTestId('frozen')).toHaveText(String(balances.frozen))
  await expect(page.getByTestId('consumed')).toHaveText(String(balances.consumed))
  await page.getByRole('button', { name: '查看流水 ' + original.first.items[0].ledger_id }).click()
  await expect(page.getByRole('dialog', { name: '积分流水详情' })).toContainText(original.first.items[0].task_id)
  await page.getByRole('button', { name: '查看来源会话', exact: true }).click()
  await expect(page).toHaveURL(new RegExp('/workspace/' + setup.conversation_id + '$'))
  await expect(page.getByText('TEST_ONLY ledger source snapshot', { exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('ledger-source.png') })
  // A second real account cannot gain content access by writing a client-side role.
  const other = await browser.newContext({ ignoreHTTPSErrors: true })
  const outsider = await other.newPage()
  await outsider.goto('https://127.0.0.1:15173/register')
  await outsider.getByLabel('账号', { exact: true }).fill(meta.account_prefix + 'other_' + randomUUID().slice(0, 8))
  await outsider.getByLabel('密码', { exact: true }).fill('TEST_ONLY_other_password')
  await outsider.getByLabel('确认密码', { exact: true }).fill('TEST_ONLY_other_password')
  await outsider.getByRole('button', { name: '创建账号', exact: true }).click()
  await expect(outsider).toHaveURL(/\/workspace$/)
  const denied = await outsider.evaluate(async id => { localStorage.setItem('role', 'admin'); return (await fetch('/api/v1/tasks/' + id)).status }, ids[0])
  expect(denied).toBe(404)
  await other.close()
  await writeFile(info.outputPath('ledger-pagination.json'), JSON.stringify({ ids, newTask, original, rendered, balances, persisted, denied }, null, 2))
})
