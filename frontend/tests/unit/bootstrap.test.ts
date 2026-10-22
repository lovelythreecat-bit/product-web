import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import App from '../../src/App.vue'
import { router } from '../../src/router'
describe('development shell', () => {
 it('guards protected pages and keeps login accessible without product facts', async () => {
  vi.stubGlobal('fetch',async()=>new Response('{}',{status:401}))
  await router.push('/workspace'); await router.isReady()
  const wrapper=mount(App,{global:{plugins:[router]}})
  expect(wrapper.get('h1').text()).toBe('欢迎回来')
  expect(wrapper.find('input[type="password"]').exists()).toBe(true)
  expect(wrapper.find('[data-testid="available"]').exists()).toBe(false)
  wrapper.unmount()
  vi.unstubAllGlobals()
 })
})
