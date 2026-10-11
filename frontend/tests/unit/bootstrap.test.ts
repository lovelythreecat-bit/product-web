import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import App from '../../src/App.vue'

describe('bootstrap screen', () => {
  it('clearly identifies the development shell as TEST_ONLY', () => {
    const wrapper = mount(App)
    expect(wrapper.get('h1').text()).toBe('电商 AI 创作平台')
    expect(wrapper.text()).toContain('TEST_ONLY')
  })
})
