import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { ApiError } from '../../src/api/client'

const api = vi.hoisted(() => ({ getMediaConnection: vi.fn(), saveMediaConnection: vi.fn(),
  getVideoModels: vi.fn(),
  listMediaResources: vi.fn(), getMediaResource: vi.fn(), saveMediaResource: vi.fn(),
  loadMediaOptions: vi.fn(), recordId: (row: {id?:string;profile_id?:string}) => row.id ?? row.profile_id ?? '' }))
vi.mock('../../src/api/mediaAgents', () => api)
import MediaAgentConfigs from '../../src/features/admin/MediaAgentConfigs.vue'
import MediaResourceEditor from '../../src/features/admin/MediaResourceEditor.vue'

const connection = { id:'c1', kind:'image', base_url:'https://images.example', revision:2,
  has_service_key:true, has_management_key:false, default_config_id:null, image_model:null }
const service = { id:'s1', name:'图片服务', protocol:'openai_images', base_url:'https://provider.example',
  generation_path:null, edit_path:null, chat_path:'/chat/completions', enabled:true, has_api_key:true, version:3 }
const model = { id:'m1', service_id:'s1', model:'image-model', description:'模型', enabled:true, version:2 }
const scheme = { id:'a1', name:'上新方案', image_models:{fast:'m1'}, stages:{vision:'m2',custom:'m3'},
  parameters:{request_timeout_seconds:180,model_concurrency:2,generation_reference_limit:4,
    vision_image_limit:12,model_completion_attempts:4,http_proxy:null}, enabled:true, version:5 }
const drawer = defineComponent({props:['open'],emits:['update:open'],
  template:'<section v-if="open"><button data-close @click="$emit(\'update:open\',false)">取消</button><slot/><slot name="actions"/></section>'})
const global = { stubs:{AppDrawer:drawer} }
beforeEach(() => { vi.clearAllMocks(); api.getMediaConnection.mockResolvedValue(connection)
  api.getVideoModels.mockResolvedValue({revision:2,configuration_revision:1,models:{planner:null,video:null,visual:null},bindings:{}})
  api.listMediaResources.mockResolvedValue([service]); api.getMediaResource.mockResolvedValue({...service,version:7})
  api.loadMediaOptions.mockImplementation((_kind:string,resource:string) => Promise.resolve(
    resource==='agent-configs'?[scheme]:resource==='model-configs'?[model]:resource==='services'?[service]:[])) })

it('loads the latest video connection on opening and preserves omitted keys', async () => {
  const wrapper=mount(MediaAgentConfigs,{props:{kind:'video'},global});await flushPromises()
  api.getMediaConnection.mockResolvedValue({...connection,revision:6})
  await wrapper.get('[data-configure-connection]').trigger('click');await flushPromises()
  expect(api.getMediaConnection).toHaveBeenCalledTimes(2)
  expect((wrapper.get('#media-service-key').element as HTMLInputElement).value).toBe('')
  api.saveMediaConnection.mockResolvedValue({...connection,revision:7})
  await wrapper.get('#video-connection-form').trigger('submit');await flushPromises()
  expect(api.saveMediaConnection).toHaveBeenCalledWith('video',expect.objectContaining({expected_revision:6}))
  expect(api.saveMediaConnection.mock.calls[0][1]).not.toHaveProperty('service_key')
  wrapper.unmount()
})

it('retains conflicting connection input, clears secrets when closed, and has no version review action', async () => {
  const wrapper=mount(MediaAgentConfigs,{props:{kind:'video'},global});await flushPromises()
  await wrapper.get('[data-configure-connection]').trigger('click');await flushPromises()
  await wrapper.get('#media-service-url').setValue('https://new.example')
  await wrapper.get('#media-service-key').setValue('private-replacement')
  api.saveMediaConnection.mockRejectedValue(new ApiError('配置已更新',409))
  await wrapper.get('#video-connection-form').trigger('submit');await flushPromises()
  expect(wrapper.text()).toContain('关闭后重新打开')
  expect((wrapper.get('#media-service-url').element as HTMLInputElement).value).toBe('https://new.example')
  expect(wrapper.get('[data-save-connection]').attributes('disabled')).toBeDefined()
  expect(wrapper.text()).not.toContain('核对版本')
  await wrapper.get('[data-close]').trigger('click')
  await wrapper.get('[data-configure-connection]').trigger('click');await flushPromises()
  expect((wrapper.get('#media-service-key').element as HTMLInputElement).value).toBe('')
  wrapper.unmount()
})

it('routes video configuration to actual model uses without a resource list', async () => {
  const wrapper=mount(MediaAgentConfigs,{props:{kind:'video'},global});await flushPromises()
  expect(wrapper.text()).toContain('分镜文本模型');expect(wrapper.text()).toContain('视频生成模型')
  expect(api.listMediaResources).not.toHaveBeenCalled()
  expect(wrapper.find('[data-load-more]').exists()).toBe(false);wrapper.unmount()
})

it('fetches current resource on opening and submits its native hidden version without blank key', async () => {
  const wrapper=mount(MediaResourceEditor,{props:{kind:'image',resource:'services',record:service},global})
  await flushPromises();expect(api.getMediaResource).toHaveBeenCalledWith('image','services','s1')
  await wrapper.get('#media-resource-name').setValue('新服务名称')
  api.saveMediaResource.mockRejectedValue(new ApiError('冲突',409))
  await wrapper.get('#media-resource-form').trigger('submit');await flushPromises()
  expect(api.saveMediaResource).toHaveBeenCalledWith('image','services','s1',expect.objectContaining({version:7,name:'新服务名称'}),false)
  expect(api.saveMediaResource.mock.calls[0][3]).not.toHaveProperty('api_key')
  expect((wrapper.get('#media-resource-name').element as HTMLInputElement).value).toBe('新服务名称')
  expect(wrapper.text()).toContain('关闭后重新打开');wrapper.unmount()
})

it('preserves non-vision image stages and runtime settings while selecting models', async () => {
  api.getMediaResource.mockResolvedValue(scheme)
  const wrapper=mount(MediaResourceEditor,{props:{kind:'image',resource:'agent-configs',record:scheme},global})
  await flushPromises();await wrapper.get('#media-resource-name').setValue('新方案名称')
  api.saveMediaResource.mockResolvedValue({...scheme,name:'新方案名称'})
  await wrapper.get('#media-resource-form').trigger('submit');await flushPromises()
  expect(api.saveMediaResource.mock.calls[0][3]).toMatchObject({version:5,stages:{vision:'m2',custom:'m3'},
    parameters:scheme.parameters,image_models:{fast:'m1'}});wrapper.unmount()
})

it('filters discovered adapters by role and preserves video parameters with write-only keys', async () => {
  api.listMediaResources.mockResolvedValue([
    {adapter:'openai_chat',roles:['planner'],required_fields:['base_url','api_key','model'],secret_fields:['api_key']},
    {adapter:'wan',roles:['video'],required_fields:['base_url','api_key','model','max_segment_seconds'],secret_fields:['api_key']},
  ])
  const profile={profile_id:'p1',name:'视频模型',role:'video' as const,adapter:'wan',base_url:'https://video.example/v1',
    model:'wan-model',parameters:{max_segment_seconds:5,custom_parameter:'keep'},secret_presence:{api_key:true},enabled:true,version:9}
  api.getMediaResource.mockResolvedValue(profile)
  const wrapper=mount(MediaResourceEditor,{props:{kind:'video',resource:'model-profiles',record:profile},global})
  await flushPromises()
  expect(wrapper.get('select[data-select-id="media-video-adapter"]').text()).toContain('wan')
  expect(wrapper.get('select[data-select-id="media-video-adapter"]').text()).not.toContain('openai_chat')
  expect((wrapper.get('#media-secret-api_key').element as HTMLInputElement).value).toBe('')
  await wrapper.get('#media-wan-seconds').setValue(7)
  api.saveMediaResource.mockResolvedValue(profile)
  await wrapper.get('#media-resource-form').trigger('submit');await flushPromises()
  expect(api.saveMediaResource.mock.calls[0][3]).toMatchObject({expected_version:9,
    parameters:{max_segment_seconds:7,custom_parameter:'keep'}})
  expect(api.saveMediaResource.mock.calls[0][3]).not.toHaveProperty('secrets')
  await wrapper.get('select[data-select-id="media-video-role"]').setValue('planner');await flushPromises()
  expect(wrapper.get('select[data-select-id="media-video-adapter"]').text()).toContain('openai_chat')
  expect(wrapper.get('select[data-select-id="media-video-adapter"]').text()).not.toContain('wan')
  wrapper.unmount()
})

it('uses configuration_revision for five-role bindings and only lists matching profiles', async () => {
  const roles=['planner','video','voice','music','visual']
  api.getMediaResource.mockResolvedValue({configuration_revision:12,...Object.fromEntries(roles.map(role=>[role,{adapter:role==='visual'?'none':'fake',profile_id:null}]))})
  api.loadMediaOptions.mockResolvedValue([{profile_id:'vp1',name:'成片模型',role:'video',adapter:'wan',enabled:true},
    {profile_id:'pp1',name:'规划模型',role:'planner',adapter:'openai_chat',enabled:true}])
  const wrapper=mount(MediaResourceEditor,{props:{kind:'video',resource:'adapter-bindings',record:{configuration_revision:1}},global})
  await flushPromises()
  expect(wrapper.get('select[data-select-id="media-binding-video"]').text()).toContain('成片模型')
  expect(wrapper.get('select[data-select-id="media-binding-video"]').text()).not.toContain('规划模型')
  expect(wrapper.get('select[data-select-id="media-binding-planner"]').find('option[value="@none"]').exists()).toBe(false)
  await wrapper.get('select[data-select-id="media-binding-video"]').setValue('vp1')
  api.saveMediaResource.mockResolvedValue({configuration_revision:13})
  await wrapper.get('#media-resource-form').trigger('submit');await flushPromises()
  expect(api.saveMediaResource.mock.calls[0][3]).toMatchObject({expected_version:12,
    planner:{adapter:'fake',profile_id:null},video:{profile_id:'vp1'},visual:{adapter:'none',profile_id:null}})
  wrapper.unmount()
})

it('retains a creation intent for an unchanged retry and clears secret input on cancel', async () => {
  const wrapper=mount(MediaResourceEditor,{props:{kind:'image',resource:'services'},global})
  await flushPromises()
  await wrapper.get('#media-resource-name').setValue('新服务')
  await wrapper.get('#media-resource-url').setValue('https://provider.example')
  await wrapper.get('#media-resource-key').setValue('private-key')
  api.saveMediaResource.mockRejectedValue(new ApiError('网络失败'))
  await wrapper.get('#media-resource-form').trigger('submit');await flushPromises()
  await wrapper.get('#media-resource-form').trigger('submit');await flushPromises()
  expect(api.saveMediaResource.mock.calls[0][5].key).toBe(api.saveMediaResource.mock.calls[1][5].key)
  await wrapper.get('[data-close]').trigger('click');await flushPromises()
  expect((wrapper.get('#media-resource-key').element as HTMLInputElement).value).toBe('')
  wrapper.unmount()
})
