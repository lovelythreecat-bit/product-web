import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'
import type { Schema } from '../../src/types/api'
const api = vi.hoisted(() => ({ history: vi.fn() }))
vi.mock('../../src/api/tasks', () => ({ getTaskHistory: api.history }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: ref(1) } }))
import TaskHistory from '../../src/features/workspace/TaskHistory.vue'
const detail = (id: string) => ({ agent_id: 'copy', task: { task_id: id } }) as Schema<'TaskDetail'>
const wrappers: VueWrapper[] = []
function render() {
 const wrapper = mount(TaskHistory, { props: { detail: detail('latest'), agents: [{ agent_id: 'copy', kind: 'copy' }] as Schema<'AgentVersion'>[] }, global: { stubs: {
  AppDrawer: { props: ['open', 'title'], template: '<section v-if="open" role="dialog" :aria-label="title"><slot/></section>' },
  TaskCard: { props: { detail: Object, readOnly: Boolean }, template: '<article :data-task-id="detail.task.task_id" :data-read-only="readOnly"/>' },
 } } })
 wrappers.push(wrapper); return wrapper
}
afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()); vi.resetAllMocks() })
it('loads the selected task history on demand with read-only cards', async () => {
 api.history.mockResolvedValue([detail('previous')])
 const wrapper = render()
 expect(api.history).not.toHaveBeenCalled()
 await wrapper.get('button').trigger('click'); await flushPromises()
 expect(api.history).toHaveBeenCalledWith('latest')
 expect(wrapper.get('[data-task-id="previous"]').attributes('data-read-only')).toBe('true')
 await wrapper.setProps({ detail: { ...detail('latest') } })
 expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
})
it('ignores a late history response after another task is selected', async () => {
 let resolve!: (value: Schema<'TaskDetail'>[]) => void
 api.history.mockReturnValue(new Promise(done => { resolve = done }))
 const wrapper = render(); await wrapper.get('button').trigger('click')
 await wrapper.setProps({ detail: detail('other') })
 resolve([detail('stale')]); await flushPromises()
 expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
 api.history.mockResolvedValue([])
 await wrapper.get('button').trigger('click'); await flushPromises()
 expect(wrapper.text()).toContain('暂无历史版本')
 expect(wrapper.find('[data-task-id]').exists()).toBe(false)
})
it('can retry a read failure without submitting any generation', async () => {
 api.history.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce([detail('recovered')])
 const wrapper = render(); await wrapper.get('button').trigger('click'); await flushPromises()
 expect(wrapper.get('[role="alert"]').text()).toContain('请重试')
 await wrapper.findAll('button').find(button => button.text() === '重新读取历史版本')!.trigger('click'); await flushPromises()
 expect(wrapper.find('[data-task-id="recovered"]').exists()).toBe(true)
 expect(api.history).toHaveBeenCalledTimes(2)
})
