import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { Schema } from '../../src/types/api'
const api = vi.hoisted(() => ({ getWork: vi.fn() }))
const identity = vi.hoisted(() => ({ epoch: { value: 0 } }))
vi.mock('../../src/api/works', () => api)
vi.mock('../../src/features/auth/session', () => ({ session: identity }))
import TaskCard from '../../src/components/TaskCard.vue'
const detail = { task: { task_id: 'original-task', work_ids: ['original-work'], state: 'SUCCEEDED', settlement_state: 'CONSUMED', quote: { credits: 20 } }, input: { instruction: 'original input' }, policy_versions: {} } as Schema<'TaskDetail'>
const work = { work_id: 'original-work', task_id: 'original-task', kind: 'copy', items: [] }
const global = { stubs: { AppDrawer: true, ResultViewer: { props: ['work'], template: '<p>{{ work.work_id }}</p>' } } }
beforeEach(() => { vi.resetAllMocks(); identity.epoch.value = 0 })
it('explicitly retries the original work after same-ID task refresh and clears the read error', async () => {
  api.getWork.mockRejectedValueOnce(new Error('temporary read failure')).mockResolvedValueOnce(work)
  const wrapper = mount(TaskCard, { props: { detail }, global }); await flushPromises()
  await wrapper.setProps({ detail: { ...detail, task: { ...detail.task } } })
  expect(api.getWork).toHaveBeenCalledTimes(1)
  await wrapper.get('button[data-work-retry]').trigger('click'); await flushPromises()
  expect(api.getWork.mock.calls).toEqual([['original-work'], ['original-work']])
  expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  expect(wrapper.text()).toContain('original-work')
  expect(wrapper.attributes('data-task-id')).toBe('original-task')
  expect(wrapper.text()).toContain('生成成功'); expect(wrapper.text()).toContain('已消费')
  expect(wrapper.emitted('regenerate')).toBeUndefined(); wrapper.unmount()
})
it.each(['resolve', 'reject'])('ignores a late retry %s across an identity epoch', async outcome => {
  api.getWork.mockRejectedValueOnce(new Error('temporary read failure'))
  let resolve!: (value: typeof work) => void, reject!: (reason: Error) => void
  api.getWork.mockImplementationOnce(() => new Promise((ok, fail) => { resolve = ok; reject = fail }))
  const wrapper = mount(TaskCard, { props: { detail }, global }); await flushPromises()
  await wrapper.get('button[data-work-retry]').trigger('click')
  identity.epoch.value++
  if (outcome === 'resolve') resolve(work); else reject(new Error('late failure'))
  await flushPromises()
  expect(wrapper.text()).not.toContain('original-work')
  expect(wrapper.find('[role="alert"]').exists()).toBe(false); wrapper.unmount()
})
