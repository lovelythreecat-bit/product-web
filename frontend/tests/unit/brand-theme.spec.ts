import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ApiError } from '../../src/api/client'
const api = vi.hoisted(() => ({ getSiteBrand:vi.fn(), updateSiteBrand:vi.fn() }))
vi.mock('../../src/api/site', () => api)
vi.mock('../../src/features/auth/session', () => ({ session:{epoch:{value:0}} }))
import BrandSettings from '../../src/features/admin/BrandSettings.vue'
import ThemeToggle from '../../src/components/ThemeToggle.vue'
import { applyBrand, brandName, refreshBrand } from '../../src/features/site/brand'
import { initializeTheme, setTheme, theme } from '../../src/styles/theme'

beforeEach(() => {
  vi.clearAllMocks()
  api.getSiteBrand.mockResolvedValue({name:'映作',version:2})
  setTheme('light')
})
it('cancel keeps the saved name; a confirmed save updates name, title and version', async () => {
  const wrapper = mount(BrandSettings); await flushPromises()
  await wrapper.findAll('button').find(b => b.text() === '编辑 Logo 名称')!.trigger('click'); await flushPromises()
  await wrapper.get('input').setValue('未保存')
  await wrapper.findAll('button').find(b => b.text() === '取消')!.trigger('click')
  expect(brandName.value).toBe('映作'); expect(api.updateSiteBrand).not.toHaveBeenCalled()
  await wrapper.findAll('button').find(b => b.text() === '编辑 Logo 名称')!.trigger('click'); await flushPromises()
  api.updateSiteBrand.mockResolvedValue({name:'星河创作',version:3})
  await wrapper.get('input').setValue(' 星河创作 ')
  await wrapper.get('form').trigger('submit'); await flushPromises()
  expect(api.updateSiteBrand).toHaveBeenCalledWith({name:'星河创作',expected_version:2})
  expect(brandName.value).toBe('星河创作'); expect(document.title).toBe('星河创作 · 电商 AI 创作平台')
  expect(wrapper.find('[role="dialog"]').exists()).toBe(false); wrapper.unmount()
})
it('validation and a version conflict preserve the editor without changing the brand', async () => {
  const wrapper = mount(BrandSettings); await flushPromises()
  await wrapper.findAll('button').find(b => b.text() === '编辑 Logo 名称')!.trigger('click'); await flushPromises()
  await wrapper.get('input').setValue('   '); await wrapper.get('form').trigger('submit')
  expect(api.updateSiteBrand).not.toHaveBeenCalled()
  api.updateSiteBrand.mockRejectedValue(new ApiError('conflict',409))
  await wrapper.get('input').setValue('保留草稿'); await wrapper.get('form').trigger('submit'); await flushPromises()
  expect(wrapper.get('input').element.value).toBe('保留草稿'); expect(brandName.value).toBe('映作')
  expect(wrapper.text()).toContain('草稿已保留'); wrapper.unmount()
})
it('toggles both ways, restores the saved theme and synchronizes other tabs', async () => {
  const wrapper = mount(ThemeToggle)
  await wrapper.get('button').trigger('click')
  expect(document.documentElement.dataset.theme).toBe('dark')
  expect(localStorage.getItem('yingzuo-theme')).toBe('dark')
  theme.value = 'light'; initializeTheme(); expect(theme.value).toBe('dark')
  window.dispatchEvent(new StorageEvent('storage',{key:'yingzuo-theme',newValue:'light'}))
  expect(theme.value).toBe('light')
  await wrapper.get('button').trigger('click'); await wrapper.get('button').trigger('click')
  expect(wrapper.get('button').attributes('aria-label')).toBe('切换深色主题'); wrapper.unmount()
})
it('can switch when local storage is unavailable', () => {
  const spy = vi.spyOn(Storage.prototype,'setItem').mockImplementation(() => { throw new Error('disabled') })
  expect(() => setTheme('dark')).not.toThrow(); expect(theme.value).toBe('dark'); spy.mockRestore()
})
it('an older background read cannot overwrite a just-saved brand', async () => {
  let resolve!: (value: {name:string;version:number}) => void
  api.getSiteBrand.mockReturnValue(new Promise(done => { resolve = done }))
  const pending = refreshBrand()
  applyBrand({name:'最新名称',version:4})
  resolve({name:'旧名称',version:3}); await pending
  expect(brandName.value).toBe('最新名称')
})
