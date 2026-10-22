import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { reactive, ref } from 'vue'
import type { Schema } from '../../src/types/api'
const api = vi.hoisted(() => ({ getProductVersion: vi.fn(), createProductVersion: vi.fn(), createConversation: vi.fn(), quote: vi.fn(), regenerationQuote: vi.fn(), submitTaskIntent: vi.fn(), preparePrompt: vi.fn(), uploadFile: vi.fn(), getWork: vi.fn() }))
const route = reactive({ params: { conversationId: '' }, query: { task: undefined as string | undefined }, path: '' })
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ push: vi.fn(async (path: string) => { route.path = path; route.params.conversationId = path.split('/').at(-1)!; route.query.task = undefined }), replace: vi.fn(async location => { route.query.task = location.query.task }) }) }))
vi.mock('../../src/api/conversations', () => ({ getProductVersion: api.getProductVersion, createProductVersion: api.createProductVersion, createConversation: api.createConversation }))
vi.mock('../../src/api/catalog', () => ({ listAgents: vi.fn(async () => [{agent_id:'copy',name:'文案',kind:'copy',enabled:true,protocol_version:'text-agent-v1',input_support:{product_required_fields:['name'],min_materials:0,max_materials:3,instruction_required:false}}]), quote: api.quote }))
vi.mock('../../src/api/tasks', () => ({ submitTaskIntent: api.submitTaskIntent, getRegenerationQuote: api.regenerationQuote }))
vi.mock('../../src/api/assist', () => ({ preparePrompt: api.preparePrompt }))
vi.mock('../../src/api/works', () => ({ getWork: api.getWork }))
vi.mock('../../src/api/files', () => ({ uploadFile: api.uploadFile, fileContentUrl: (id: string) => '/files/' + id }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: ref(1), profile: ref({user_id:'task-composer'}),refreshAccount:vi.fn(async()=>{}) }, onIdentityChange:()=>()=>{} }))
vi.mock('../../src/features/workspace/useTaskStream', () => {
 const stream = {latestTaskId:ref(''),tasks:ref([]),details:ref({}),fragments:ref({}),connectionState:ref('open'),reconnect:vi.fn(),refreshTask:vi.fn(async()=>{})}
 return {useTaskStream:()=>stream}
})
import WorkspaceView from '../../src/features/workspace/WorkspaceView.vue'
import { draftFor, taskDraftFor } from '../../src/features/workspace/drafts'
import { useTaskStream } from '../../src/features/workspace/useTaskStream'
import { ApiError, createIntent } from '../../src/api/client'
import { listAgents } from '../../src/api/catalog'
const stream = useTaskStream('')
const wrappers: VueWrapper[]=[]
const detail = (id: string) => ({conversation_id:route.params.conversationId,agent_id:'copy',task:{task_id:id,state_version:1,work_ids:[]},input:{product_version:id+'-pv',product:{name:id+'商品',product_type:'home',description:'耐用'},instruction:id+'指令',parameters:{tone:'亲切',max_chars:40},material_versions:[{file_id:id+'图片',version:'1'}]}} as unknown as Schema<'TaskDetail'>)
function render(realPrompt = false){const w=mount(WorkspaceView,{global:{stubs:{TaskCard:true,QuotePanel:true,PromptEditor:!realPrompt}}});wrappers.push(w);return w}
beforeEach(()=>{vi.clearAllMocks();route.params.conversationId=crypto.randomUUID();route.path='/workspace/'+route.params.conversationId;route.query.task=undefined;stream.tasks.value=[];stream.details.value={};stream.latestTaskId.value='';api.getProductVersion.mockImplementation(async version=>({product_id:'p',version,created_at:'',product:{name:'另一个商品'}}));api.quote.mockResolvedValue({credits:8});api.createProductVersion.mockImplementation(async body=>({product_id:'p',version:'new-pv',created_at:'',product:body.product}))})
afterEach(()=>{wrappers.splice(0).forEach(w=>w.unmount());vi.useRealTimers()})
it('defaults an empty independent task to the available copy agent',async()=>{const w=render();await flushPromises();expect(w.get('[aria-pressed="true"]').text()).toBe('文案');expect(draftFor(route.params.conversationId).agentId).toBe('copy')})

it('caps new references at four even when the agent supports more, while retaining legacy references', async () => {
 const [agent] = await listAgents()
 vi.mocked(listAgents).mockResolvedValueOnce([{ ...agent!, input_support: { ...agent!.input_support, max_materials: 20 } }])
 const d = draftFor(route.params.conversationId)
 d.product = { product_id: 'p', version: 'pv', created_at: '', product: { name: '商品', product_type: 'home' } }
 d.materials = Array.from({ length: 3 }, (_, index) => ({ file_id: `reference-${index}`, version: 'v1' }))
 api.uploadFile.mockResolvedValue({ file_id: 'fourth', version: 'v1' })
 const w = render(); await flushPromises()
 const upload = w.get<HTMLInputElement>('#material-upload')
 expect(upload.element.disabled).toBe(false)
 Object.defineProperty(upload.element, 'files', { configurable: true, value: [new File(['image'], 'reference.png', { type: 'image/png' })] })
 await upload.trigger('change'); await flushPromises()
 expect(d.materials).toHaveLength(4)
 expect(upload.element.disabled).toBe(true)
 // A forced event cannot bypass the UI limit.
 upload.element.disabled = false
 await upload.trigger('change'); await flushPromises()
 expect(api.uploadFile).toHaveBeenCalledTimes(1)
 expect(d.materials).toHaveLength(4)
 d.materials.push({ file_id: 'legacy-fifth', version: 'v1' }); await flushPromises()
 expect(w.findAll('.material-row')).toHaveLength(5)
 api.quote.mockClear()
 await w.get('.generate-button').trigger('click'); await flushPromises()
 expect(w.text()).toContain('最多支持 4 张')
 expect(api.quote).not.toHaveBeenCalled()
 expect(d.materials).toHaveLength(5)
})
it.each([true,false])('locks every input of an existing task, including type switching (explicit link: %s)',async explicit=>{
 const original=detail('locked');stream.details.value={locked:original};stream.latestTaskId.value='locked';if(explicit)route.query.task='locked'
 const w=render(true);await flushPromises()
 expect(w.get('.product-details').text()).toContain('locked商品')
 expect(w.get('.composer-tabs').attributes('disabled')).toBeDefined()
 expect(w.get('.composer-form').attributes('disabled')).toBeDefined()
 expect(w.find('#creation-instruction').exists()).toBe(false)
 expect(taskDraftFor(route.params.conversationId,'locked').agents.copy.instruction).toBe('locked指令')
 expect(w.get('[aria-label="文案类型"]').element.matches(':disabled')).toBe(true)
 expect(w.findAll('.agent-types button').every(b=>b.element.matches(':disabled'))).toBe(true)
 expect(w.find('.assist-button').exists()).toBe(false)
 expect(w.findAll('button').some(b=>b.text()==='编辑资料')).toBe(false)
 expect(w.get('.generate-button').element.matches(':disabled')).toBe(false)
 expect(api.quote).not.toHaveBeenCalled()
})
it('locks a known latest task while its details are still loading',async()=>{
 stream.latestTaskId.value='loading-task'
 const w=render();await flushPromises()
 expect(w.get('.composer-tabs').attributes('disabled')).toBeDefined()
 expect(w.get('.composer-form').attributes('disabled')).toBeDefined()
 expect(w.get('.generate-button').element.matches(':disabled')).toBe(true)
})
it('copies selected task input rather than another draft and keeps historical input immutable',async()=>{
 api.createConversation.mockResolvedValue({conversation_id:'copied-task-draft'})
 const original=detail('old');stream.details.value={old:original};stream.latestTaskId.value='old';route.query.task='old'
 const unrelated=draftFor(route.params.conversationId);unrelated.agentId='other';unrelated.product={product_id:'p2',version:'other-pv',created_at:'',product:{name:'其他草稿'}}
 const w=render();await flushPromises();expect(w.get('.product-details').text()).toContain('old商品');expect(w.get('.generate-button').text()).toBe('基于此任务再生成')
 expect(api.getProductVersion).toHaveBeenCalledExactlyOnceWith('old-pv')
 expect(api.quote).not.toHaveBeenCalled()
 await w.get('.generate-button').trigger('click');await flushPromises()
 expect(w.find('[role="dialog"]').exists()).toBe(false);expect(api.submitTaskIntent).not.toHaveBeenCalled();expect(unrelated.product!.product.name).toBe('其他草稿')
 await w.findAll('button').find(b=>b.text()==='编辑资料')!.trigger('click');await w.get('#product-name').setValue('修改后的新商品');await w.get('#product-form').trigger('submit');await flushPromises()
 expect(original.input.product.name).toBe('old商品')
})
it('blocks regeneration when its product snapshot cannot be read, then retries the same snapshot',async()=>{
 stream.details.value={old:detail('old')};route.query.task='old';api.getProductVersion.mockRejectedValue(new Error('offline'))
 const w=render();await flushPromises();expect(w.get('.generate-button').attributes('disabled')).toBeDefined();expect(api.quote).not.toHaveBeenCalled()
 api.getProductVersion.mockResolvedValue({product_id:'p',version:'old-pv',created_at:'',product:{name:'其他资料'}})
 await w.findAll('button').find(b=>b.text()==='重试回填资料')!.trigger('click');await flushPromises()
 expect(w.get('.product-details').text()).toContain('old商品');expect(w.get('.generate-button').attributes('disabled')).toBeUndefined()
})

it('regenerates in a separate draft and submits a new task without changing its source',async()=>{
 const original=detail('old');const snapshot=JSON.stringify(original);const originalConversation=route.params.conversationId
 stream.details.value={old:original};route.query.task='old'
 api.createConversation.mockResolvedValue({conversation_id:'independent-regeneration'})
 api.submitTaskIntent.mockResolvedValue({task:{task_id:'new-task'}})
 const w=render();await flushPromises()
 await w.get('.generate-button').trigger('click');await flushPromises()
 expect(route.params.conversationId).toBe('independent-regeneration');expect(route.query.task).toBeUndefined()
 expect(w.find('[role="dialog"]').exists()).toBe(false)
 const source=taskDraftFor(originalConversation,'old'),copy=draftFor('independent-regeneration')
 expect(copy).not.toBe(source);expect(copy.agents.copy).not.toBe(source.agents.copy)
 expect(copy.product!.product).not.toBe(source.product!.product)
 expect(copy.materials).not.toBe(source.materials)
 await w.get('.generate-button').trigger('click');await flushPromises()
 expect(w.get('[role="dialog"]').text()).toContain('再次收费')
 await w.findAll('button').find(b=>b.text()==='确认并冻结积分')!.trigger('click');await flushPromises()
 const intent=api.submitTaskIntent.mock.calls[0][0]
 expect(JSON.parse(intent.body)).toMatchObject({conversation_id:'independent-regeneration',input:{instruction:''}})
 expect(intent.key).toBeTruthy();expect(route.query.task).toBe('new-task')
 expect(JSON.stringify(original)).toBe(snapshot);expect(source.pending).toBeUndefined();expect(source.confirmed).toBeUndefined()
})

it.each([0, 8])('confirms the server-calculated regeneration charge (%s credits) and retains the source', async credits => {
 const original = detail('free-source'); original.task.state = 'SUCCEEDED'
 stream.details.value = { 'free-source': original }; route.query.task = 'free-source'
 api.createConversation.mockResolvedValue({ conversation_id: 'regeneration-' + credits })
 api.regenerationQuote.mockResolvedValue({ quote: { credits: 8 }, credits, eligible: true, free_regenerations_used: credits ? 3 : 1, free_regenerations_remaining: credits ? 0 : 2 })
 api.submitTaskIntent.mockResolvedValue({ task: { task_id: 'regenerated' } })
 const w = render(); await flushPromises()
 await w.get('.generate-button').trigger('click'); await flushPromises()
 await w.get('.generate-button').trigger('click'); await flushPromises()
 expect(api.regenerationQuote).toHaveBeenCalledWith('free-source', expect.objectContaining({ input: expect.objectContaining({ instruction: 'free-source指令' }) }))
 const dialog = w.get('[role="dialog"]')
 expect(dialog.get('.charge-amount').text()).toBe(credits + ' 积分')
 expect(dialog.text()).toContain(credits ? '再次收费' : '免费重新生成')
 expect(dialog.text()).toContain(credits ? '按当前报价' : '不冻结或扣除积分')
 await dialog.findAll('button').find(b => b.text() === (credits ? '确认并冻结积分' : '确认免费生成'))!.trigger('click'); await flushPromises()
 const submitted = JSON.parse(api.submitTaskIntent.mock.calls[0][0].body)
 expect(submitted.regeneration).toEqual({ source_task_id: 'free-source', expected_credits: credits, expected_used: credits ? 3 : 1 })
 expect(submitted.confirmed_quote.credits).toBe(8)
 expect(original.input.instruction).toBe('free-source指令')
})

it.each([false, true])('does not label a zero standard price as free allowance (eligible: %s)', async eligible => {
 const d = draftFor(route.params.conversationId)
 Object.assign(d, { agentId: 'copy', sourceTaskId: 'source', regenerationSourceId: 'source', product: { version: 'pv', product: { name: '杯子' } }, agents: { copy: { parameters: {}, instruction: '', specId: '' } } })
 api.regenerationQuote.mockResolvedValue({ quote: { credits: 0 }, credits: 0, eligible, free_regenerations_used: 3, free_regenerations_remaining: 0 })
 const w = render(); await flushPromises(); await w.get('.generate-button').trigger('click'); await flushPromises()
 expect(w.get('[role="dialog"]').text()).not.toContain('使用 1 次免费')
 expect(w.get('[role="dialog"]').text()).toContain('本次报价为 0 积分')
})

it('refreshes a stale allowance before requesting confirmation again', async () => {
 const d = draftFor(route.params.conversationId)
 Object.assign(d, { agentId: 'copy', sourceTaskId: 'source', regenerationSourceId: 'source', product: { version: 'pv', product: { name: '杯子' } }, agents: { copy: { parameters: {}, instruction: '', specId: '' } } })
 api.regenerationQuote.mockResolvedValueOnce({ quote: { credits: 8 }, credits: 0, eligible: true, free_regenerations_used: 2, free_regenerations_remaining: 1 })
 api.regenerationQuote.mockResolvedValue({ quote: { credits: 8 }, credits: 8, eligible: true, free_regenerations_used: 3, free_regenerations_remaining: 0 })
 const stale: Schema<'ErrorResponse'> = { trace_id: 'stale', error: { code: 'QUOTE_STALE', message: '额度变化', current_quotes: null, current_specs: null } }
 api.submitTaskIntent.mockRejectedValue(new ApiError('额度变化', 409, 'QUOTE_STALE', stale))
 const w = render(); await flushPromises(); await w.get('.generate-button').trigger('click'); await flushPromises()
 await w.findAll('button').find(b => b.text() === '确认免费生成')!.trigger('click'); await flushPromises()
 expect(d.pending).toBeNull()
 await w.get('.generate-button').trigger('click'); await flushPromises()
 expect(w.get('[role="dialog"]').text()).toContain('再次收费')
 expect(w.get('.charge-amount').text()).toBe('8 积分')
})

it('does not navigate away from a newly selected task when an older work regeneration finishes loading', async () => {
 stream.details.value = { a: detail('a'), b: detail('b') }; route.query.task = 'a'
 let resolve!: (value: unknown) => void
 api.getWork.mockReturnValue(new Promise(done => { resolve = done }))
 const w = render(); await flushPromises()
 w.findComponent({ name: 'TaskCard' }).vm.$emit('regenerate', { work_id: 'work-a' }); await flushPromises()
 route.query.task = 'b'; await flushPromises()
 resolve({ work_id: 'work-a', source: { input: { product_version: 'a-pv' } } }); await flushPromises()
 expect(route.query.task).toBe('b')
 expect(api.createConversation).not.toHaveBeenCalled()
})

it('also forks when reopening an existing conversation without a task query',async()=>{
 const original=detail('latest');stream.details.value={latest:original};stream.latestTaskId.value='latest'
 const base=draftFor(route.params.conversationId);base.agentId='copy';base.agents.copy={instruction:'新指令',specId:'',parameters:{}}
 api.createConversation.mockResolvedValue({conversation_id:'forked-resumed-task'})
 const w=render();await flushPromises();await w.get('.generate-button').trigger('click');await flushPromises()
 expect(route.params.conversationId).toBe('forked-resumed-task')
 expect(draftFor('forked-resumed-task').sourceTaskId).toBe('latest')
 expect(w.find('[role="dialog"]').exists()).toBe(false)
 expect(draftFor('forked-resumed-task').agents.copy.instruction).toBe('latest指令')
 expect(base.confirmed).toBeUndefined()
})
it('ignores an old snapshot response after selecting a different task',async()=>{
 stream.details.value={a:detail('a'),b:detail('b')};route.query.task='a';let finish!:(value:unknown)=>void
 api.getProductVersion.mockImplementation(version=>version==='a-pv'?new Promise(resolve=>{finish=resolve}):Promise.resolve({product_id:'p',version,created_at:'',product:{name:'错误内容'}}))
 const w=render();await flushPromises();route.query.task='b';await flushPromises();finish({product_id:'p',version:'a-pv',created_at:'',product:{name:'迟到'}});await flushPromises()
 expect(w.get('.product-details').text()).toContain('b商品');expect(w.get('.product-details').text()).not.toContain('a商品')
})
it.each(['success','rejected','stale'] as const)('finishes original-intent recovery visibly after following an older task link (%s)',async outcome=>{
 // Isolate this original-intent recovery from the selected draft's independent
 // 200ms automatic quote. An explicit stale-response refresh would still run.
 vi.useFakeTimers()
 const original=draftFor(route.params.conversationId)
 original.agentId='copy';original.confirmed={conversation_id:route.params.conversationId,agent_id:'copy',input:detail('pending').input,confirmed_quote:{credits:8}} as Schema<'SubmitTaskRequest'>
 original.confirmed.input.parameters.audience='历史受众'
 original.pending=createIntent(original.confirmed)
 const persistedBody=original.pending.body
 stream.details.value={old:detail('old')};route.query.task='old'
 if(outcome==='success') api.submitTaskIntent.mockResolvedValue({task:{task_id:'admitted'}})
 else {const code=outcome==='stale'?'QUOTE_STALE':'INSUFFICIENT_CREDITS';api.submitTaskIntent.mockRejectedValue(new ApiError('原请求未受理',402,code,{trace_id:'test-only',error:{code,message:'原请求未受理',current_quotes:null,current_specs:null}}))}
 const w=render();await flushPromises()
 await w.findAll('button').find(b=>b.text()==='核对并重试原请求')!.trigger('click');await flushPromises();expect(w.find('[role="dialog"]').exists()).toBe(true)
 await w.findAll('button').find(b=>b.text()==='确认并冻结积分')!.trigger('click');await flushPromises()
 expect(api.submitTaskIntent.mock.calls[0][0].body).toBe(persistedBody)
 expect(original.pending).toBeNull();expect(w.find('[role="dialog"]').exists()).toBe(false)
 if(outcome==='success') expect(route.query.task).toBe('admitted')
 else expect(w.get('.composer-recovery').text()).toContain(outcome==='stale'?'报价已更新':'原请求未受理')
 if(outcome==='stale') {
  expect(api.quote).not.toHaveBeenCalled()
  await vi.advanceTimersByTimeAsync(200);await flushPromises()
  expect(api.quote).not.toHaveBeenCalled()
 }
})
it('replaces an old editable task cache with its persisted input and keeps both selections read only',async()=>{
 const cache=taskDraftFor(route.params.conversationId,'a');cache.sourceTaskId='a';cache.product={product_id:'p',version:'changed',created_at:'',product:{name:'旧版缓存改稿'}}
 stream.details.value={a:detail('a'),b:detail('b')};route.query.task='a';const w=render();await flushPromises()
 expect(w.get('.product-details').text()).toContain('a商品')
 route.query.task='b';await flushPromises();expect(w.get('.product-details').text()).toContain('b商品')
 route.query.task='a';await flushPromises();expect(w.get('.product-details').text()).toContain('a商品')
 expect(w.get('.composer-form').attributes('disabled')).toBeDefined()
})
it('keeps historical instructions immutable while exposing no retired instruction editor in a copied draft',async()=>{
 const oldConversation=route.params.conversationId;stream.details.value={a:detail('a')};route.query.task='a'
 api.createConversation.mockResolvedValue({conversation_id:'assisted-draft'})
 const w=render(true);await flushPromises();await w.get('.generate-button').trigger('click');await flushPromises()
 expect(w.find('#creation-instruction').exists()).toBe(false)
 expect(w.findAll('button').some(b=>b.text()==='AI 帮我完善')).toBe(false)
 expect(draftFor('assisted-draft').agents.copy.instruction).toBe('a指令')
 route.params.conversationId=oldConversation;route.query.task='a';await flushPromises()
 expect(w.find('.undo-button').exists()).toBe(false)
 expect(w.find('#creation-instruction').exists()).toBe(false)
 expect(taskDraftFor(oldConversation,'a').agents.copy.instruction).toBe('a指令')
 expect(draftFor('assisted-draft').agents.copy.instruction).toBe('a指令')
})
it.each([['重复描述','重复描述',false],['商品说明','不同历史卖点',true],['','仅历史卖点',false]])('offers one main selling input and retains distinct legacy points (%s)',async(description,sellingPoints,hasLegacy)=>{
 const d=draftFor(route.params.conversationId);d.product={product_id:'p',version:'pv',created_at:'',product:{name:'商品',product_type:'home',description,sellingPoints}}
 const w=render();await flushPromises();await w.findAll('button').find(b=>b.text()==='编辑资料')!.trigger('click');expect(w.find('#product-sellingPoints').exists()).toBe(hasLegacy);expect((w.get('#product-description').element as HTMLTextAreaElement).value).toBe(description||sellingPoints)
 await w.get('#product-form').trigger('submit');await flushPromises();expect(api.createProductVersion.mock.calls[0][0].product).toMatchObject({description:description||sellingPoints});expect(api.createProductVersion.mock.calls[0][0].product.sellingPoints).toBe(hasLegacy?sellingPoints:undefined)
})
