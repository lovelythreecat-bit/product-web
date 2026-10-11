import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import App from '../../src/App.vue'
import { router } from '../../src/router'
describe('development shell', () => {
 it('marks placeholders and keeps product facts unavailable', async () => {
  await router.push('/workspace'); await router.isReady()
  const wrapper=mount(App,{global:{plugins:[router]}})
  expect(wrapper.get('h1').text()).toBe('创作工作台')
  expect(wrapper.text()).toContain('TEST_ONLY')
  expect(wrapper.text()).toContain('业务页面正在开发')
  expect(wrapper.text()).toContain('积分信息待接入')
  wrapper.unmount()
 })
})
