import { expect, test } from '@playwright/test'
import { readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { randomUUID } from 'node:crypto'

test('unknown registration response retries original intent; profile failure and validation retain inputs; 401 switches identity', async ({ page, context }, info) => {
  const meta = JSON.parse(await readFile(resolve(process.env.BROWSER_RUNTIME_DIR!, 'metadata.json'), 'utf8'))
  const account = meta.account_prefix + 'retry_' + randomUUID().slice(0, 8)
  const bodies: string[] = []
  let calls = 0
  await page.route('**/api/v1/auth/register', async route => {
    bodies.push(route.request().postData()!)
    calls++
    if (calls === 1) { await route.fetch(); await route.abort('failed') }
    else await route.continue()
  })
  await page.goto('/register')
  await page.getByLabel('账号', { exact: true }).fill(account)
  await page.getByLabel('密码', { exact: true }).fill('TEST_ONLY_retry_password')
  await page.getByLabel('确认密码', { exact: true }).fill('TEST_ONLY_retry_password')
  await page.getByRole('button', { name: '创建账号', exact: true }).click()
  await expect(page.getByText('网络连接失败，请重试。同一次注册重试会沿用原请求。')).toBeVisible()
  await page.getByRole('button', { name: '创建账号', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  expect(calls).toBe(2)
  expect(bodies[1]).toBe(bodies[0])
  const originalKey = JSON.parse(bodies[0]).request_key
  bodies.length = 0
  await page.unroute('**/api/v1/auth/register')
  await page.getByRole('link', { name: '个人中心', exact: true }).click()
  let patchCalls = 0
  page.on('request', r => { if (r.method() === 'PATCH') patchCalls++ })
  await page.getByRole('button', { name: '编辑资料', exact: true }).click()
  await page.getByLabel('昵称', { exact: true }).fill('a'.repeat(81))
  await page.getByLabel('个人简介', { exact: true }).fill('b'.repeat(501))
  await page.getByRole('button', { name: '保存资料', exact: true }).click()
  await expect(page.getByText('昵称须为 1–80 个字符，不能仅为空格。')).toBeVisible()
  await expect(page.getByText('个人简介最多 500 个字符。')).toBeVisible()
  expect(patchCalls).toBe(0)
  await page.getByLabel('昵称', { exact: true }).fill('保留输入')
  await page.getByLabel('个人简介', { exact: true }).fill('失败后这段输入仍然存在')
  await page.route('**/api/v1/me', route => route.request().method() === 'PATCH' ? route.abort('failed') : route.continue())
  await page.getByRole('button', { name: '保存资料', exact: true }).click()
  await expect(page.getByText('保存未完成，输入已保留，请重试。')).toBeVisible()
  await expect(page.getByLabel('昵称', { exact: true })).toHaveValue('保留输入')
  await expect(page.getByLabel('个人简介', { exact: true })).toHaveValue('失败后这段输入仍然存在')
  await page.unroute('**/api/v1/me')
  await page.getByRole('button', { name: '保存资料', exact: true }).click()
  await expect(page.getByRole('dialog', { name: '编辑个人资料' })).not.toBeVisible()
  const first = await page.evaluate(async () => { const p='/src/api/account.ts', a='/src/api/auth.ts'; return { profile:await(await import(a)).getProfile(), ledger:await(await import(p)).listLedger() } })
  expect(first.ledger.items).toHaveLength(1)
  // An actual server-revoked cookie makes the next UI GET return 401.
  await page.evaluate(async () => { const p='/src/api/auth.ts'; await(await import(p)).logout() })
  await page.getByRole('button', { name: '刷新记录', exact: true }).click()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByText('保留输入', { exact: true })).toHaveCount(0)
  await page.getByLabel('账号', { exact: true }).fill(account)
  await page.getByLabel('密码', { exact: true }).fill('TEST_ONLY_wrong_password')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByText('登录未完成，请检查账号和密码，或稍后重试。')).toBeVisible()
  await expect(page.getByLabel('账号', { exact: true })).toHaveValue(account)
  const accountB = meta.account_prefix + 'new_' + randomUUID().slice(0, 8)
  await page.getByRole('link', { name: '还没有账号？创建账号' }).click()
  await page.getByLabel('账号', { exact: true }).fill(accountB)
  await page.getByLabel('密码', { exact: true }).fill('TEST_ONLY_new_password')
  await page.getByLabel('确认密码', { exact: true }).fill('TEST_ONLY_new_password')
  await page.getByRole('button', { name: '创建账号', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  await page.getByRole('link', { name: '个人中心', exact: true }).click()
  await expect(page.getByTestId('profile-nickname')).toHaveText('尚未设置昵称')
  await expect(page.getByRole('button', { name: '查看流水 ' + first.ledger.items[0].ledger_id })).toHaveCount(0)
  const second = await page.evaluate(async () => { const p='/src/api/account.ts', a='/src/api/auth.ts'; return { profile:await(await import(a)).getProfile(), ledger:await(await import(p)).listLedger() } })
  expect(second.profile.user_id).not.toBe(first.profile.user_id)
  await writeFile(info.outputPath('retry-isolation.json'), JSON.stringify({ account, accountB, originalKey, calls, first, second, patchCalls }, null, 2))
})
