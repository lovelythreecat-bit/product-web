/** TEST_ONLY: all API requests are answered in memory; no real writes or charges. */
import { createApp } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from '../../src/App.vue'
import QuickGenerationView from '../../src/features/quick-generation/QuickGenerationView.vue'
import { session } from '../../src/features/auth/session'
import '../../src/styles/element-components'
import '../../src/styles/tokens.css'
import '../../src/styles/element-theme.css'
import '../../src/features/workspace/workspace.css'

const params = new URLSearchParams(location.search)
const step = Number(params.get('step') || 1)
const types = ['宣传文案', '商品标题', '卖点描述', '详情介绍', '社交平台文案', '直播口播', '营销策略']
const product = { name: '轻量无线头戴耳机', product_type: 'digital', category: '数码电器', brand: '示例品牌', model: 'H01', material: '轻量复合材质', description: '柔软耳垫与可调节头梁，适合日常通勤、阅读和桌面办公。\n商品事实以提供的真实资料为准。', usage_scenarios: '办公室、日常通勤' }
const materials = Array.from({ length: params.has('empty') ? 0 : 4 }, (_, index) => ({ file_id: `TEST_ONLY-image-${index}`, version: 'v1' }))
const quote = { credits: 10, agent_version: 'v1', spec_id: 'copy', spec_version: 'v1', price_version: 'v1', input_digest: 'TEST_ONLY', policy_versions: {} }
const copyText = '轻一点，让日常更自在。\n\n柔软耳垫贴合双耳，可调节头梁让佩戴更舒适。放进通勤包，或留在办公桌边，随时开启属于自己的片刻。\n\n具体功能与参数以商品资料为准。'
const draft = { product_version: 'TEST_ONLY-product', material_versions: materials, copy_parameters: { platform: '淘宝', tone: '自然' }, copy_types: types, copy_instruction: '', copy_text: copyText, copy_texts: Object.fromEntries(types.map(type => [type, type === '商品标题' ? '轻量无线头戴耳机，日常随行' : copyText])), image_platform: 'taobao', image_outputs: ['main_image', 'detail_page', 'long_image'], image_instruction: '', video_first_frame_file_id: materials[0]?.file_id || '', video_instruction: '' }
const input = { product_version: draft.product_version, product, parameters: {}, material_versions: materials, instruction: '' }
const plan = { plan_version: 3, document: { creative: '从通勤到办公，展示轻松佩戴体验', audience: '日常通勤与办公人群', selling_points: ['柔软耳垫', '可调节头梁'], duration_seconds: 10, aspect_ratio: '9:16', subtitles: true, music: true, music_direction: '舒缓自然', shots: [{ shot_id: 's1', content: '耳机放在明亮的木质桌面上', action: '缓慢转动', camera: '轻推', shot_size: '特写', subtitle_text: '让日常更自在', voiceover_text: '轻一点，舒适多一点' }, { shot_id: 's2', content: '展示耳垫与头梁细节', action: '平稳展示', camera: '平移', subtitle_text: '柔软贴合' }] } }
const media = { kind: 'video', status: 'awaiting_confirmation', head_plan_version: 3, plan }
const tasks: Record<string, any> = {}, works: Record<string, any> = {}
function batch(kind: string, labels: string[]) {
  return { id: kind, kind, submitted: true, items: labels.map((label, index) => {
    const taskId = `TEST_ONLY-${kind}-${index}`, workId = taskId + '-work'
    const parameters = kind === 'copy' ? { copy_type: label } : { output_type: ['main_image', 'detail_page', 'long_image'][index] }
    const request = { input: { ...input, parameters }, confirmed_quote: quote }
    const failed = params.has('failure') && kind === 'image' && index === 1
    const running = kind === 'video' && step === 4 || params.has('loading') && kind === 'copy'
    tasks[taskId] = { agent_id: kind, conversation_id: 'TEST_ONLY-conversation', input: request.input, policy_versions: {}, ...(running && kind === 'video' ? { media } : {}), task: { task_id: taskId, display_number: `20261021-${index + 1}`, created_at: '2026-10-21T03:00:00Z', state: failed ? 'FAILED' : running ? 'RUNNING' : 'SUCCEEDED', state_version: 1, settlement_state: failed || running ? 'FROZEN' : 'CONSUMED', work_ids: failed || running ? [] : [workId], quote } }
    works[workId] = { work_id: workId, kind, task_id: taskId, created_at: '2026-10-21T03:00:00Z', items: Array.from({ length: kind === 'image' && index === 1 ? 3 : 1 }, (_, n) => ({ file_id: `TEST_ONLY-${kind}-${index}-${n}`, file_version: 'v1', item_key: String(n), media_type: kind === 'copy' ? 'text/plain' : kind === 'video' ? 'video/mp4' : 'image/svg+xml', actual_bytes: 4096, content_url: `/api/v1/files/TEST_ONLY-${kind}-${index}-${n}/content`, text: kind === 'copy' ? draft.copy_texts[label] : null })) }
    return { label, task_id: taskId, request, free_regenerations_used: 0 }
  }) }
}
const batches = [batch('copy', types), batch('image', ['商品主图', '详情图', '商品长图']), batch('video', ['商品视频'])]
// Persisted image history used only by the local UI verification page.
if (params.has('image-history')) {
  const original = batches[1]!
  original.id = 'image-original'
  const previous = original.items[1]!, taskId = 'TEST_ONLY-image-details-v2', workId = taskId + '-work'
  tasks[taskId] = structuredClone(tasks[previous.task_id])
  tasks[taskId].task.task_id = taskId
  tasks[taskId].task.work_ids = [workId]
  works[workId] = { ...structuredClone(works[previous.task_id + '-work']), work_id: workId, task_id: taskId }
  batches.push({ ...original, id: 'image', items: original.items.map((item, index) => index === 1 ? { ...item, task_id: taskId, free_regenerations_used: 1 } : item) })
}
const run: any = { run_id: 'TEST_ONLY-ui', conversation_id: 'TEST_ONLY-conversation', title: product.name, step, version: 1, state: { step, draft, confirmed_copy: copyText, confirmed_images: step >= 4 ? 'image' : null, current: { copy: step >= 2 ? 'copy' : null, image: step >= 3 && !params.has('empty-results') ? 'image' : null, video: step >= 4 && !params.has('frames') ? 'video' : null }, pending_batch: null, batches }, tasks: Object.fromEntries(Object.entries(tasks).filter(([key]) => step >= 4 || !key.includes('video'))) }
function svg(id: string) {
  const long = id.includes('image-2-'), height = long ? 1200 : 480
  return `<svg xmlns="http://www.w3.org/2000/svg" width="480" height="${height}" viewBox="0 0 480 ${height}"><rect width="480" height="${height}" fill="#e9ddcd"/><circle cx="240" cy="240" r="174" fill="#f2e8db"/><path d="M122 265v-65a118 118 0 0 1 236 0v65" fill="none" stroke="#bca98e" stroke-width="31"/><rect x="99" y="213" width="70" height="131" rx="29" fill="#d5c6af"/><rect x="311" y="213" width="70" height="131" rx="29" fill="#d5c6af"/><text x="240" y="409" text-anchor="middle" fill="#706259" font-family="sans-serif" font-size="17">TEST_ONLY · 商品示意</text>${long ? '<rect x="40" y="510" width="400" height="630" rx="16" fill="#fffdfa"/><text x="240" y="620" text-anchor="middle" fill="#706259" font-size="22">完整长图示意</text>' : ''}</svg>`
}
const imageSrc = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src')!
Object.defineProperty(HTMLImageElement.prototype, 'src', { ...imageSrc, set(value: string) { imageSrc.set!.call(this, value.includes('/api/v1/files/TEST_ONLY-') ? 'data:image/svg+xml,' + encodeURIComponent(svg(value)) : value) } })
const requests: any[] = []
Object.assign(window, { quickUiFixtureRequests: requests })
window.fetch = async (resource, options = {}) => {
  const url = new URL(String(resource), location.origin), path = url.pathname, method = options.method || 'GET'
  requests.push({ path, method, body: options.body })
  const json = (value: unknown) => new Response(JSON.stringify(value), { headers: { 'Content-Type': 'application/json' } })
  if (!path.startsWith('/api/v1/')) throw new Error('Fixture blocks non-API fetch')
  if (path === '/api/v1/me') return json({ user_id: 'TEST_ONLY-ui-owner', username: '界面验证', role: 'user', status: 'active' })
  if (path === '/api/v1/account') return json({ available: 100, frozen: 10, consumed: 20 })
  if (path === '/api/v1/agents') return json(['copy', 'image', 'video'].map(kind => ({ agent_id: kind, kind, name: kind, enabled: true, version: 'v1', input_support: { product_required_fields: [] } })))
  if (path.includes('/quote')) return json(quote)
  if (path === '/api/v1/products/versions/TEST_ONLY-product') return json({ product_id: 'TEST_ONLY-product', version: 'TEST_ONLY-product', product })
  if (path === '/api/v1/products/versions' && method === 'POST') return json({ product_id: 'TEST_ONLY-product', version: 'TEST_ONLY-product', product: JSON.parse(String(options.body)).product })
  if (path === '/api/v1/quick-generation') return json([{ ...run, state: undefined, tasks: undefined }])
  if (path === '/api/v1/quick-generation/TEST_ONLY-ui') { if (method === 'PATCH') { run.state.draft = JSON.parse(String(options.body)).draft; run.version++ } return json(run) }
  if (path.includes('/video/plan-revisions')) { const body = JSON.parse(String(options.body)); media.head_plan_version++; media.plan.plan_version = media.head_plan_version; Object.assign(media.plan.document, { music_direction: body.patch.music_direction }); for (const shot of body.patch.shot_texts || []) Object.assign(media.plan.document.shots.find(s => s.shot_id === shot.shot_id)!, shot); return json(media) }
  if (path.includes('/video/confirm')) { media.status = 'generating'; return json(media) }
  if (path.startsWith('/api/v1/tasks/')) return json(tasks[path.split('/').at(-1)!])
  if (path.startsWith('/api/v1/works/')) return json(works[path.split('/').at(-1)!])
  if (path.startsWith('/api/v1/files/') && path.endsWith('/content')) return new Response(svg(path), { headers: { 'Content-Type': 'image/svg+xml' } })
  if (path === '/api/v1/files' && method === 'POST') return json({ file_id: `TEST_ONLY-upload-${requests.length}`, version: 'v1' })
  if (method !== 'GET') return new Response(JSON.stringify({ error: { code: 'TEST_ONLY_BLOCKED', message: '此验证页面未实现该写入操作。' } }), { status: 409, headers: { 'Content-Type': 'application/json' } })
  return json({ items: [], next_cursor: null })
}
await session.restore()
const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/workspace/quick/:runId', component: QuickGenerationView }, { path: '/:pathMatch(.*)*', component: { template: '<p>TEST_ONLY 验证结束</p>' } }] })
await router.push('/workspace/quick/TEST_ONLY-ui')
createApp(App).use(router).mount('#app')
