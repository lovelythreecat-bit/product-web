import { test, expect, type Locator } from '@playwright/test'
import { resolve } from 'node:path'
import { readFile } from 'node:fs/promises'
import { selectOption } from './ui-controls'

async function expectResultColumns(items: Locator, mobile: boolean, layout: 'copy' | 'image' = 'copy') {
  const boxes = await items.evaluateAll(elements => elements.map(element => {
    const { x, y, width } = element.getBoundingClientRect()
    return { x, y, width }
  }))
  expect(boxes.length).toBeGreaterThanOrEqual(2)
  if (mobile) {
    expect(Math.abs(boxes[0]!.x - boxes[1]!.x)).toBeLessThan(2)
    expect(boxes[1]!.y).toBeGreaterThan(boxes[0]!.y)
  } else {
    expect(Math.abs(boxes[0]!.y - boxes[1]!.y)).toBeLessThan(2)
    expect(boxes[1]!.x).toBeGreaterThan(boxes[0]!.x + boxes[0]!.width)
    if (boxes.length === 3) {
      if (layout === 'image') {
        expect(Math.abs(boxes[2]!.y - boxes[0]!.y)).toBeLessThan(2)
        expect(boxes[2]!.x).toBeGreaterThan(boxes[1]!.x + boxes[1]!.width)
        expect(Math.abs(boxes[2]!.width - boxes[0]!.width)).toBeLessThan(2)
      } else {
        expect(boxes[2]!.y).toBeGreaterThan(boxes[0]!.y)
        expect(Math.abs(boxes[2]!.x - boxes[0]!.x)).toBeLessThan(2)
        expect(Math.abs(boxes[2]!.width - boxes[0]!.width)).toBeLessThan(2)
      }
    }
  }
}

test('recent quick tasks restore successful copies, keep originals collapsed and use equal-width copy cards', async ({ page }, info) => {
  const types = ['宣传文案', '商品标题', '短视频脚本']
  const input = { product_version: 'p1', product: { name: 'TEST_ONLY-部分成功商品', product_type: 'home' }, parameters: {}, material_versions: [], instruction: '' }
  const quote = { credits: 10, agent_version: 'v1', spec_id: 'copy', spec_version: 'v1', price_version: 'v1', input_digest: 'TEST_ONLY', policy_versions: {} }
  const copies: any = { run_id: 'TEST_ONLY-copies', conversation_id: 'TEST_ONLY-conversation', title: input.product.name, step: 2, version: 1,
    state: { step: 2, draft: { product_version: 'p1', material_versions: [], copy_parameters: {}, copy_types: types, copy_instruction: '', copy_text: '', copy_texts: { 商品标题: '人工保留标题' }, image_platform: '', image_outputs: [], image_instruction: '', video_first_frame_file_id: '', video_instruction: '' }, confirmed_copy: null, confirmed_images: null, current: { copy: 'copies', image: null, video: null }, pending_batch: null,
      batches: [{ id: 'copies', kind: 'copy', submitted: true, items: types.map((label, i) => ({ label, task_id: 'copy-' + i, request: { input: { ...input, parameters: { copy_type: label } }, confirmed_quote: quote } })) }] },
    tasks: Object.fromEntries(types.map((_, i) => ['copy-' + i, { agent_id: 'copy', conversation_id: 'TEST_ONLY-conversation', input, policy_versions: {}, task: { task_id: 'copy-' + i, state: i === 2 ? 'FAILED' : 'SUCCEEDED', state_version: 1, settlement_state: i === 2 ? 'FROZEN' : 'CONSUMED', work_ids: i === 2 ? [] : ['work-' + i], quote } }])) }
  const empty = { ...copies, run_id: 'TEST_ONLY-new', title: 'TEST_ONLY-空白任务', step: 1, state: { ...copies.state, step: 1, current: { copy: null, image: null, video: null }, batches: [] }, tasks: {} }
  const mutations: string[] = [], errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname
    if (request.method() !== 'GET') mutations.push(path)
    const respond = (json: unknown) => route.fulfill({ json })
    if (path === '/api/v1/me') return respond({ user_id: 'TEST_ONLY-owner', username: '部分成功验证', role: 'user', status: 'active' })
    if (path === '/api/v1/account') return respond({ available: 100, frozen: 10, consumed: 20 })
    if (path === '/api/v1/agents') return respond([])
    if (path === '/api/v1/products/versions/p1') return respond({ version: 'p1', product: input.product })
    if (path === '/api/v1/quick-generation') return respond([empty, copies].map(run => ({ ...run, state: undefined, tasks: undefined })))
    if (path === '/api/v1/quick-generation/TEST_ONLY-new') return respond(empty)
    if (path === '/api/v1/quick-generation/TEST_ONLY-copies') return respond(copies)
    if (path.startsWith('/api/v1/works/')) return respond({ work_id: path.split('/').at(-1), kind: 'copy', items: [{ file_id: 'TEST_ONLY-text', text: '已成功的完整宣传文案' }] })
    return respond({ items: [], next_cursor: null })
  })
  await page.goto('/workspace/quick/TEST_ONLY-new')
  if (info.project.name === 'mobile') await selectOption(page.getByRole('combobox', { name: '最近任务' }), 'quick:' + copies.run_id)
  else await page.locator('.quick-history-item').filter({ hasText: copies.title }).click()
  await expect(page.getByLabel('宣传文案', { exact: true })).toHaveValue('已成功的完整宣传文案')
  await expect(page.getByLabel('商品标题', { exact: true })).toHaveValue('人工保留标题')
  await expect(page.getByLabel('短视频脚本', { exact: true })).toHaveValue('')
  await expect(page.getByRole('button', { name: '确认文案，生成图片', exact: true })).toBeDisabled()
  await expect(page.locator('.quick-stepper').getByRole('button', { name: /图片生成/ })).toBeDisabled()
  await expectResultColumns(page.locator('.quick-copy-grid > .quick-copy-paper'), info.project.name === 'mobile')
  await expect(page.getByText('修改将在确认后用于下一阶段', { exact: true })).toHaveCount(0)
  const toggle = page.getByRole('button', { name: '查看原始任务', exact: true })
  await expect(toggle).toHaveAttribute('aria-expanded', 'false')
  await expect(page.locator('.quick-original .task-card')).toHaveCount(0)
  await page.screenshot({ path: info.outputPath('quick-partial-copies.png'), fullPage: true })
  await toggle.click()
  await expect(page.locator('.quick-original .task-card')).toHaveCount(3)
  await expect(page.getByRole('button', { name: '重试', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '收起原始任务', exact: true }).click()
  await expect(page.locator('.quick-original .task-card')).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.locator('.quick-stepper').getByRole('button', { name: /商品确认/ }).click()
  await expect(page.locator('.quick-stepper [aria-current="step"]')).toContainText('商品确认')
  await page.locator('.quick-footer').getByRole('button', { name: '下一步', exact: true }).click()
  await expect(page.getByLabel('宣传文案', { exact: true })).toHaveValue('已成功的完整宣传文案')
  await page.getByRole('button', { name: '保存并退出', exact: true }).click()
  await expect(page).toHaveURL(/\/works$/)
  expect(mutations).toEqual([])
  expect(errors).toEqual([])
})

test('workspace defaults to quick creation and switches matching history without an intermediate page', async ({ page }, info) => {
  const mutations: string[] = [], errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  const draft = { product_version: null, material_versions: [], copy_parameters: {}, copy_types: [], copy_instruction: '', copy_text: '', copy_texts: {}, image_platform: '', image_outputs: [], image_instruction: '', video_first_frame_file_id: '', video_instruction: '' }
  const run = (runId: string) => ({ run_id: runId, conversation_id: 'TEST_ONLY-conversation', title: 'TEST_ONLY-入口导航', version: 1, step: 1, state: { step: 1, draft, confirmed_copy: null, confirmed_images: null, current: { copy: null, image: null, video: null }, pending_batch: null, batches: [] }, tasks: {} })
  await page.route('**/api/v1/**', async route => {
    const req = route.request(), path = new URL(req.url()).pathname
    const respond = (json: unknown) => route.fulfill({ json })
    if (req.method() !== 'GET') mutations.push(req.method() + ' ' + path)
    if (path === '/api/v1/me') return respond({ user_id: 'TEST_ONLY-owner', username: '入口验证', role: 'user', status: 'active' })
    if (path === '/api/v1/account') return respond({ available: 100, frozen: 0, consumed: 0 })
    if (path === '/api/v1/agents') return respond([])
    if (path === '/api/v1/quick-generation') {
      if (req.method() === 'POST') return respond(run(req.postDataJSON().run_id))
      return respond([{ ...run('TEST_ONLY-saved'), state: undefined, tasks: undefined }])
    }
    if (path.startsWith('/api/v1/quick-generation/')) return respond(run(path.split('/').pop()!))
    return respond({ items: [], next_cursor: null })
  })
  await page.goto('/workspace')
  await expect(page).toHaveURL(/\/workspace\/quick\/TEST_ONLY-saved$/)
  await expect(page.locator('.quick-stepper [aria-current="step"]')).toContainText('商品确认')
  await expect(page.locator('.quick-intro')).toHaveCount(0)
  const modes = page.getByRole('navigation', { name: '工作台模式', exact: true })
  await expect(modes.getByRole('link', { name: '快速生成', exact: true })).toHaveAttribute('aria-current', 'page')
  await expect(page.locator('.quick-entry')).toHaveCount(0)
  await expect(page.locator('.quick-history-item')).toHaveCount(1)
  await modes.getByRole('link', { name: '专业工作台', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace\/ordinary$/)
  await expect(page.getByRole('region', { name: '创作配置', exact: true })).toBeVisible()
  await expect(page.locator('.quick-history-item')).toHaveCount(0)
  await expect(modes.getByRole('link', { name: '专业工作台', exact: true })).toHaveAttribute('aria-current', 'page')
  await expect(page.getByLabel('创作指令', { exact: true })).toHaveCount(0)
  await modes.getByRole('link', { name: '快速生成', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace\/quick\/TEST_ONLY-saved$/)
  await page.getByRole('button', { name: '新建快速生成', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace\/quick\/[\da-f-]+$/)
  await expect(page.locator('.quick-stepper [aria-current="step"]')).toContainText('商品确认')
  await page.screenshot({ path: info.outputPath('workspace-modes.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.getByRole('button', { name: '保存并退出', exact: true }).click()
  await expect(page).toHaveURL(/\/works$/)
  expect(mutations).toEqual(['POST /api/v1/quick-generation'])
  expect(errors).toEqual([])
})

test('quick generation keeps explicit confirmations, five images, plan review and saved progress', async ({ page }, info) => {
  const errors: string[] = [], submissions: any[] = [], assists: any[] = [], stageMutations: string[] = [], preparations: any[] = [], productSaves: any[] = []
  page.on('pageerror', error => errors.push(error.message))
  const photo = await readFile(resolve('../docs/design/quick-generation-2026-10-18/assets/commerce-categories-v3.png'))
  const product = { product_id: 'p', version: 'p1', created_at: '2026-10-18T10:00:00Z', product: { name: '日常通勤商品', product_type: 'digital', category: '数码电子', description: '轻巧便携，适合日常通勤。', audience: '日常通勤者', scene: '通勤、办公' } }
  const draft: any = { product_version: 'p1', material_versions: [{ file_id: 'reference-1', version: 'v1' }, { file_id: 'reference-2', version: 'v1' }], copy_parameters: {}, copy_types: [], copy_instruction: '', copy_text: '', copy_texts: {}, image_platform: '', image_outputs: [], image_instruction: '', video_first_frame_file_id: '', video_instruction: '' }
  const run: any = { run_id: 'run-1', conversation_id: 'c1', title: product.product.name, version: 1, step: 1, state: { step: 1, draft, confirmed_copy: null, confirmed_images: null, current: { copy: null, image: null, video: null }, pending_batch: null, batches: [] }, tasks: {} }
  const works: Record<string, any> = {}
  let queueFirstImages = true
  let discountedCopyPreview = true
  const prices: any = { copy: 10, image: 20, video: 60 }
  const quote = (kind: string, output?: string) => ({ credits: prices[kind] * (kind === 'image' && output === 'detail_page' ? 3 : 1), spec_id: 'agent-' + kind, spec_version: 'v1', price_version: 'p1', agent_version: 'v1', input_digest: 'TEST_ONLY', policy_versions: {} })
  const agents = ['copy', 'image', 'video'].map(kind => ({ agent_id: 'agent-' + kind, kind, name: kind === 'copy' ? '文案' : kind === 'image' ? '图片' : '视频', protocol_version: kind === 'copy' ? 'text-agent-v1' : kind === 'image' ? 'image-agent-v1' : 'video-agent-v1', enabled: true, version: 'v1', input_support: { min_materials: kind === 'copy' ? 0 : 1, max_materials: 3, product_required_fields: ['name'], instruction_required: false } }))
  const plan = { kind: 'video', status: 'awaiting_confirmation', plan: { plan_version: 1, document: { creative: '展示商品真实外观和通勤场景', audience: '日常通勤者', selling_points: ['轻巧便携'], duration_seconds: 5, aspect_ratio: '9:16', subtitles: true, voiceover: false, music: false, shared_visual: { scene: '自然光中的简洁桌面' }, shots: [{ shot_id: 's1', content: '展示完整商品', camera: '缓慢推进' }] } } }
  await page.route('**/api/v1/**', async route => {
    const req = route.request(), path = new URL(req.url()).pathname, body = req.method() === 'GET' ? null : req.postDataJSON()
    const respond = (json: unknown) => route.fulfill({ json })
    if (/\/(prepare|submit|advance)$/.test(path)) stageMutations.push(path)
    if (path === '/api/v1/me') return respond({ user_id: 'TEST_ONLY-owner', username: '流程验证', role: 'user', status: 'active' })
    if (path === '/api/v1/account') return respond({ available: 920, frozen: 0, consumed: 0 })
    if (path === '/api/v1/agents') return respond(agents)
    if (path === '/api/v1/assist/prompts') { assists.push(body); return respond({ original: body.original, proposed: 'AI 完善：' + body.original, missing_facts: [], policy_version: 'v1', agent_version: 'v1', spec_version: 'v1' }) }
    if (path === '/api/v1/tasks') return respond({ items: [], next_cursor: null })
    if (path === '/api/v1/products/versions/' + product.version) return respond(product)
    if (path === '/api/v1/products/versions') {
      productSaves.push(body)
      product.version = 'p' + (productSaves.length + 1); product.product = body.product
      return respond(product)
    }
    if (path.startsWith('/api/v1/files/')) return route.fulfill({ body: photo, contentType: 'image/png' })
    if (path.startsWith('/api/v1/works/')) return respond(works[path.split('/').pop()!])
    if (path === '/api/v1/quotes') {
      const kind = body.agent_id.replace('agent-', '')
      return respond({ ...quote(kind, body.input.parameters.output_type), ...(kind === 'copy' && discountedCopyPreview ? { credits: 9 } : {}) })
    }
    if (path.endsWith('/video/confirm')) {
      const video = Object.values(run.tasks).find((task: any) => task.agent_id === 'agent-video') as any
      video.media = { kind: 'video', status: 'completed' }; video.task.state = 'SUCCEEDED'; video.task.settlement_state = 'CONSUMED'; video.task.work_ids = ['work-video']
      works['work-video'] = { work_id: 'work-video', task_id: video.task.task_id, kind: 'video', items: [{ file_id: 'video-file' }] }
      return respond(video.media)
    }
    if (path === '/api/v1/quick-generation') return respond([{ ...run, step: run.state.step, state: undefined, tasks: undefined }])
    if (path === '/api/v1/quick-generation/run-1' && req.method() === 'PATCH') { run.state.draft = body.draft; run.version++; return respond(run) }
    if (path.endsWith('/cancel')) { run.state.pending_batch = null; run.version++; return respond(run) }
    if (path.endsWith('/prepare')) {
      const d = run.state.draft, kind = body.kind
      preparations.push(body)
      if (body.item_index !== undefined) {
        const previous = run.state.batches.find((b: any) => b.id === run.state.current[kind])
        const items = structuredClone(previous.items)
        const item = items[body.item_index]
        item.task_id = null
        item.free_regeneration = (item.free_regenerations_used || 0) < 3
        item.free_regenerations_used = (item.free_regenerations_used || 0) + (item.free_regeneration ? 1 : 0)
        const batch = { id: 'batch-' + run.state.batches.length, kind, submitted: false, draft_digest: 'TEST_ONLY', items }
        run.state.batches.push(batch); run.state.pending_batch = batch.id; run.version++; return respond(run)
      }
      const selections = kind === 'image' ? d.image_outputs : kind === 'copy' ? d.copy_types.length ? d.copy_types : [d.copy_parameters.copy_type || 'copy'] : [kind]
      const batch = { id: 'batch-' + run.state.batches.length, kind, submitted: false, draft_digest: 'TEST_ONLY', items: selections.map((output: string) => ({ free_regenerations_used: 0, free_regeneration: false, label: kind === 'copy' ? output === 'copy' ? '营销文案' : output : ({ main_image: '商品主图 · 1 张', detail_page: '详情图 · 3 张', long_image: '商品长图 · 1 张', video: '视频' } as any)[output], task_id: null, request: { agent_id: 'agent-' + kind, conversation_id: 'c1', confirmed_quote: quote(kind, output), input: { product_version: d.product_version, product: product.product, instruction: kind === 'copy' ? d.copy_instruction : d[kind + '_instruction'] + '\n已确认文案：' + run.state.confirmed_copy, parameters: kind === 'copy' ? { ...d.copy_parameters, ...(output === 'copy' ? {} : { copy_type: output }) } : kind === 'image' ? { platform: d.image_platform, output_type: output } : { first_frame_file_id: d.video_first_frame_file_id }, material_versions: d.material_versions } } })) }
      run.state.batches.push(batch); run.state.pending_batch = batch.id; run.version++; return respond(run)
    }
    if (path.endsWith('/submit')) {
      const batch = run.state.batches.find((b: any) => b.id === path.split('/').at(-2))
      if (batch.kind === 'copy') discountedCopyPreview = false
      submissions.push(JSON.parse(JSON.stringify(batch)))
      for (const [index, item] of batch.items.entries()) {
        if (item.task_id) continue
        const taskId = batch.id + '-' + index, workId = 'work-' + taskId, output = item.request.input.parameters.output_type
        item.task_id = taskId
        const count = output === 'detail_page' ? 3 : 1
        works[workId] = { work_id: workId, task_id: taskId, kind: batch.kind, warnings: [], items: Array.from({ length: count }, (_, i) => ({ file_id: taskId + '-file-' + i, file_version: 'v1', media_type: batch.kind === 'copy' ? 'text/plain' : 'image/png', text: batch.kind === 'copy' ? '原始' + item.label + '\n轻巧便携，陪伴日常通勤。' : null })) }
        const queued = batch.kind === 'image' && queueFirstImages
        run.tasks[taskId] = { agent_id: item.request.agent_id, conversation_id: 'c1', conversation_display_number: 'H20261018-000001', policy_versions: {}, input: item.request.input, media: batch.kind === 'video' ? plan : null, task: { task_id: taskId, display_number: 'T20261018-00000' + index, state: queued ? 'QUEUED' : batch.kind === 'video' ? 'RUNNING' : 'SUCCEEDED', state_version: 1, settlement_state: queued || batch.kind === 'video' ? 'FROZEN' : 'CONSUMED', quote: { ...item.request.confirmed_quote, credits: item.free_regeneration ? 0 : item.request.confirmed_quote.credits }, work_ids: queued || batch.kind === 'video' ? [] : [workId], created_at: '2026-10-18T10:00:00Z', updated_at: '2026-10-18T10:00:00Z', investigation_reason: null } }
      }
      if (batch.kind === 'copy') {
        const changed = batch.items.filter((item: any) => item.task_id.startsWith(batch.id + '-'))
        if (changed.length === batch.items.length) { run.state.draft.copy_text = ''; run.state.draft.copy_texts = {} }
        else { for (const item of changed) delete run.state.draft.copy_texts[item.request.input.parameters.copy_type]; run.state.draft.copy_text = '' }
        run.state.confirmed_copy = null; run.state.confirmed_images = null; run.state.current.image = null; run.state.current.video = null
      }
      batch.submitted = true; run.state.current[batch.kind] = batch.id; run.state.pending_batch = null; run.state.step = batch.kind === 'copy' ? 2 : batch.kind === 'image' ? 3 : 4; run.version++; return respond(run)
    }
    if (path.endsWith('/advance')) {
      if (body.action === 'confirm_copy') { const d = run.state.draft; run.state.confirmed_copy = d.copy_types.length > 1 ? d.copy_types.map((type: string) => type + '\n' + d.copy_texts[type]).join('\n\n') : d.copy_text; run.state.step = 3 }
      if (body.action === 'confirm_images') { run.state.confirmed_images = run.state.current.image; run.state.step = 4 }
      if (body.action === 'finish') run.state.step = 5
      run.version++; return respond(run)
    }
    if (path === '/api/v1/quick-generation/run-1') return respond(run)
    return respond({ items: [], next_cursor: null })
  })
  const snap = async (name: string) => { await page.evaluate(() => { window.scrollTo(0, 0); document.querySelector('.quick-content')?.scrollTo(0, 0) }); await page.screenshot({ path: info.outputPath('quick-generation-' + name + '.png'), fullPage: true, animations: 'disabled' }); expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true); if (info.project.name === 'desktop') expect(await page.locator('.quick-footer').evaluate(el => el.getBoundingClientRect().bottom <= innerHeight)).toBe(true) }
  await page.goto('/workspace/quick/run-1')
  await expect(page.locator('.quick-stepper [aria-current="step"]')).toContainText('商品确认')
  if (info.project.name === 'desktop') expect(await page.locator('.quick-history-item .task-title').evaluate(el => el.getBoundingClientRect().width)).toBeGreaterThan(120)
  const productName = page.locator('#quick-product-name')
  await expect(productName).toHaveValue('日常通勤商品')
  await productName.fill('日常通勤商品 · 已核对')
  await page.keyboard.press('Escape')
  await expect(productName).toHaveValue('日常通勤商品 · 已核对')
  expect(productSaves).toHaveLength(0)
  await page.getByRole('button', { name: '保存商品资料', exact: true }).click()
  await expect.poll(() => run.state.draft.product_version).toBe('p2')
  await expect(page.getByRole('button', { name: '保存商品资料', exact: true })).toBeDisabled()
  expect(productSaves).toHaveLength(1)
  expect(productSaves[0].product.name).toBe('日常通勤商品 · 已核对')
  expect(run.state.draft.product_version).toBe('p2')
  await page.reload()
  await expect(productName).toHaveValue('日常通勤商品 · 已核对')
  await expect(page.locator('.quick-content').getByText('文案创作要求', { exact: true })).toHaveCount(0)
  await expect(page.getByLabel('创作指令', { exact: true })).toHaveCount(0)
  await expect(page.getByLabel('目标人群', { exact: true })).toHaveCount(0)
  await expect(page.getByText('适用人群', { exact: true })).toBeVisible()
  await snap('01-product')
  await page.getByRole('button', { name: '确认商品，生成文案' }).click()
  const requirements = page.getByRole('dialog', { name: '文案创作要求', exact: true })
  const charge = page.getByRole('dialog', { name: '确认生成', exact: true })
  await expect(requirements).toBeVisible()
  await expect(charge).not.toBeVisible()
  await expect(requirements.getByRole('button', { name: '取消', exact: true })).toBeFocused()
  expect(stageMutations).toHaveLength(0)
  await expect(requirements.getByLabel('最大字符数', { exact: true })).toHaveCount(0)
  await expect(requirements.getByLabel('额外写作要求', { exact: true })).toHaveCount(0)
  await expect(requirements.getByLabel('额外协作要求', { exact: true })).toHaveCount(0)
  await expect(requirements.getByLabel('目标平台', { exact: true })).toHaveValue('淘宝')
  await expect(requirements.getByLabel('语气', { exact: true })).toHaveValue('自然')
  await expect(requirements.locator('.quick-copy-requirements > .el-select .el-tag')).toHaveCount(7)
  await expect(requirements.locator('.quick-copy-requirements > .el-select')).toContainText('营销策略')
  const selectTwoCopyTypes = async () => {
    for (const type of ['卖点描述', '详情介绍', '社交平台文案', '直播口播', '营销策略']) {
      await requirements.locator('.quick-copy-requirements > .el-select .el-tag').filter({ hasText: type }).getByRole('button', { name: '关闭此标签', exact: true }).click()
    }
    await expect(requirements.locator('.quick-copy-requirements > .el-select .el-tag')).toHaveCount(2)
  }
  await selectTwoCopyTypes()
  await requirements.getByLabel('语气', { exact: true }).fill('专业')
  await expect(requirements.locator('.quick-charge-total')).toContainText('18 积分')
  await snap('01-copy-requirements')
  // A changed exact quote stays in this dialog and needs a second explicit confirmation.
  await requirements.getByRole('button', { name: '确认生成文案', exact: true }).click()
  await expect(requirements).toBeVisible()
  await expect(requirements.locator('.quick-charge-total')).toContainText('20 积分')
  await expect(requirements.getByRole('combobox', { name: '文案类型', exact: true })).toBeDisabled()
  await expect(charge).not.toBeVisible()
  expect(preparations[0].kind).toBe('copy')
  expect(submissions).toHaveLength(0)
  await requirements.getByRole('button', { name: '取消', exact: true }).click()
  await expect(requirements).not.toBeVisible()
  expect(submissions).toHaveLength(0)
  await page.getByRole('button', { name: '确认商品，生成文案' }).click()
  await expect(requirements.getByLabel('语气', { exact: true })).toHaveValue('自然')
  await expect(requirements.locator('.quick-copy-requirements > .el-select .el-tag')).toHaveCount(7)
  await selectTwoCopyTypes()
  await requirements.getByLabel('语气', { exact: true }).fill('专业')
  await expect(requirements.locator('.quick-charge-total')).toContainText('18 积分')
  await requirements.getByRole('button', { name: '确认生成文案', exact: true }).click()
  await expect(requirements.locator('.quick-charge-total')).toContainText('20 积分')
  expect(submissions).toHaveLength(0)
  await expect(charge).not.toBeVisible()
  await requirements.getByRole('button', { name: '确认生成文案', exact: true }).click()
  await expect(requirements).not.toBeVisible()
  await expect(charge).not.toBeVisible()
  expect(submissions).toHaveLength(1)
  expect(submissions[0].items.map((item: any) => item.request.input.parameters.copy_type)).toEqual(['宣传文案', '商品标题'])
  expect(submissions[0].items.every((item: any) => item.request.input.parameters.tone === '专业' && item.request.input.parameters.platform === '淘宝')).toBe(true)
  expect(submissions[0].items.every((item: any) => !('max_chars' in item.request.input.parameters) && !('extra_instructions' in item.request.input.parameters))).toBe(true)
  await expect(page.getByLabel('宣传文案', { exact: true })).toHaveValue(/原始宣传文案/)
  await expect(page.getByLabel('商品标题', { exact: true })).toHaveValue(/原始商品标题/)
  await expectResultColumns(page.locator('.quick-copy-grid > .quick-copy-paper'), info.project.name === 'mobile')
  await page.getByLabel('商品标题', { exact: true }).fill('兄弟文案保留人工标题')
  const originalTitleTask = run.state.batches.find((batch: any) => batch.id === run.state.current.copy).items[1].task_id
  for (let attempt = 1; attempt <= 4; attempt++) {
    await page.locator('.quick-copy-paper').filter({ has: page.getByLabel('宣传文案', { exact: true }) }).getByRole('button', { name: /重新生成/ }).click()
    await expect(charge).toBeVisible()
    await expect(charge.locator('.quick-charge-list')).toHaveCount(0)
    await expect(charge.locator('.quick-charge-total')).toContainText(attempt <= 3 ? '0 积分' : '10 积分')
    expect(preparations.at(-1).item_index).toBe(0)
    await charge.getByRole('button', { name: '确认生成' }).click()
    await expect(charge).not.toBeVisible()
    await expect(page.getByLabel('宣传文案', { exact: true })).toHaveValue(/原始宣传文案/)
    await expect(page.getByLabel('商品标题', { exact: true })).toHaveValue('兄弟文案保留人工标题')
    const batch = run.state.batches.find((batch: any) => batch.id === run.state.current.copy)
    expect(batch.items[1].task_id).toBe(originalTitleTask)
    expect(batch.items[0].free_regenerations_used).toBe(Math.min(attempt, 3))
    expect(batch.items[0].request.confirmed_quote.credits).toBe(10)
  }
  await page.getByLabel('宣传文案', { exact: true }).fill('人工修改并确认的通勤营销文案')
  await page.getByLabel('商品标题', { exact: true }).fill('轻巧通勤商品标题')
  await page.locator('.quick-stepper').getByRole('button', { name: /商品确认/ }).click()
  await page.locator('.quick-footer').getByRole('button', { name: '下一步', exact: true }).click()
  await page.reload()
  await expect(page.getByLabel('宣传文案', { exact: true })).toHaveValue('人工修改并确认的通勤营销文案')
  await expect(page.getByLabel('商品标题', { exact: true })).toHaveValue('轻巧通勤商品标题')
  await snap('02-copy')
  await page.getByRole('button', { name: '确认文案，生成图片' }).click()
  const imageSelection = page.getByRole('dialog', { name: '选择图片内容', exact: true })
  await expect(imageSelection).toBeVisible()
  await expect(page.locator('.quick-stepper [aria-current="step"]')).toContainText('营销文案')
  await expect(page.locator('.quick-content .quick-image-settings')).toHaveCount(0)
  await page.keyboard.press('Escape')
  await expect(imageSelection).toBeVisible()
  await imageSelection.getByRole('button', { name: '取消', exact: true }).click()
  await expect(page.locator('.quick-stepper').getByRole('button', { name: /视频生成/ })).toBeDisabled()
  for (const name of ['商品确认', '营销文案', '图片生成']) {
    await page.locator('.quick-stepper').getByRole('button', { name: new RegExp(name) }).click()
    await expect(page.locator('.quick-stepper [aria-current="step"]')).toContainText(name)
  }
  expect(submissions).toHaveLength(5)
  await page.getByRole('button', { name: '确认费用并生成图片', exact: true }).click()
  await imageSelection.getByRole('button', { name: '确认生成图片', exact: true }).click()
  await expect(imageSelection).toBeVisible()
  await expect(page.getByRole('alert').filter({ hasText: '请选择目标平台' }).first()).toBeVisible()
  await selectOption(imageSelection.getByRole('combobox', { name: '目标平台', exact: true }), 'taobao')
  for (const label of ['商品主图', '详情图', '商品长图']) await imageSelection.locator('.quick-output-option').filter({ hasText: label }).click()
  await expect(page.getByLabel('创作指令', { exact: true })).toHaveCount(0)
  await snap('03-image-selection')
  await expect(imageSelection.locator('.quick-charge-total')).toContainText('100 积分')
  await expect(imageSelection.locator('.quick-output-option').filter({ hasText: '详情图' })).toContainText('60 积分')
  // This live quote matches the exact quote, so one confirmation submits the group.
  await imageSelection.getByRole('button', { name: '确认生成图片', exact: true }).click()
  await expect(imageSelection).not.toBeVisible()
  await expect(charge).not.toBeVisible()
  await expect(page.locator('.quick-stepper [aria-current="step"]')).toContainText('图片生成')
  await expect(page.locator('.quick-stage-status')).toContainText('后台排队')
  await expect(page.locator('.quick-image-result .status-label')).toHaveText(['排队中', '排队中', '排队中'])
  await expect(page.locator('.quick-content .quick-image-settings')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '确认图片，继续视频', exact: true })).toBeDisabled()
  queueFirstImages = false
  for (const detail of Object.values(run.tasks) as any[]) {
    if (detail.agent_id !== 'agent-image') continue
    detail.task.state = 'SUCCEEDED'; detail.task.settlement_state = 'CONSUMED'; detail.task.state_version++
    detail.task.work_ids = ['work-' + detail.task.task_id]
  }
  await expect(page.locator('.quick-image-result .result-item>img')).toHaveCount(5)
  await expectResultColumns(page.locator('.quick-image-result').filter({ hasText: '详情图 · 3 张' }).locator('.image-gallery > .result-item'), info.project.name === 'mobile', 'image')
  expect(submissions.at(-1).items.every((item: any) => item.request.input.instruction.includes('人工修改并确认的通勤营销文案') && item.request.input.instruction.includes('轻巧通勤商品标题'))).toBe(true)
  const firstImageBatch = run.state.batches.find((batch: any) => batch.id === run.state.current.image)
  const siblingImageTasks = firstImageBatch.items.slice(1).map((item: any) => item.task_id)
  const originalMainTask = firstImageBatch.items[0].task_id
  for (let attempt = 1; attempt <= 4; attempt++) {
    await page.locator('.quick-image-result').filter({ has: page.getByRole('heading', { name: '商品主图 · 1 张', exact: true }) }).getByRole('button', { name: /重新生成/ }).click()
    await expect(charge).toBeVisible()
    await expect(charge.locator('.quick-charge-list')).toHaveCount(0)
    await expect(charge.locator('.quick-charge-total')).toContainText(attempt <= 3 ? '0 积分' : '20 积分')
    expect(preparations.at(-1).item_index).toBe(0)
    await charge.getByRole('button', { name: '确认生成' }).click()
    await expect(charge).not.toBeVisible()
    await expect(page.locator('.quick-image-result .result-item>img')).toHaveCount(5)
    const batch = run.state.batches.find((batch: any) => batch.id === run.state.current.image)
    expect(batch.items.slice(1).map((item: any) => item.task_id)).toEqual(siblingImageTasks)
    expect(batch.items[0].free_regenerations_used).toBe(Math.min(attempt, 3))
    expect(batch.items[0].request.confirmed_quote.credits).toBe(20)
    expect(works['work-' + originalMainTask]).toBeDefined()
  }
  await snap('04-image-results')
  await page.getByRole('button', { name: '确认图片，继续视频' }).click()
  expect(submissions).toHaveLength(10)
  await expect(page.locator('.frame-option')).toHaveCount(7)
  await page.locator('.frame-option').filter({ hasText: '商品主图 · 1 张 · 成果 1' }).click()
  await expect(page.getByLabel('创作指令', { exact: true })).toHaveCount(0)
  expect(assists).toHaveLength(0)
  await expect(page.locator('.quick-footer strong')).toHaveText('60 积分')
  await snap('05-video')
  await page.getByRole('button', { name: '确认费用，生成视频方案' }).click()
  await charge.getByRole('button', { name: '确认生成' }).click()
  const navigateExistingStages = async () => {
    const mutationsBefore = stageMutations.length
    const footer = page.locator('.quick-footer')
    for (const [index, name] of ['商品确认', '营销文案', '图片生成'].entries()) {
      await page.locator('.quick-stepper').getByRole('button', { name: new RegExp(name) }).click()
      await expect(page.locator('.quick-stepper [aria-current="step"]')).toContainText(name)
      await expect(footer).toHaveText(index === 0 ? /^\s*下一步\s*$/ : /^\s*上一步\s*下一步\s*$/)
      await expect(footer.getByRole('button', { name: '下一步', exact: true })).toBeEnabled()
      await footer.getByRole('button', { name: '下一步', exact: true }).click()
      await expect(page.locator('.quick-stepper [aria-current="step"]')).toContainText(['营销文案', '图片生成', '视频生成'][index]!)
    }
    expect(stageMutations).toHaveLength(mutationsBefore)
    expect(submissions).toHaveLength(11)
  }
  await navigateExistingStages()
  await page.getByRole('button', { name: '查看并确认方案' }).click()
  const drawer = page.getByRole('dialog', { name: '视频创作方案', exact: true })
  await expect(drawer).toContainText('展示商品真实外观')
  await expect(drawer.locator('input,textarea')).toHaveCount(0)
  await snap('06-plan')
  await drawer.getByRole('button', { name: '确认此方案' }).click()
  await page.getByRole('dialog', { name: '确认视频方案', exact: true }).getByRole('button', { name: '确认并继续生成' }).click()
  await expect(page.getByRole('button', { name: '完成并汇总成果' })).toBeEnabled()
  await page.getByRole('button', { name: '完成并汇总成果' }).click()
  await expect(page.locator('.quick-completed-section')).toHaveCount(3)
  await page.reload()
  await expect(page.locator('.quick-completed-section')).toHaveCount(3)
  await expect(page.locator('.quick-confirmed-copy')).toContainText('人工修改并确认的通勤营销文案')
  await expect(page.locator('.quick-confirmed-copy')).toContainText('轻巧通勤商品标题')
  await snap('07-complete')
  await navigateExistingStages()
  await expect(page.locator('.quick-page-caption')).toContainText('已完成 · 只读查看')
  await expect(page.locator('.regenerate-action')).toHaveCount(0)
  await expect(page.locator('.quick-footer').getByRole('button', { name: '查看汇总', exact: true })).toBeEnabled()
  const historyMutations = stageMutations.length
  await page.locator('.quick-footer').getByRole('button', { name: '查看汇总', exact: true }).click()
  await expect(page.locator('.quick-completed-section')).toHaveCount(3)
  await page.locator('.quick-stepper').getByRole('button', { name: /营销文案/ }).click()
  for (const type of ['宣传文案', '商品标题']) await expect(page.getByLabel(type, { exact: true })).toHaveAttribute('readonly')
  await expect(page.getByRole('button', { name: '调整创作要求', exact: true })).toHaveCount(0)
  expect(stageMutations).toHaveLength(historyMutations)
  expect(submissions).toHaveLength(11)
  expect(errors).toEqual([])
})
