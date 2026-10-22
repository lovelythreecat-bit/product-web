import { test, expect } from '@playwright/test'
import { resolve } from 'node:path'
import { selectOption } from './ui-controls'

test('tasks show every output, keep input in details, and recover silently', async ({ page }, info) => {
  const errors: string[] = [], posts: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => {
    class Events {
      onopen: (() => void) | null = null
      onerror: (() => void) | null = null
      constructor() { (window as any).taskEvents = this; queueMicrotask(() => this.onopen?.()) }
      addEventListener() {}
      close() {}
    }
    Object.defineProperty(window, 'EventSource', { value: Events })
  })
  const quote = { credits: 8, agent_version: 'a1', spec_id: 'copy', spec_version: 'a1', price_version: 'p1', input_digest: 'fixture', policy_versions: {} }
  const tasks = ['new', 'old'].map((name, index) => ({ task_id: 'task-' + name, display_number: 'T20261017-00000' + (2 - index), state: 'SUCCEEDED', settlement_state: 'CONSUMED', state_version: 2, created_at: `2026-10-17T0${2 - index}:00:00Z`, updated_at: '2026-10-17T02:10:00Z', quote, work_ids: name === 'new' ? ['work-a', 'work-b'] : ['work-old'] }))
  tasks.push({ ...tasks[1], task_id: 'task-image', display_number: 'T20261017-000003', work_ids: ['work-image'] })
  const work = (id: string) => ({ work_id: id, task_id: id === 'work-old' ? 'task-old' : 'task-new', kind: 'copy', display_number: 'W-' + id, items: id === 'work-a' ? [{ file_id: 'a1', text: '第一份完整成果' }, { file_id: 'a2', text: '第二份完整成果' }] : [{ file_id: id, text: id === 'work-old' ? '历史任务的产物' : '第三份完整成果' }], source_snapshot: {}, created_at: '2026-10-17T02:10:00Z' })
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), url = new URL(request.url()), pathname = url.pathname
    if (request.method() === 'POST') posts.push(pathname)
    if (pathname === '/api/v1/me') return route.fulfill({ json: { user_id: 'task-results-user', username: '任务预览', role: 'user', status: 'active' } })
    if (pathname === '/api/v1/account') return route.fulfill({ json: { available: 100, frozen: 0, consumed: 16 } })
    if (pathname === '/api/v1/agents') return route.fulfill({ json: ['copy', 'image'].map(kind => ({ agent_id: kind + '-agent', version: 'a1', protocol_version: 'a1', name: kind === 'copy' ? '文案' : '图片', kind, enabled: true, input_support: { product_required_fields: ['name'], min_materials: 0, max_materials: 3, instruction_required: false } })) })
    if (pathname === '/api/v1/tasks') return route.fulfill({ json: { items: tasks, next_cursor: null } })
    if (pathname.startsWith('/api/v1/tasks/')) {
      const task = tasks.find(task => pathname.endsWith('/' + task.task_id))!
      return route.fulfill({ json: { task, conversation_id: 'demo', agent_id: task.task_id === 'task-image' ? 'image-agent' : 'copy-agent', input: { product_version: 'pv1', product: { name: '陶瓷马克杯', sellingPoints: '只出现在详情的商品卖点' }, instruction: '只出现在详情的创作指令', parameters: { platform: '淘宝', copy_type: '商品介绍' }, material_versions: [] }, policy_versions: { private_policy: 'hidden-v1' } } })
    }
    if (pathname === '/api/v1/works/work-image') return route.fulfill({ json: { ...work('work-image'), kind: 'image', task_id: 'task-image', items: [1, 2, 3].map(index => ({ file_id: 'image-' + index, text: null })) } })
    if (pathname.startsWith('/api/v1/works/')) return route.fulfill({ json: work(pathname.split('/').pop()!) })
    if (pathname.startsWith('/api/v1/files/image-')) return route.fulfill({ path: resolve('public/homepage/commerce-categories-v3.png'), contentType: 'image/png' })
    if (pathname.includes('/products/')) return route.fulfill({ json: { product_id: 'product', version: 'pv1', product: { name: '陶瓷马克杯' } } })
    if (pathname === '/api/v1/quotes') return route.fulfill({ json: quote })
    if (pathname === '/api/v1/conversations') return route.fulfill({ json: { items: [{ conversation_id: 'demo', title: '杯子创作', created_at: '2026-10-17T01:00:00Z' }], next_cursor: null } })
    if (pathname.startsWith('/api/v1/conversations/')) return route.fulfill({ json: {} })
    return route.fulfill({ json: { items: [], next_cursor: null } })
  })
  await page.goto('/workspace/demo?task=task-new')
  const content = page.locator('.task-history')
  await expect(content.getByText('第一份完整成果', { exact: true })).toBeVisible()
  await expect(content.getByText('第二份完整成果', { exact: true })).toBeVisible()
  await expect(content.getByText('第三份完整成果', { exact: true })).toBeVisible()
  await expect(content.getByText('只出现在详情的创作指令', { exact: true })).toHaveCount(0)
  await expect(content.getByText('历史任务的产物', { exact: true })).toHaveCount(0)
  await page.evaluate(() => (window as any).taskEvents.onerror?.())
  await expect(content.getByText('第一份完整成果', { exact: true })).toBeVisible()
  await expect(page.getByText(/正在核对原任务/)).toHaveCount(0)
  await page.screenshot({ path: resolve('../docs/verification/screenshots/task-results-2026-10-17-' + info.project.name + '.png'), fullPage: true })
  const details = content.getByRole('button', { name: '任务详情', exact: true })
  await details.click()
  const drawer = page.getByRole('dialog', { name: '任务详情', exact: true })
  await expect(drawer.getByText('只出现在详情的创作指令', { exact: true })).toBeVisible()
  await expect(drawer.getByText('只出现在详情的商品卖点', { exact: true })).toBeVisible()
  await expect(drawer.getByText('适用政策版本', { exact: true })).toHaveCount(0)
  await page.waitForFunction(() => !document.getAnimations().some(animation => animation.playState === 'running'))
  await page.screenshot({ path: resolve('../docs/verification/screenshots/task-details-2026-10-17-' + info.project.name + '.png') })
  await page.keyboard.press('Escape')
  await expect(drawer).toBeVisible()
  await drawer.locator('.overlay-header button').click()
  await expect(drawer).toHaveCount(0)
  await expect(details).toBeFocused()
  if (info.project.name === 'mobile') await selectOption(page.getByRole('combobox', { name: '最近任务', exact: true }), 'task-old')
  else await page.locator('.task-history-item[href="/workspace/demo?task=task-old"]').click()
  await expect(page).toHaveURL(/task=task-old/)
  await expect(content.getByText('历史任务的产物', { exact: true })).toBeVisible()
  await expect(content.getByText('第一份完整成果', { exact: true })).toHaveCount(0)
  if (info.project.name === 'mobile') await selectOption(page.getByRole('combobox', { name: '最近任务', exact: true }), 'task-image')
  else await page.locator('.task-history-item[href="/workspace/demo?task=task-image"]').click()
  const images = content.locator('.result-item>img')
  await expect(images).toHaveCount(3)
  await expect.poll(() => images.evaluateAll(elements => elements.every(image => (image as HTMLImageElement).complete && (image as HTMLImageElement).naturalWidth > 0))).toBe(true)
  expect(await images.evaluateAll(elements => elements.every(image => getComputedStyle(image).objectFit === 'contain'))).toBe(true)
  await page.screenshot({ path: resolve('../docs/verification/screenshots/task-images-2026-10-17-' + info.project.name + '.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  expect(posts).toEqual([])
  expect(errors).toEqual([])
})
