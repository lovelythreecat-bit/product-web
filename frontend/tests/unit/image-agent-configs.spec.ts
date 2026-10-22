import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { ApiError } from '../../src/api/client'

const api = vi.hoisted(() => ({ getMediaConnection: vi.fn(), saveMediaConnection: vi.fn(),
  getImageModels: vi.fn(), saveImageModels: vi.fn() }))
vi.mock('../../src/api/mediaAgents', () => api)
import ImageAgentConfigs from '../../src/features/admin/ImageAgentConfigs.vue'

const connection = { id:'c',kind:'image',base_url:'https://agent.example',revision:2,
  has_service_key:true,has_management_key:false,default_config_id:'a',image_model:'fast' }
const models = { revision:2,versions:{'/api/v1/agent-configs/a':1},
  text_model:{base_url:'https://text.example/v1',model:'vision',protocol:'chat_completions',has_api_key:true,enabled:true},
  image_model:{base_url:'https://image.example/v1',model:'image',protocol:'openai_images',has_api_key:true,enabled:true} }
const drawer = defineComponent({props:['open'],emits:['update:open'],
  template:'<section v-if="open"><button data-close @click="$emit(\'update:open\',false)">取消</button><slot/><slot name="actions"/></section>'})
const global = { stubs:{AppDrawer:drawer} }
beforeEach(() => { vi.clearAllMocks();api.getMediaConnection.mockResolvedValue(connection)
  api.getImageModels.mockResolvedValue(structuredClone(models)) })

it('shows only two model roles and opens current settings with blank keys', async () => {
  const wrapper=mount(ImageAgentConfigs,{global});await flushPromises()
  expect(wrapper.text()).toContain('文字模型');expect(wrapper.text()).toContain('图片生成模型')
  for(const old of ['Agent 方案','生图别名','视觉阶段模型','服务配置']) expect(wrapper.text()).not.toContain(old)
  api.getImageModels.mockResolvedValue({...models,revision:7})
  await wrapper.get('[data-configure-image-models]').trigger('click');await flushPromises()
  expect(api.getImageModels).toHaveBeenCalledTimes(2)
  expect((wrapper.get('#image-text-key').element as HTMLInputElement).value).toBe('')
  await wrapper.get('#image-text-model').setValue('new-vision')
  api.saveImageModels.mockResolvedValue({...models,revision:8})
  await wrapper.get('#image-models-form').trigger('submit');await flushPromises()
  expect(api.saveImageModels).toHaveBeenCalledWith({expected_revision:7,expected_versions:models.versions,
    text_model:{base_url:'https://text.example/v1',model:'new-vision',protocol:'chat_completions'},
    image_model:{base_url:'https://image.example/v1',model:'image',protocol:'openai_images'}})
  wrapper.unmount()
})

it('requires new keys for provider origin/protocol changes and clears secrets on cancel',async()=>{
  const wrapper=mount(ImageAgentConfigs,{global});await flushPromises()
  await wrapper.get('[data-configure-image-models]').trigger('click');await flushPromises()
  expect(wrapper.get('#image-text-key').attributes('required')).toBeUndefined()
  await wrapper.get('#image-text-url').setValue('https://other.example/v1')
  expect(wrapper.get('#image-text-key').attributes('required')).toBeDefined()
  await wrapper.get('#image-text-key').setValue('private')
  await wrapper.get('[data-close]').trigger('click')
  await wrapper.get('[data-configure-image-models]').trigger('click');await flushPromises()
  expect((wrapper.get('#image-text-key').element as HTMLInputElement).value).toBe('')
  expect((wrapper.get('#image-text-url').element as HTMLInputElement).value).toBe(models.text_model.base_url)
  await wrapper.get('select[data-select-id="image-generation-protocol"]').setValue('openrouter_images')
  expect(wrapper.get('#image-generation-key').attributes('required')).toBeDefined()
  wrapper.unmount()
})

it('keeps both drafts after conflict and prevents resubmission until reopened',async()=>{
  const wrapper=mount(ImageAgentConfigs,{global});await flushPromises()
  await wrapper.get('[data-configure-image-models]').trigger('click');await flushPromises()
  await wrapper.get('#image-text-model').setValue('draft-vision')
  await wrapper.get('#image-generation-key').setValue('private')
  api.saveImageModels.mockRejectedValue(new ApiError('配置冲突',409))
  await wrapper.get('#image-models-form').trigger('submit');await flushPromises()
  expect((wrapper.get('#image-text-model').element as HTMLInputElement).value).toBe('draft-vision')
  expect((wrapper.get('#image-generation-key').element as HTMLInputElement).value).toBe('private')
  expect(wrapper.get('[data-save-image-models]').attributes('disabled')).toBeDefined()
  expect(wrapper.text()).toContain('关闭后重新打开')
  wrapper.unmount()
})

it('configures the imageAgent connection without any scheme or alias selections',async()=>{
  const wrapper=mount(ImageAgentConfigs,{global});await flushPromises()
  await wrapper.get('[data-configure-connection]').trigger('click');await flushPromises()
  expect(wrapper.findAll('select')).toHaveLength(0)
  api.saveMediaConnection.mockResolvedValue({...connection,revision:3})
  await wrapper.get('#image-connection-form').trigger('submit');await flushPromises()
  expect(api.saveMediaConnection).toHaveBeenCalledWith('image',{expected_revision:2,base_url:connection.base_url})
  wrapper.unmount()
})

it('blocks model editing until a service connection exists',async()=>{
  api.getMediaConnection.mockResolvedValue({...connection,has_service_key:false,base_url:null})
  const wrapper=mount(ImageAgentConfigs,{global});await flushPromises()
  expect(wrapper.get('[data-configure-image-models]').attributes('disabled')).toBeDefined()
  expect(api.getImageModels).not.toHaveBeenCalled()
  wrapper.unmount()
})
