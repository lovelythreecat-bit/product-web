import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import QuickGenerationView from '../../src/features/quick-generation/QuickGenerationView.vue'
import { useQuickGeneration } from '../../src/features/quick-generation/useQuickGeneration'

const api = vi.hoisted(() => ({ getQuickRun: vi.fn(), saveQuickRun: vi.fn(), prepareQuickRun: vi.fn(), uploadFile: vi.fn() }))
vi.mock('../../src/api/quickGeneration', () => api)
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { runId: 'run-1' }, query: {} }), useRouter: () => ({ push: vi.fn(), replace: vi.fn() }), onBeforeRouteLeave: vi.fn(), onBeforeRouteUpdate: vi.fn() }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: ref(1), profile: ref({ user_id: 'owner' }), refreshAccount: vi.fn() } }))
vi.mock('../../src/api/catalog', () => ({ listAgents: vi.fn().mockResolvedValue([]), quote: vi.fn().mockResolvedValue({ credits: 20 }) }))
vi.mock('../../src/api/conversations', () => ({ getProductVersion: vi.fn().mockResolvedValue({ version: 'p1', product: { name: '杯子', category: '家居', product_type: 'home' } }) }))
vi.mock('../../src/api/files', () => ({ uploadFile: api.uploadFile, fileContentUrl: (id: string) => '/files/' + id }))
const materials = (count: number) => Array.from({ length: count }, (_, index) => ({ file_id: `image-${index}`, version: 'v1' }))
const fixture = (count: number) => ({ run_id: 'run-1', version: 1, conversation_id: 'c1', title: '杯子', step: 1, state: { step: 1, draft: { product_version: 'p1', material_versions: materials(count), copy_parameters: {}, copy_instruction: '', copy_text: '', image_platform: 'taobao', image_outputs: ['main_image'], image_instruction: '', video_first_frame_file_id: '', video_instruction: '' }, confirmed_copy: null, confirmed_images: null, current: { copy: null, image: null, video: null }, pending_batch: null, batches: [] }, tasks: {} })
beforeEach(() => {
 vi.clearAllMocks()
 api.getQuickRun.mockResolvedValue(fixture(3))
 api.saveQuickRun.mockImplementation(async (_id, version, draft) => ({ ...fixture(3), version: version + 1, state: { ...fixture(3).state, draft } }))
 api.uploadFile.mockResolvedValue({ file_id: 'fourth', version: 'v1' })
})
function controller() {
 let state!: ReturnType<typeof useQuickGeneration>
 const view = mount(defineComponent({ setup() { state = useQuickGeneration(); return () => h('div') } }))
 return { view, state }
}
it('persists the fourth reference and refuses a fifth without uploading it', async () => {
 const { view, state } = controller(); await flushPromises()
 try {
  const file = new File(['image'], 'reference.png', { type: 'image/png' })
  expect(await state.upload(file)).toBe(true)
  expect(state.materials.value).toHaveLength(4)
  expect(await state.upload(file)).toBe(false)
  expect(state.materials.value).toHaveLength(4)
  expect(api.uploadFile).toHaveBeenCalledTimes(1)
 } finally { view.unmount() }
})
it('reads all legacy references but rejects a new generation until at most four remain', async () => {
 api.getQuickRun.mockResolvedValue(fixture(5))
 const { view, state } = controller(); await flushPromises()
 try {
  expect(state.materials.value).toHaveLength(5)
  await state.prepare('copy')
  expect(state.error.value).toContain('最多支持 4 张')
  expect(api.prepareQuickRun).not.toHaveBeenCalled()
  expect(state.materials.value).toHaveLength(5)
 } finally { view.unmount() }
})
it('rejects an overflowing multi-file selection before uploading any files', async () => {
 const view = mount(QuickGenerationView, { global: { stubs: { RouterLink: true, QuickProductEditor: true, TaskCard: true } } }); await flushPromises()
 try {
  const input = view.get<HTMLInputElement>('[aria-label="上传商品图片"]')
  const files = [new File(['a'], 'a.png', { type: 'image/png' }), new File(['b'], 'b.png', { type: 'image/png' })]
  Object.defineProperty(input.element, 'files', { configurable: true, value: files })
  await input.trigger('change'); await flushPromises()
  expect(view.text()).toContain('还可以添加 1 张')
  expect(api.uploadFile).not.toHaveBeenCalled()
 } finally { view.unmount() }
})
