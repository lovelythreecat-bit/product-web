import { expect, test } from '@playwright/test'
import { resolve } from 'node:path'

test('three categories, media connection setup and accessible text model drawer', async ({ page }, info) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  const row = { id: '00000000-0000-4000-8000-000000000001', name: 'TEST_ONLY 文本模型', provider: 'openai_chat', base_url: 'https://models.example/v1', model: 'test-model', supports_images: false, timeout_seconds: 60, temperature: null, max_tokens: null, enabled: true, has_api_key: true, revision: 3, created_at: '2026-10-15T00:00:00Z', updated_at: '2026-10-15T00:00:00Z' }
  await page.route('**/api/v1/admin/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path.includes('/media-agents/') && path.endsWith('/connection')) return route.fulfill({json:{id:null,kind:path.includes('/image/')?'image':'video',base_url:null,revision:0,has_service_key:false,has_management_key:false,default_config_id:null,image_model:null}})
    return route.fulfill({ json: path.endsWith('/text-model-configs') ? { items: [row], next_cursor: null } : path.endsWith('/text-service-connection') ? { base_url: 'http://127.0.0.1:8000', has_service_key: true, revision: 1, updated_at: null } : [] })
  })
  await page.goto('/tests/fixtures/agent-configs.html')
  await expect(page.getByRole('heading', { name: '文本模型配置' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '文本服务接入' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '新增文本 Agent' })).toHaveCount(0)
  for (const name of ['图片', '视频']) {
    await page.getByRole('button', { name, exact: true }).click()
    await expect(page.getByRole('heading', { name: name + '服务连接' })).toBeVisible()
    await expect(page.getByRole('button', { name: '配置服务连接', exact:true })).toBeVisible()
    if(name==='图片')await expect(page.getByRole('button', { name: '配置模型',exact:true })).toBeDisabled()
    else await expect(page.getByRole('button', { name: '声音设置' })).toBeDisabled()
    await expect(page.getByRole('button', { name: '新增文本 Agent' })).toHaveCount(0)
  }
  await page.getByRole('button', { name: '文本', exact: true }).click()
  await expect(page.getByRole('cell', { name: 'TEST_ONLY 文本模型 test-model' })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)
  expect(overflow).toBe(false)
  await page.screenshot({ path: resolve('../docs/verification/screenshots/element-plus-2026-10-16-service-connection-2026-10-15-' + info.project.name + '.png'), fullPage: true })
  await page.getByRole('button', { name: '配置模型', exact: true }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByLabel('配置名称', { exact: true })).toBeFocused()
  await expect(page.getByLabel('替换模型密钥（留空保留原密钥）', { exact: true })).toHaveValue('')
  await page.getByLabel('配置名称', { exact: true }).fill('未保存草稿')
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByLabel('配置名称', { exact: true })).toHaveValue('未保存草稿')
  await page.getByRole('dialog').getByRole('button', { name: '取消', exact: true }).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(page.getByRole('button', { name: '配置模型', exact: true })).toBeFocused()
  expect(errors).toEqual([])
})

test('default text model is explicitly selected and survives a refresh', async ({ page }) => {
  const row = { id: '00000000-0000-4000-8000-000000000001', name: 'TEST_ONLY 文本模型', provider: 'openai_chat', base_url: 'https://models.example/v1', model: 'test-model', supports_images: false, timeout_seconds: 60, temperature: null, max_tokens: null, enabled: true, has_api_key: true, revision: 3 }
  let preference = { model_config_id: null as string | null, revision: 0, connection_revision: 2 }
  const writes: Record<string,unknown>[] = []
  await page.route('**/api/v1/admin/**', async route => {
    const path = new URL(route.request().url()).pathname
    if(path.endsWith('/text-default-model')) {
      if(route.request().method() === 'PATCH') {
        writes.push(route.request().postDataJSON()); preference = {...preference,model_config_id:row.id,revision:1}
      }
      return route.fulfill({json:preference})
    }
    return route.fulfill({json:path.endsWith('/text-model-configs')?{items:[row],next_cursor:null}:path.endsWith('/text-service-connection')?{base_url:'http://127.0.0.1:8000',has_service_key:true,revision:2,updated_at:null}:[]})
  })
  await page.goto('/tests/fixtures/agent-configs.html')
  await page.getByRole('button',{name:'设为默认',exact:true}).click()
  await expect(page.getByRole('heading',{name:'设置默认文本模型',exact:true})).toBeFocused()
  await expect(page.getByLabel('修改原因')).toHaveCount(0)
  await page.getByRole('button',{name:'保存默认模型',exact:true}).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(page.getByText('工作台默认模型',{exact:true})).toBeVisible()
  expect(writes).toEqual([{model_config_id:row.id,expected_revision:0,expected_connection_revision:2}])
  await page.reload()
  await expect(page.getByText('工作台默认模型',{exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'新增文本 Agent'})).toHaveCount(0)
})

test('service connection drawer saves a write-only key and reloads remote models', async ({ page }, info) => {
  const writes: Record<string, unknown>[] = []
  let revision = 0, reads = 0
  await page.route('**/api/v1/admin/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/text-service-connection')) {
      if (route.request().method() === 'PATCH') {
        writes.push(route.request().postDataJSON()); revision++
      }
      return route.fulfill({ json: { base_url: revision ? 'http://127.0.0.1:8000' : null, has_service_key: revision > 0, revision, updated_at: null } })
    }
    if (path.endsWith('/text-model-configs')) { reads++; return route.fulfill({ json: { items: [], next_cursor: null } }) }
    return route.fulfill({ json: [] })
  })
  await page.goto('/tests/fixtures/agent-configs.html')
  await expect(page.getByRole('heading', { name: '服务连接设置' })).toBeVisible()
  const action = page.getByRole('button', { name: '配置服务连接', exact: true })
  await action.click()
  await expect(page.getByLabel('服务地址', { exact: true })).toBeFocused()
  await page.getByLabel('服务地址', { exact: true }).fill('http://127.0.0.1:8000')
  await page.getByLabel('服务访问 Key', { exact: true }).fill('TEST_ONLY_service_key')
  await expect(page.getByLabel('修改原因')).toHaveCount(0)
  await page.getByRole('button', { name: '保存服务连接', exact: true }).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(page.getByText('服务连接已保存。', { exact: true })).toBeVisible()
  await expect.poll(() => reads).toBe(2)
  expect(writes).toHaveLength(1)
  expect(writes[0]).toMatchObject({ expected_revision: 0, service_key: 'TEST_ONLY_service_key' })
  await action.click()
  await expect(page.getByLabel('替换服务访问 Key（留空保留原 Key）', { exact: true })).toHaveValue('')
  await page.getByRole('button', { name: '保存服务连接', exact: true }).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  expect(writes).toHaveLength(2)
  expect(writes[1]).not.toHaveProperty('service_key')
  await action.click()
  await page.screenshot({ path: resolve('../docs/verification/screenshots/element-plus-2026-10-16-service-connection-drawer-2026-10-15-' + info.project.name + '.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.getByRole('dialog').getByRole('button', { name: '取消', exact: true }).click()
  await expect(action).toBeFocused()
})
