import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import AgentSelector from '../../src/components/AgentSelector.vue'
import AppShell from '../../src/components/AppShell.vue'
import type { Schema } from '../../src/types/api'

vi.mock('../../src/features/auth/session', () => ({ session: { profile: ref({ role: 'admin' }), epoch: ref(1), account: ref(null), refreshAccount: vi.fn().mockResolvedValue(undefined) } }))
const wrappers: VueWrapper[] = []
afterEach(() => wrappers.splice(0).forEach(wrapper => wrapper.unmount()))
it('selects the single agent for the chosen creation type without an agent dropdown', async () => {
  const agents = [{ agent_id: 'copy', kind: 'copy', enabled: true }, { agent_id: 'image', kind: 'image', enabled: true }] as Schema<'AgentVersion'>[]
  const wrapper = mount(AgentSelector, { props: { agents, modelValue: '' } }); wrappers.push(wrapper)
  expect(wrapper.find('select').exists()).toBe(false)
  await wrapper.findAll('button')[1].trigger('click')
  expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['image'])
  await wrapper.setProps({ modelValue: 'image' })
  expect(wrapper.findAll('button')[1].attributes('aria-pressed')).toBe('true')
  await wrapper.findAll('button')[2].trigger('click')
  expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([''])
  expect(wrapper.text()).toContain('暂无可用')
})
it('marks redirected admin routes active and exposes only the brand as a new-tab homepage link', async () => {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/admin', redirect: '/admin/tasks' }, { path: '/:pathMatch(.*)*', component: { template: '<div />' } }] })
  await router.push('/admin'); await router.isReady()
  const wrapper = mount(AppShell, { global: { plugins: [router], stubs: { UserMenu: true, ConversationList: true } } }); wrappers.push(wrapper)
  await flushPromises()
  const admin = wrapper.get('.app-header nav a[href="/admin"]')
  expect(admin.classes()).toContain('router-link-active')
  expect(admin.attributes('aria-current')).toBe('page')
  expect(wrapper.get('a.brand').attributes('target')).toBe('_blank')
  expect(wrapper.get('a.brand').attributes('rel')).toContain('noopener')
  expect(wrapper.find('.app-header nav a[href="/"]').exists()).toBe(false)
})

it('keeps the workspace navigation active when a conversation is opened and clears it on other pages', async () => {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/workspace/:conversationId?', component: { template: '<div />' } },
    { path: '/works', component: { template: '<div />' } },
    { path: '/:pathMatch(.*)*', component: { template: '<div />' } },
  ] })
  await router.push('/workspace'); await router.isReady()
  const wrapper = mount(AppShell, { global: { plugins: [router], stubs: { UserMenu: true, ConversationList: true } } }); wrappers.push(wrapper)
  const workspace = () => wrapper.get('.app-header nav a[href="/workspace"]')
  expect(workspace().classes()).toContain('router-link-active')
  await router.push('/workspace/conversation-1'); await flushPromises()
  expect(workspace().classes()).toContain('router-link-active')
  expect(workspace().attributes('aria-current')).toBe('page')
  await router.push('/workspace/conversation-2'); await flushPromises()
  expect(workspace().classes()).toContain('router-link-active')
  await router.push('/works'); await flushPromises()
  expect(workspace().classes()).not.toContain('router-link-active')
  expect(workspace().attributes('aria-current')).toBeUndefined()
})

it('keeps the recharge shortcut out of the page header while retaining the workspace balance entry', async () => {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }] })
  await router.push('/account'); await router.isReady()
  const wrapper = mount(AppShell, { global: { plugins: [router], stubs: { UserMenu: true, ConversationList: true } } }); wrappers.push(wrapper)
  expect(wrapper.find('.app-header a[href="/recharge"]').exists()).toBe(false)
  await router.push('/workspace'); await flushPromises()
  expect(wrapper.find('.app-header a[href="/recharge"]').exists()).toBe(false)
  expect(wrapper.find('.sidebar-bottom a[href="/recharge"]').exists()).toBe(true)
})
