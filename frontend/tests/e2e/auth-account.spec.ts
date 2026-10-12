import { expect, test } from '@playwright/test'
import { readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { randomUUID } from 'node:crypto'

test('real UI registration profile persistence cancel recharge and logout isolation', async ({ page, context }, info) => {
  const metadata = JSON.parse(await readFile(resolve(process.env.BROWSER_RUNTIME_DIR!, 'metadata.json'), 'utf8'))
  const account = metadata.account_prefix + 'ui_' + randomUUID().slice(0, 8)
  const password = 'TEST_ONLY_ui_password'
  const mutations: string[] = []
  page.on('request', r => { if (r.url().includes('/api/v1/') && r.method() !== 'GET') mutations.push(r.method() + ' ' + new URL(r.url()).pathname) })
  await page.goto('/register')
  await page.getByLabel('账号', { exact: true }).fill(account)
  await page.getByLabel('密码', { exact: true }).fill(password)
  await page.getByRole('button', { name: '创建账号', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  await page.getByRole('link', { name: '个人中心', exact: true }).click()
  await expect(page.getByRole('heading', { name: '个人中心', exact: true })).toBeVisible()
  const initial = await page.evaluate(async () => {
    const a = '/src/api/account.ts', p = '/src/api/auth.ts'
    return { profile: await (await import(p)).getProfile(), account: await (await import(a)).getAccount(), ledger: await (await import(a)).listLedger(), tasks: await (await fetch('/api/v1/tasks')).json() }
  })
  await expect(page.getByTestId('available')).toHaveText(String(initial.account.available))
  await expect(page.getByTestId('frozen')).toHaveText(String(initial.account.frozen))
  await expect(page.getByTestId('consumed')).toHaveText(String(initial.account.consumed))
  const edit = page.getByRole('button', { name: '编辑资料', exact: true })
  await edit.click()
  await page.getByLabel('昵称', { exact: true }).fill('昵'.repeat(80))
  await page.getByLabel('个人简介', { exact: true }).fill('介'.repeat(500))
  await page.getByRole('button', { name: '保存资料', exact: true }).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(edit).toBeFocused()
  await page.reload()
  await expect(page.getByTestId('profile-nickname')).toHaveText('昵'.repeat(80))
  await expect(page.getByTestId('profile-bio')).toHaveText('介'.repeat(500))
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('account.png'), fullPage: true })
  const patches = mutations.filter(x => x === 'PATCH /api/v1/me').length
  for (const escape of [false, true]) {
    await edit.click()
    await page.getByLabel('昵称', { exact: true }).fill('不保存')
    if (escape) await page.keyboard.press('Escape')
    else await page.getByRole('button', { name: '取消', exact: true }).click()
    await expect(edit).toBeFocused()
  }
  expect(mutations.filter(x => x === 'PATCH /api/v1/me')).toHaveLength(patches)
  const beforeRecharge = mutations.length
  for (const source of ['account', 'header']) {
    await page.getByTestId(source + '-recharge').click()
    await expect(page.getByRole('heading', { name: '充值说明' })).toBeVisible()
    await expect(page.getByText('首版尚未开通真实充值')).toBeVisible()
    await page.getByRole('link', { name: '个人中心', exact: true }).click()
  }
  expect(mutations).toHaveLength(beforeRecharge)
  const final = await page.evaluate(async () => {
    const p = '/src/api/account.ts'; const a = await import(p)
    return { account: await a.getAccount(), ledger: await a.listLedger(), tasks: await (await fetch('/api/v1/tasks')).json() }
  })
  expect(final.account).toEqual(initial.account)
  expect(final.ledger).toEqual(initial.ledger)
  expect(final.tasks).toEqual(initial.tasks)
  expect(final.tasks.items).toHaveLength(0)
  const cookie = (await context.cookies()).find(c => c.name === 'session')!
  expect(cookie).toMatchObject({ secure: true, httpOnly: true, sameSite: 'Lax' })
  const stored = await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }))
  expect(stored).not.toContain(password)
  await page.getByRole('button', { name: '退出登录', exact: true }).click()
  await expect(page).toHaveURL(/\/login$/)
  await page.goto('/account')
  await expect(page).toHaveURL(/\/login$/)
  await page.getByLabel('账号', { exact: true }).fill(account)
  await page.getByLabel('密码', { exact: true }).fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  await page.getByRole('link', { name: '个人中心', exact: true }).click()
  await expect(page.getByTestId('profile-nickname')).toHaveText('昵'.repeat(80))
  await writeFile(info.outputPath('auth-account-evidence.json'), JSON.stringify({ account, initial, final, mutations, cookie: { secure: cookie.secure, httpOnly: cookie.httpOnly, sameSite: cookie.sameSite } }, null, 2))
})
