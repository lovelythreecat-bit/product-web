import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ApiError } from '../../src/api/client'

const api = vi.hoisted(() => ({getMediaConnection:vi.fn(),saveMediaConnection:vi.fn(),
  getVideoModels:vi.fn(),saveVideoModel:vi.fn(),getMediaResource:vi.fn(),saveMediaResource:vi.fn()}))
vi.mock('../../src/api/mediaAgents',()=>api)
import VideoAgentConfigs from '../../src/features/admin/VideoAgentConfigs.vue'

const connection={revision:2,base_url:'https://video.example',has_service_key:true,has_management_key:true}
const models={revision:2,configuration_revision:4,models:{planner:null,video:{profile_id:'v1',version:3,
  adapter:'wan',base_url:'https://wan.example/api/v1',model:'wan-model',enabled:true,has_api_key:true,max_segment_seconds:5},visual:null},
  bindings:{configuration_revision:4,planner:{adapter:'fake',profile_id:null},video:{adapter:'wan',profile_id:'v1'},
    visual:{adapter:'none',profile_id:null},voice:{adapter:'fake',profile_id:null},music:{adapter:'fake',profile_id:null}}}
beforeEach(()=>{vi.clearAllMocks();api.getMediaConnection.mockResolvedValue(connection);api.getVideoModels.mockResolvedValue(models)})

it('keeps the saved connection visible when the upstream management key is rejected',async()=>{
  api.getVideoModels.mockRejectedValueOnce(new ApiError('请配置视频管理 Key。',503))
  const wrapper=mount(VideoAgentConfigs);await flushPromises()
  expect(wrapper.text()).toContain(connection.base_url)
  expect(wrapper.text()).toContain('请配置视频管理 Key。')
  await wrapper.get('[data-configure-connection]').trigger('click');await flushPromises()
  expect((wrapper.get('#media-service-url').element as HTMLInputElement).value).toBe(connection.base_url)
  wrapper.unmount()
})

it('presents the actual three model uses without profile creation, manual bindings or JSON',async()=>{
  const wrapper=mount(VideoAgentConfigs);await flushPromises()
  for(const name of ['分镜文本模型','视频生成模型','视觉检查模型']) expect(wrapper.text()).toContain(name)
  for(const name of ['角色绑定','适配器能力','新增模型配置','JSON']) expect(wrapper.text()).not.toContain(name)
  expect(wrapper.text()).toContain('wan-model');wrapper.unmount()
})

it('reads fresh settings, preserves omitted key and sends the actual wan segment limit',async()=>{
  const wrapper=mount(VideoAgentConfigs);await flushPromises()
  await wrapper.get('[data-configure-video]').trigger('click');await flushPromises()
  expect(api.getVideoModels).toHaveBeenCalledTimes(2)
  expect((wrapper.get('#video-model-key').element as HTMLInputElement).value).toBe('')
  await wrapper.get('#video-segment-seconds').setValue(10)
  api.saveVideoModel.mockResolvedValue(models)
  await wrapper.get('#video-model-form').trigger('submit');await flushPromises()
  expect(api.saveVideoModel).toHaveBeenCalledWith('video',expect.objectContaining({
    expected_revision:2,expected_configuration_revision:4,expected_profile_id:'v1',expected_profile_version:3,
    adapter:'wan',max_segment_seconds:10}))
  expect(api.saveVideoModel.mock.calls[0][1]).not.toHaveProperty('api_key')
  wrapper.unmount()
})

it('requires a new key on provider change and preserves conflicting drafts until reopened',async()=>{
  const wrapper=mount(VideoAgentConfigs);await flushPromises()
  await wrapper.get('[data-configure-video]').trigger('click');await flushPromises()
  await wrapper.get('select[data-select-id="video-provider"]').setValue('seedance');await flushPromises()
  expect(wrapper.find('#video-segment-seconds').exists()).toBe(false)
  expect(wrapper.get('#video-model-key').attributes('required')).toBeDefined()
  await wrapper.get('#video-model-key').setValue('TEST_ONLY_new_key')
  api.saveVideoModel.mockRejectedValue(new ApiError('冲突',409))
  await wrapper.get('#video-model-form').trigger('submit');await flushPromises()
  expect(wrapper.text()).toContain('关闭后重新打开')
  expect(wrapper.get('[data-save-video-model]').attributes('disabled')).toBeDefined()
  expect((wrapper.get('#video-model-key').element as HTMLInputElement).value).toBe('TEST_ONLY_new_key')
  await wrapper.findAll('button').find(button=>button.text()==='取消')!.trigger('click');await flushPromises()
  await wrapper.get('[data-configure-video]').trigger('click');await flushPromises()
  expect((wrapper.get('#video-model-key').element as HTMLInputElement).value).toBe('')
  wrapper.unmount()
})
