import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'
import type { Schema } from '../../src/types/api'

const api = vi.hoisted(() => ({ preparePrompt: vi.fn(), createProductVersion: vi.fn(), listAgents: vi.fn(), listSpecs: vi.fn(), quote: vi.fn() }))
vi.mock('../../src/api/assist', () => ({ preparePrompt: api.preparePrompt }))
vi.mock('../../src/api/catalog', () => ({ listAgents: api.listAgents, listSpecs: api.listSpecs, quote: api.quote }))
vi.mock('../../src/api/conversations', () => ({ createProductVersion: api.createProductVersion, createConversation: vi.fn(), getProductVersion: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { conversationId: 'remediation' } }), useRouter: () => ({ push: vi.fn() }) }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: ref(1), profile: ref({ user_id: 'remediation-user' }), refreshAccount: vi.fn() }, onIdentityChange: () => () => {} }))
vi.mock('../../src/features/workspace/useTaskStream', () => ({ useTaskStream: () => ({ tasks: ref([]), details: ref({}), fragments: ref({}), connectionState: ref('open'), reconnect: vi.fn() }) }))

import PromptEditor from '../../src/features/workspace/PromptEditor.vue'
import WorkspaceView from '../../src/features/workspace/WorkspaceView.vue'
import ResultViewer from '../../src/components/ResultViewer.vue'
import { draftFor } from '../../src/features/workspace/drafts'

const wrappers: VueWrapper[] = []
const findButton = (wrapper: VueWrapper, text: string) => wrapper.findAll('button').find(button => button.text() === text)!
const overlay = { props: ['open'], emits: ['update:open'], template: '<div v-if="open"><slot/><button @click="$emit(\'update:open\', false)">取消</button><slot name="actions"/></div>' }
beforeEach(() => {
  vi.resetAllMocks()
  api.listAgents.mockResolvedValue([{ agent_id: 'image-agent', name: '图片', kind: 'image', enabled: true, input_support: { product_required_fields: ['name'], min_materials: 1, max_materials: 1, instruction_required: false } }])
  api.listSpecs.mockResolvedValue([])
  const draft = draftFor('remediation')
  draft.agentId = 'image-agent'; draft.agents = { 'image-agent': { specId: '', instruction: '', parameters: { ratio: '1:1' } } }
  draft.product = { product_id: 'product', version: 'version', product: { name: '真实商品', sellingPoints: '原卖点' }, created_at: '' }
  draft.materials = []; draft.pending = null
})
afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()) })

it('fills the instruction immediately and can restore the actual original', async () => {
  api.preparePrompt.mockResolvedValue({ original: '服务端原值', proposed: '辅助建议' })
  const wrapper = mount(PromptEditor, { props: { modelValue: '原指令', request: { original: '原指令' } as Schema<'AssistRequest'> } }); wrappers.push(wrapper)
  await findButton(wrapper, 'AI 帮我完善').trigger('click'); await flushPromises()
  expect(wrapper.find('#assist-suggestion').exists()).toBe(false)
  expect(wrapper.text()).not.toContain('采用建议')
  expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['辅助建议'])
  await findButton(wrapper, '撤回辅助，恢复原指令').trigger('click')
  expect(wrapper.emitted('update:modelValue')?.[1]).toEqual(['原指令'])
})

it('keeps the first original when adopting a second refinement and shows missing fact labels', async () => {
  api.preparePrompt.mockResolvedValue({ proposed: '第一版建议', missing_facts: ['category', 'material_versions'] })
  const wrapper = mount(PromptEditor, { props: { modelValue: '商家原指令', request: { original: '商家原指令' } as Schema<'AssistRequest'> } }); wrappers.push(wrapper)
  await findButton(wrapper, 'AI 帮我完善').trigger('click'); await flushPromises()
  expect(wrapper.text()).toContain('商品品类')
  expect(wrapper.text()).toContain('商品图片')
  await wrapper.setProps({ modelValue: '第一版建议', request: { original: '第一版建议' } as Schema<'AssistRequest'> })
  api.preparePrompt.mockResolvedValue({ proposed: '第二版建议', missing_facts: [] })
  await findButton(wrapper, 'AI 帮我完善').trigger('click'); await flushPromises()
  await wrapper.setProps({ modelValue: '第二版建议' })
  await findButton(wrapper, '撤回辅助，恢复原指令').trigger('click')
  expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['商家原指令'])
})

it('removes prompt editing and assistance from ordinary image creation', async () => {
  api.listAgents.mockResolvedValue([{ agent_id:'image-agent', version:'v1', kind:'image', name:'图片', protocol_version:'image-agent-v1', enabled:true, input_support:{product_required_fields:['name'],min_materials:1,max_materials:3,instruction_required:false} }])
  const draft = draftFor('remediation')
  draft.agents['image-agent'].parameters = {platform:'taobao',output_type:'main_image'}
  const wrapper = mount(WorkspaceView, { global: { stubs: { AppDrawer: overlay, AppDialog: overlay, AgentSelector: true, PromptEditor: true, TaskCard: true } } }); wrappers.push(wrapper)
  await flushPromises()
  expect(wrapper.findComponent(PromptEditor).exists()).toBe(false)
  draft.agents['image-agent'].parameters = {}
  await flushPromises()
  expect(wrapper.find('#creation-instruction').exists()).toBe(false)
  expect(api.preparePrompt).not.toHaveBeenCalled()
})

it('drops retired hidden instruction and target audience from new quotes and charged snapshots', async () => {
  api.listAgents.mockResolvedValue([{agent_id:'text-agent',version:'text-agent-v1',kind:'copy',name:'文案',protocol_version:'text-agent-v1',enabled:true,input_support:{product_required_fields:['name'],min_materials:0,max_materials:3,instruction_required:false}}])
  const draft = draftFor('remediation')
  draft.agentId = 'text-agent'
  draft.product!.product.audience = '商品适用人群'
  const parameters = {copy_type:'直播口播',platform:'抖音',audience:'通勤者',tone:'亲切',max_chars:120,extra_instructions:'先讲使用场景'}
  draft.agents['text-agent'] = {specId:'',instruction:'只写已有依据的特点',parameters}
  api.quote.mockResolvedValue({credits:8})
  const wrapper = mount(WorkspaceView, {global:{stubs:{AppDrawer:overlay,AppDialog:overlay,AgentSelector:true,PromptEditor:true,TaskCard:true}}}); wrappers.push(wrapper)
  await flushPromises()
  expect(wrapper.find('[aria-label="文案类型"]').exists()).toBe(true)
  expect(wrapper.findComponent(PromptEditor).exists()).toBe(false)
  expect(wrapper.find('[aria-label="目标人群"]').exists()).toBe(false)
  await findButton(wrapper, '确认费用并生成').trigger('click'); await flushPromises()
  const { audience: _retired, ...remaining } = parameters
  expect(api.quote).toHaveBeenLastCalledWith(expect.objectContaining({input:expect.objectContaining({parameters:remaining,instruction:''})}))
  expect(draft.confirmed?.input.parameters).toEqual(remaining)
  expect(draft.confirmed?.input.instruction).toBe('')
  expect(draft.confirmed?.input.product.audience).toBe('商品适用人群')
  expect(draft.agents['text-agent'].instruction).toBe('只写已有依据的特点')
})

it('rejects invalid maximum characters before requesting a text quote', async () => {
  api.listAgents.mockResolvedValue([{agent_id:'text-agent',kind:'copy',protocol_version:'text-agent-v1',enabled:true,input_support:{product_required_fields:['name'],min_materials:0,max_materials:3,instruction_required:false}}])
  const draft = draftFor('remediation'); draft.agentId='text-agent'; draft.agents['text-agent']={specId:'',instruction:'',parameters:{max_chars:1.5}}
  const wrapper=mount(WorkspaceView,{global:{stubs:{AppDrawer:overlay,AppDialog:overlay,AgentSelector:true,PromptEditor:true,TaskCard:true}}}); wrappers.push(wrapper)
  await flushPromises(); await findButton(wrapper,'确认费用并生成').trigger('click'); await flushPromises()
  expect(api.quote).not.toHaveBeenCalled()
  expect(wrapper.text()).toContain('最大字符数请填写正整数')
})

it('does not overwrite newer user input with a late AI suggestion', async () => {
  let resolve!: (value: {proposed:string}) => void
  api.preparePrompt.mockImplementationOnce(() => new Promise(ok => {resolve=ok}))
  const wrapper=mount(PromptEditor,{props:{modelValue:'原指令',request:{original:'原指令'} as Schema<'AssistRequest'>}}); wrappers.push(wrapper)
  await findButton(wrapper,'AI 帮我完善').trigger('click')
  await wrapper.setProps({modelValue:'用户刚修改的指令'})
  resolve({proposed:'迟到建议'}); await flushPromises()
  expect(wrapper.emitted('update:modelValue')).toBeUndefined()
})

it('keeps routine fee copy compact while retaining validation when generation is requested', async () => {
  const wrapper = mount(WorkspaceView, { global: { stubs: { AppDrawer: overlay, AppDialog: overlay, AgentSelector: true, PromptEditor: true, TaskCard: true } } }); wrappers.push(wrapper)
  await flushPromises()
  const footer = wrapper.get('.composer-footer')
  expect(footer.text()).toContain('本次费用')
  expect(footer.text()).not.toContain('完整成果保存后消费')
  expect(footer.text()).not.toContain('请上传至少')
  await findButton(wrapper, '确认费用并生成').trigger('click'); await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('请上传至少 1 张商品图片')
})

it('removes generation settings and cancels the full grouped product form without changing its saved snapshot', async () => {
  const wrapper = mount(WorkspaceView, { global: { stubs: { AppDrawer: overlay, AppDialog: overlay, AgentSelector: true, PromptEditor: true, TaskCard: true } } }); wrappers.push(wrapper)
  await flushPromises()
  expect(wrapper.find('.settings-disclosure').exists()).toBe(false)
  expect(wrapper.text()).not.toContain('请选择当前生成规格')
  expect(api.listSpecs).not.toHaveBeenCalled()
  await findButton(wrapper, '编辑资料').trigger('click')
  expect(wrapper.get('select[data-select-id="product-product_type"]').element.tagName).toBe('SELECT')
  expect(wrapper.text()).toContain('商品卖点与说明')
  expect(wrapper.text()).toContain('包装清单')
  await wrapper.get('#product-name').setValue('未保存的名字')
  await findButton(wrapper, '取消').trigger('click')
  expect(draftFor('remediation').product?.product.name).toBe('真实商品')
  expect(api.createProductVersion).not.toHaveBeenCalled()
  await findButton(wrapper, '编辑资料').trigger('click')
  expect((wrapper.get('#product-name').element as HTMLInputElement).value).toBe('真实商品')
  await wrapper.get('select[data-select-id="product-product_type"]').setValue('home')
  await wrapper.get('#product-description').setValue(' 已核对的卖点 ')
  api.createProductVersion.mockImplementation(async ({ product }) => ({ product_id: 'product', version: 'saved-version', product, created_at: '' }))
  await wrapper.get('#product-form').trigger('submit'); await flushPromises()
  expect(draftFor('remediation').product?.product.description).toBe('已核对的卖点')
  expect(draftFor('remediation').product?.product.sellingPoints).toBeUndefined()
  expect(draftFor('remediation').product?.version).toBe('saved-version')
})

it('changes specifications by enumerated product type and retains previous input across switches', async () => {
  const wrapper = mount(WorkspaceView, { global: { stubs: { AppDrawer: overlay, AppDialog: overlay, AgentSelector: true, PromptEditor: true, TaskCard: true } } }); wrappers.push(wrapper)
  await flushPromises()
  await findButton(wrapper, '编辑资料').trigger('click')
  await wrapper.get('select[data-select-id="product-product_type"]').setValue('clothing')
  expect(wrapper.find('#product-fabric').exists()).toBe(true)
  expect(wrapper.find('#product-capacity').exists()).toBe(false)
  await wrapper.get('#product-fabric').setValue('棉 95%、氨纶 5%')
  await wrapper.get('select[data-select-id="product-product_type"]').setValue('digital')
  expect(wrapper.find('#product-storage').exists()).toBe(true)
  expect(wrapper.find('#product-fabric').exists()).toBe(false)
  await wrapper.get('select[data-select-id="product-product_type"]').setValue('clothing')
  expect((wrapper.get('#product-fabric').element as HTMLInputElement).value).toBe('棉 95%、氨纶 5%')
  api.createProductVersion.mockImplementation(async ({ product }) => ({ product_id: 'product', version: 'saved', product, created_at: '' }))
  await wrapper.get('#product-form').trigger('submit'); await flushPromises()
  expect(api.createProductVersion.mock.calls[0][0].product).toMatchObject({product_type:'clothing', category:'服饰内衣', fabric:'棉 95%、氨纶 5%'})
  expect(api.createProductVersion.mock.calls[0][0].product).not.toHaveProperty('storage')
})

it('keeps compact output complete in its explicit preview', async () => {
  const text = '一份完整商品文案。'.repeat(60)
  const wrapper = mount(ResultViewer, { props: { compact: true, work: { work_id: 'work', kind: 'copy', items: [{ file_id: 'file', text }] } as Schema<'WorkView'> }, global: { stubs: { AppDialog: overlay } } }); wrappers.push(wrapper)
  expect(wrapper.classes()).toContain('compact')
  await findButton(wrapper, '预览').trigger('click')
  expect(wrapper.findAll('.copy-result').at(-1)?.text()).toBe(text)
})

it('shows saved creation facts in full without the retired SKU and keeps image controls within product information', async () => {
  const product = { name: '真实商品', brand: '真实品牌', model: 'SKU-123', material: '陶瓷', color: '奶油白', size: '12cm', weight: '300g', package: '杯子和杯盖', audience: '日常使用者', notes: '完整说明。'.repeat(120) }
  draftFor('remediation').product!.product = product
  const wrapper = mount(WorkspaceView, { global: { stubs: { AppDrawer: overlay, AppDialog: overlay, AgentSelector: true, PromptEditor: true, TaskCard: true } } }); wrappers.push(wrapper)
  await flushPromises()
  const information = wrapper.get('[aria-label="商品资料"]')
  for (const [key, value] of Object.entries(product)) if (key !== 'model') expect(information.text()).toContain(value)
  expect(information.text()).not.toContain('SKU-123')
  expect(draftFor('remediation').product!.product.model).toBe('SKU-123')
  expect(information.find('#material-upload').exists()).toBe(true)
  expect(wrapper.text()).not.toContain('准备本次创作')
  expect(wrapper.text()).not.toContain('选择创作类型')
})

it('omits optional SKU from product editing and a new saved version without rewriting the old product', async () => {
  const oldProduct = { name: '真实商品', product_type: 'home', category: '家居日用', model: 'SKU-123', notes: '保留商品事实' }
  draftFor('remediation').product!.product = oldProduct
  const wrapper = mount(WorkspaceView, { global: { stubs: { AppDrawer: overlay, AppDialog: overlay, AgentSelector: true, PromptEditor: true, TaskCard: true } } }); wrappers.push(wrapper)
  await flushPromises()
  await findButton(wrapper, '编辑资料').trigger('click')
  expect(wrapper.find('#product-model').exists()).toBe(false)
  expect(wrapper.get('#product-form').text()).not.toContain('SKU')
  api.createProductVersion.mockImplementation(async ({ product }) => ({ product_id: 'product', version: 'without-sku', product, created_at: '' }))
  await wrapper.get('#product-form').trigger('submit'); await flushPromises()
  expect(api.createProductVersion.mock.calls[0][0].product).not.toHaveProperty('model')
  expect(draftFor('remediation').product!.product.notes).toBe('保留商品事实')
  expect(oldProduct.model).toBe('SKU-123')
})


it('quotes by selected agent without a spec and drops restored legacy parameters for a new creation', async () => {
  const draft = draftFor('remediation')
  draft.materials = [{file_id: 'material', version: 'm1'}]
  draft.agents['image-agent'].specId = 'retired-spec'
  api.quote.mockResolvedValue({credits: 0})
  const wrapper = mount(WorkspaceView, { global: { stubs: { AppDrawer: overlay, AppDialog: overlay, AgentSelector: true, PromptEditor: true, TaskCard: true } } }); wrappers.push(wrapper)
  await flushPromises()
  await findButton(wrapper, '确认费用并生成').trigger('click'); await flushPromises()
  expect(api.quote).toHaveBeenCalledWith({agent_id:'image-agent', input:{product_version:'version',product:{name:'真实商品',sellingPoints:'原卖点'},instruction:'',parameters:{},material_versions:[{file_id:'material',version:'m1'}]}})
  expect(api.listSpecs).not.toHaveBeenCalled()
  expect(wrapper.text()).toContain('本次报价为 0 积分，不冻结或扣除积分。')
  expect(findButton(wrapper, '确认生成').attributes('disabled')).toBeUndefined()
  expect(wrapper.text()).not.toContain('确认并冻结积分')
})
