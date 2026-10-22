import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import ParametersView from '../../src/features/admin/ParametersView.vue'
import { ApiError } from '../../src/api/client'
const api = vi.hoisted(() => ({ getParameterConfig: vi.fn(), saveParameterConfig: vi.fn() }))
vi.mock('../../src/api/admin', () => api)
const overlay = { props: ['open'], emits: ['update:open'], template: '<div v-if="open"><slot/><button @click="$emit(\'update:open\', false)">取消</button><slot name="actions"/></div>' }
let wrapper: VueWrapper
beforeEach(() => { vi.resetAllMocks(); api.getParameterConfig.mockResolvedValue({ version: null, text_price: null, image_price: null, video_price: null }); api.saveParameterConfig.mockResolvedValue({ version:'v1', text_price:0, image_price:8, video_price:null }) })
afterEach(() => wrapper?.unmount())
it('edits prices, preserves zero and nullable prices, cancel never saves', async () => {
 wrapper=mount(ParametersView,{global:{stubs:{AppDrawer:overlay}}});await flushPromises()
 const edit=()=>wrapper.findAll('button').find(x=>x.text()==='编辑参数')!
 await edit().trigger('click');await flushPromises();expect(wrapper.findAll('input[type="number"]')).toHaveLength(3)
 await wrapper.findAll('button').find(x=>x.text()==='取消')!.trigger('click');expect(api.saveParameterConfig).not.toHaveBeenCalled()
 await edit().trigger('click');await flushPromises();await wrapper.get('#text-price').setValue('0');await wrapper.get('#image-price').setValue('8');await wrapper.get('form').trigger('submit');await flushPromises()
 expect(api.saveParameterConfig).toHaveBeenCalledWith(expect.objectContaining({expected_version:null,text_price:0,image_price:8,video_price:null}))
 expect(wrapper.text()).toContain('0 积分 / 次');expect(wrapper.text()).toContain('未配置')
})
it('hides assist configuration and omits its fields when saving prices', async () => {
 api.getParameterConfig.mockResolvedValue({version:'v1',text_price:0,image_price:8,video_price:null,assist_base_url:'https://models.example/v1',assist_model:'existing-model',has_assist_api_key:true})
 wrapper=mount(ParametersView,{global:{stubs:{AppDrawer:overlay}}});await flushPromises()
 expect(wrapper.text()).not.toContain('AI 帮我完善')
 expect(wrapper.text()).not.toContain('https://models.example/v1')
 await wrapper.findAll('button').find(x=>x.text()==='编辑参数')!.trigger('click');await flushPromises()
 expect(wrapper.text()).not.toContain('AI 帮我完善')
 expect(wrapper.find('#assist-base-url').exists()).toBe(false)
 expect(wrapper.find('#assist-model').exists()).toBe(false)
 expect(wrapper.find('#assist-api-key').exists()).toBe(false)
 await wrapper.get('#image-price').setValue('9')
 await wrapper.get('form').trigger('submit');await flushPromises()
 expect(api.saveParameterConfig).toHaveBeenLastCalledWith({expected_version:'v1',text_price:0,image_price:9,video_price:null})
 expect(wrapper.text()).not.toContain('AI 完善')
})
it('rejects fractions before saving and retains editable draft on conflict',async()=>{
 wrapper=mount(ParametersView,{global:{stubs:{AppDrawer:overlay}}});await flushPromises();await wrapper.findAll('button').find(x=>x.text()==='编辑参数')!.trigger('click');await flushPromises()
 await wrapper.get('#text-price').setValue('1.5');await wrapper.get('form').trigger('submit');expect(api.saveParameterConfig).not.toHaveBeenCalled()
 await wrapper.get('#text-price').setValue('5');api.saveParameterConfig.mockRejectedValueOnce(Error('配置已更新'));await wrapper.get('form').trigger('submit');await flushPromises()
 expect(wrapper.get('#text-price').element).toHaveProperty('value','5');expect(wrapper.text()).toContain('配置已更新')
})
it('loads current prices on reopen after a conflict without manual version adoption',async()=>{
 api.getParameterConfig.mockResolvedValue({version:'v1',text_price:12,image_price:8,video_price:null})
 wrapper=mount(ParametersView,{global:{stubs:{AppDrawer:overlay}}});await flushPromises()
 const button=(text:string)=>wrapper.findAll('button').find(button=>button.text()===text)!
 await button('编辑参数').trigger('click');await flushPromises()
 expect(wrapper.findAll('button').some(button=>/核对|采用.*版本/.test(button.text()))).toBe(false)
 await wrapper.get('#text-price').setValue('5')
 api.saveParameterConfig.mockRejectedValueOnce(new ApiError('conflict',409))
 await wrapper.get('form').trigger('submit');await flushPromises()
 expect(wrapper.get('#text-price').element).toHaveProperty('value','5')
 expect(api.saveParameterConfig).toHaveBeenLastCalledWith(expect.objectContaining({expected_version:'v1'}))
 await button('取消').trigger('click')
 api.getParameterConfig.mockResolvedValue({version:'v2',text_price:13,image_price:8,video_price:null})
 await button('编辑参数').trigger('click');await flushPromises()
 expect(wrapper.get('#text-price').element).toHaveProperty('value','13')
 await wrapper.get('#text-price').setValue('7');await wrapper.get('form').trigger('submit');await flushPromises()
 expect(api.saveParameterConfig).toHaveBeenLastCalledWith(expect.objectContaining({expected_version:'v2',text_price:7}))
})
