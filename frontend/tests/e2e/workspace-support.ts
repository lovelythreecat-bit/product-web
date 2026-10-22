import { selectOption } from './ui-controls'
import { expect, type Page } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
export const png = 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAACXBIWXMAAAABAAAAAQBPJcTWAAAAPElEQVR4nO3RQQ0AMAgEwSOpu2qpPuxVwvLhtyPgSJbqd7PprK7HAwP+AJkImQiZCJkImQiZCJkImSjkA2iaAe2JlpYoAAAAAElFTkSuQmCC'
export async function runtime() {
  const root = process.env.BROWSER_RUNTIME_DIR!
  const meta = JSON.parse(await readFile(resolve(root, 'metadata.json'), 'utf8'))
  const control = JSON.parse(await readFile(resolve(root, 'control.json'), 'utf8'))
  const command = async (path: string, body: object) => { const r = await fetch(control.url + path, { method: 'POST', headers: { Authorization: control.token, 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); expect(r.status, await r.clone().text()).toBe(200); return r.json() }
  return { meta, command }
}
export async function registerUI(page: Page, prefix: string) {
  await page.goto('/register')
  await page.getByLabel('账号', { exact: true }).fill(prefix + crypto.randomUUID().slice(0, 8))
  await page.getByLabel('密码', { exact: true }).fill('TEST_ONLY_browser_password')
  await page.getByLabel('确认密码', { exact: true }).fill('TEST_ONLY_browser_password')
  await page.getByRole('button', { name: '创建账号', exact: true }).click()
  await expect(page.getByRole('heading', { name: '创作工作台' })).toBeVisible()
}
export async function chooseAgentUI(page: Page, agentId: string, kind: string) {
  const label = ({ copy: '文案', image: '图片', video: '视频' } as Record<string, string>)[kind]
  await page.getByRole('group', { name: '创作类型', exact: true }).getByRole('button', { name: label, exact: true }).click()
  const choices = page.getByLabel('选择 Agent', { exact: true })
  if (await choices.isVisible()) await selectOption(choices, agentId)
}
export async function productUI(page: Page, name = '真实流程马克杯') {
  await page.getByRole('button', { name: /^(填写资料|编辑资料)$/ }).click()
  await page.getByLabel('商品名称', { exact: true }).fill(name)
  await selectOption(page.getByLabel('商品类型', { exact: false }), 'home')
  await page.getByLabel('核心卖点', { exact: true }).fill('350ml，奶油白釉面')
  await page.getByRole('button', { name: '保存商品资料' }).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
}
export async function uploadUI(page: Page) { await page.getByLabel('上传商品图片').setInputFiles({ name: 'TEST_ONLY-cup.png', mimeType: 'image/png', buffer: Buffer.from(png, 'base64') }); await expect(page.locator('.material-row img')).toHaveCount(1) }
export async function newConversationUI(page: Page) {
  const previous = page.url()
  await page.getByRole('button', { name: '新建会话', exact: true }).click()
  await expect(page).not.toHaveURL(previous)
  await expect(page.locator('[data-task-id]')).toHaveCount(0)
}
export async function confirmUI(page: Page, credits: number) {
  await page.getByRole('button', { name: '确认费用并生成', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: /^(确认本次生成|重新生成 · 再次收费)$/ })
  await expect(dialog.getByRole('button', { name: '取消', exact: true })).toBeFocused()
  await expect(dialog).toContainText(credits + ' 积分')
  return dialog
}
export async function account(page: Page) { return page.evaluate(async () => { const p = '/src/api/account.ts'; const api = await import(p); return { account: await api.getAccount(), ledger: await api.listLedger() } }) }
export async function taskDetail(page: Page, id: string) { return page.evaluate(async id => { const p = '/src/api/tasks.ts'; return (await import(p)).getTask(id) }, id) }
