import { expect, test } from '@playwright/test'
import { resolve } from 'node:path'

test('missing video management key keeps the connection editable and recovers after saving', async ({ page }, info) => {
  let repaired = false
  const writes: Record<string, unknown>[] = []
  await page.route('**/api/v1/admin/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname
    if (path.endsWith('/video/connection')) {
      if (request.method() === 'PATCH') { writes.push(request.postDataJSON()); repaired = true }
      return route.fulfill({ json: { id: 'c1', kind: 'video', revision: repaired ? 2 : 1,
        base_url: 'https://video.example', has_service_key: true, has_management_key: repaired } })
    }
    if (path.endsWith('/video/models')) {
      if (!repaired) return route.fulfill({ status: 503, json: { error: {
        code: 'MEDIA_SERVICE_UNAVAILABLE', message: '媒体服务拒绝管理操作，请在服务连接中配置有效的管理 Key。', retryable: true,
      } } })
      return route.fulfill({ json: { revision: 2, configuration_revision: 1,
        models: { planner: null, video: null, visual: null }, bindings: {} } })
    }
    if (path.endsWith('/settings')) return route.fulfill({ json: { mode: 'fake' } })
    return route.fulfill({ json: [] })
  })
  await page.goto('/tests/fixtures/agent-configs.html')
  await page.getByRole('button', { name: '视频', exact: true }).click()
  await expect(page.getByText('https://video.example', { exact: false })).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('管理 Key')
  await page.screenshot({ path: resolve('../docs/verification/screenshots/video-integration-recovery-2026-10-17-' + info.project.name + '.png'), fullPage: true })
  await page.getByRole('button', { name: '配置服务连接', exact: true }).click()
  await expect(page.getByLabel('服务地址', { exact: true })).toHaveValue('https://video.example')
  await page.getByLabel('管理访问 Key（留空保留）', { exact: true }).fill('TEST_ONLY_admin')
  await page.getByRole('button', { name: '保存服务连接', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '分镜文本模型', exact: true })).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
  expect(writes).toEqual([{ expected_revision: 1, base_url: 'https://video.example', management_key: 'TEST_ONLY_admin' }])
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
})
