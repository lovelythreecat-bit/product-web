import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { defineComponent, effectScope, ref, reactive } from 'vue'
import { useTaskStream } from '../../src/features/workspace/useTaskStream'
import { draftFor, setSourceDraft } from '../../src/features/workspace/drafts'
import type { Schema } from '../../src/types/api'
import MediaChoices from '../../src/features/workspace/MediaChoices.vue'
import VideoTaskPanel from '../../src/features/workspace/VideoTaskPanel.vue'

vi.mock('../../src/features/auth/session', async () => {
  const { ref } = await import('vue')
  return { session: { profile: ref({ user_id: 'user-media' }), epoch: ref(1), refreshAccount: vi.fn() },
    onIdentityChange: () => () => {} }
})

afterEach(() => { sessionStorage.clear(); vi.unstubAllGlobals(); vi.useRealTimers() })
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function () { this.open = true }
  HTMLDialogElement.prototype.close = function () { this.open = false }
})

it('requires explicit choices, allows white backgrounds on every platform and enables long images', async () => {
  const Harness = defineComponent({ components: { MediaChoices }, setup() {
    return { value: ref({}) }
  }, template: '<MediaChoices protocol="image-agent-v1" v-model="value" :materials="[]" />' })
  const wrapper = mount(Harness)
  const platform = wrapper.get('select[data-select-id$="-platform"]')
  const output = wrapper.get('select[data-select-id$="-output"]')
  expect((platform.element as HTMLSelectElement).value).toBe('')
  expect((output.element as HTMLSelectElement).value).toBe('')
  expect(wrapper.get('option[value="long_image"]').attributes('disabled')).toBeUndefined()
  expect(wrapper.get('option[value="pdd_white_background"]').text()).toBe('白底图')
  await platform.setValue('pinduoduo')
  await output.setValue('pdd_white_background')
  await platform.setValue('taobao')
  expect((output.element as HTMLSelectElement).value).toBe('pdd_white_background')
  expect(wrapper.get('option[value="pdd_white_background"]').attributes('disabled')).toBeUndefined()
  await output.setValue('long_image')
  expect((output.element as HTMLSelectElement).value).toBe('long_image')
  wrapper.unmount()
})

it('does not automatically select a first frame and clears a removed image', async () => {
  const wrapper = mount(MediaChoices, { props: { protocol: 'video-agent-v1', modelValue: {},
    materials: [{ file_id: 'image-1' }, { file_id: 'image-2' }] } })
  expect(wrapper.findAll('input:checked')).toHaveLength(0)
  await wrapper.get('input[value="image-2"]').setValue(true)
  expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([{ first_frame_file_id: 'image-2' }])
  await wrapper.setProps({ modelValue: { first_frame_file_id: 'image-2' },
    materials: [{ file_id: 'image-1' }] })
  expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([{}])
  wrapper.unmount()
})

it('prefills actual video defaults and preserves chosen seconds and ratio when changing or losing the first frame', async () => {
  const Harness = defineComponent({ components: { MediaChoices }, setup() {
    return { value: ref<Record<string, string | number | boolean>>({}), materials: ref([{ file_id: 'frame' }]) }
  }, template: '<MediaChoices protocol="video-agent-v1" v-model="value" :materials="materials" :video-options="{ duration_tiers: [6, 12], default_duration: 12, aspect_ratios: [\'9:16\', \'16:9\'] }" />' })
  const wrapper = mount(Harness)
  await flushPromises()
  const duration = wrapper.get('select[data-select-id$="-duration"]')
  const ratio = wrapper.get('select[data-select-id$="-ratio"]')
  expect((duration.element as HTMLSelectElement).value).toBe('12')
  expect((ratio.element as HTMLSelectElement).value).toBe('9:16')
  expect(duration.findAll('option').map(option => option.attributes('value'))).toEqual(['6', '12'])
  await duration.setValue('6')
  await ratio.setValue('16:9')
  await wrapper.get('input[value="frame"]').setValue(true)
  expect(wrapper.vm.value).toEqual({ duration_seconds: 6, aspect_ratio: '16:9', first_frame_file_id: 'frame' })
  wrapper.vm.materials = []
  await flushPromises()
  expect(wrapper.vm.value).toEqual({ duration_seconds: 6, aspect_ratio: '16:9' })
  wrapper.unmount()
})

it('keeps restored video parameters while source work data stays immutable', () => {
  const product = { product_id: 'p', version: 'pv', created_at: '', product: { name: '商品' } } as Schema<'ProductVersionView'>
  const work = { work_id: 'w', source: { agent_id: 'video-agent', input: { instruction: '', parameters: { duration_seconds: 12, aspect_ratio: '16:9', retired: 1 } }, materials: [] } } as unknown as Schema<'WorkDetail'>
  setSourceDraft('video-parameter-source', work, product)
  const parameters = draftFor('video-parameter-source').agents['video-agent'].parameters
  expect(parameters).toEqual({ duration_seconds: 12, aspect_ratio: '16:9' })
  parameters.duration_seconds = 6
  expect(work.source.input.parameters.duration_seconds).toBe(12)
})

it('does not replace saved video choices when capabilities or disabled state changes', async () => {
  const wrapper = mount(MediaChoices, { props: { protocol: 'video-agent-v1', modelValue: { duration_seconds: 12, aspect_ratio: '16:9' }, materials: [],
    videoOptions: { duration_tiers: [6, 12], default_duration: 6, aspect_ratios: ['9:16', '16:9'] } } })
  expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  await wrapper.setProps({ videoOptions: { duration_tiers: [5, 10], default_duration: 10, aspect_ratios: ['9:16'] }, disabled: true })
  expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  expect(wrapper.get('select[data-select-id$="-duration"]').element).toHaveProperty('value', '12')
  expect(wrapper.get('select[data-select-id$="-ratio"]').element).toHaveProperty('value', '16:9')
  wrapper.unmount()
})

it('awaiting confirmation only reads; explicit confirmation keeps the viewed plan version', async () => {
  const requests: { url: string; options: RequestInit }[] = []
  vi.stubGlobal('fetch', async (url: string, options: RequestInit) => {
    requests.push({ url, options }); return new Response(JSON.stringify({ kind: 'video', status: 'generating' }))
  })
  const wrapper = mount(VideoTaskPanel, { props: { taskId: 'task-video', media: {
    kind: 'video', status: 'awaiting_confirmation', head_plan_version: 3,
    plan: { plan_version: 3, document: { creative: '保持商品原色', audience: '用户',
      selling_points: ['用户提供卖点'], duration_seconds: 10, aspect_ratio: '9:16',
      subtitles: true, voiceover: false, music: false,
      shared_visual: { scene: '桌面' }, shots: [{ shot_id: 'shot-1', content: '商品近景',
        start_frame: 0, end_frame: 48 }] } } } } })
  expect(requests).toHaveLength(0)
  await wrapper.get('[data-view-plan]').trigger('click')
  expect(wrapper.text()).toContain('商品近景')
  expect(wrapper.text()).toContain('起始帧')
  await wrapper.get('[data-confirm-plan]').trigger('click')
  await wrapper.setProps({ media: { kind: 'video', status: 'awaiting_confirmation', head_plan_version: 4 } })
  await wrapper.get('[data-send-confirmation]').trigger('click')
  await flushPromises()
  expect(requests).toHaveLength(1)
  expect(JSON.parse(String(requests[0].options.body))).toEqual({ plan_version: 3 })
  expect(wrapper.emitted('changed')).toHaveLength(1)
  wrapper.unmount()
})

it('restores only media choices and requires a new first frame when the original is unavailable', () => {
  const product = { product_id: 'p', version: 'pv', created_at: '', product: { name: '商品' } } as Schema<'ProductVersionView'>
  setSourceDraft('media-source', { work_id: 'w', source: { agent_id: 'video-agent',
    input: { instruction: '原指令', parameters: { first_frame_file_id: 'lost', platform: 'taobao', output_type: 'main_image', retired: 1 } },
    materials: [{ available: false, file: { file_id: 'lost', version: 'v' } }] } } as unknown as Schema<'WorkDetail'>, product)
  expect(draftFor('media-source').agents['video-agent'].parameters).toEqual({ platform: 'taobao', output_type: 'main_image' })
})

it('SSE updates media phases without task version changes and never polls while idle', async () => {
  vi.useFakeTimers()
  let source!: Events
  class Events {
    listeners = new Map<string, (event: MessageEvent) => void>()
    constructor() { source = this }
    close() {}
    addEventListener(name: string, listener: (event: MessageEvent) => void) { this.listeners.set(name, listener) }
    update(revision: number) { this.listeners.get('task.updated')?.(new MessageEvent('task.updated', { data: JSON.stringify({ payload: { task_id: 'media-poll', state_version: 1, media_revision: revision } }) })) }
  }
  vi.stubGlobal('EventSource', Events)
  let phase = 'awaiting_input', state = 'RUNNING'
  const requests: { url: string; method: string }[] = []
  const task = () => ({ task_id: 'media-poll', state, state_version: 1, work_ids: [] })
  vi.stubGlobal('fetch', async (url: string, options: RequestInit) => {
    requests.push({ url, method: options.method || 'GET' })
    const value = url.startsWith('/api/v1/tasks/media-poll') ? { task: task(), conversation_id: 'c',
      media: { kind: 'video', status: phase, revision: phase === 'awaiting_input' ? 1 : 2 } } : url.startsWith('/api/v1/tasks?') ? { items: [task()], next_cursor: null }
      : { items: [], next_cursor: null }
    return new Response(JSON.stringify(value))
  })
  const scope = effectScope(), conversation = ref('c')
  const stream = scope.run(() => useTaskStream(conversation))!
  await flushPromises()
  const initialCount = requests.length
  await vi.advanceTimersByTimeAsync(15000)
  expect(requests).toHaveLength(initialCount)
  phase = 'awaiting_confirmation'
  source.update(2)
  await flushPromises()
  expect((stream.details.value['media-poll'] as unknown as { media: { status: string } }).media.status).toBe('awaiting_confirmation')
  expect(requests.every(r => r.method === 'GET')).toBe(true)
  state = 'SUCCEEDED'
  await stream.refreshTask('media-poll')
  const count = requests.length
  await vi.advanceTimersByTimeAsync(10000)
  expect(requests).toHaveLength(count)
  conversation.value = ''
  await flushPromises()
  expect(stream.tasks.value).toEqual([])
  scope.stop()
})

it('restores an uncertain command with its exact key/body after remount and never auto sends', async () => {
  const requests: RequestInit[] = []
  vi.stubGlobal('fetch', async (_: string, options: RequestInit) => {
    requests.push(options); throw new Error('response lost')
  })
  const props = { taskId: 'task-video', media: { kind: 'video' as const,
    status: 'awaiting_input', questions: ['请说明商品材质'] } }
  let wrapper = mount(VideoTaskPanel, { props })
  await wrapper.get('[data-open-inputs]').trigger('click')
  await wrapper.get('textarea').setValue('用户补充：陶瓷')
  await wrapper.get('[data-send-inputs]').trigger('click')
  await flushPromises()
  expect(requests).toHaveLength(1)
  wrapper.unmount()
  wrapper = mount(VideoTaskPanel, { props })
  await flushPromises()
  expect(requests).toHaveLength(1)
  await wrapper.get('[data-retry-command]').trigger('click')
  await flushPromises()
  expect(requests).toHaveLength(2)
  expect(requests[1].body).toEqual(requests[0].body)
  expect(new Headers(requests[1].headers).get('Idempotency-Key'))
    .toEqual(new Headers(requests[0].headers).get('Idempotency-Key'))
  wrapper.unmount()
})

it('does not create a fresh command when its saved original intent is unreadable', async () => {
  sessionStorage.setItem('video-command-v1:user-media:damaged-task', '{broken')
  const requests: unknown[] = []
  vi.stubGlobal('fetch', async (...args: unknown[]) => { requests.push(args); return new Response('{}') })
  const wrapper = mount(VideoTaskPanel, { props: { taskId: 'damaged-task',
    media: { kind: 'video', status: 'awaiting_input' } } })
  await wrapper.get('[data-open-inputs]').trigger('click')
  await wrapper.get('textarea').setValue('陶瓷')
  await wrapper.get('[data-send-inputs]').trigger('click')
  await flushPromises()
  expect(requests).toHaveLength(0)
  expect(wrapper.text()).toContain('原操作记录无法读取')
  wrapper.unmount()
})

it('a structured command rejection preserves editable text and allows a new corrected intent', async () => {
  const requests: RequestInit[] = []
  vi.stubGlobal('fetch', async (_: string, options: RequestInit) => {
    requests.push(options)
    return requests.length === 1
      ? new Response(JSON.stringify({ error: { code: 'COMMAND_REJECTED', message: '请补充商品材质。' } }), { status: 422 })
      : new Response(JSON.stringify({ kind: 'video', status: 'planning' }))
  })
  const wrapper = mount(VideoTaskPanel, { props: { taskId: 'rejected-task',
    media: { kind: 'video', status: 'awaiting_input' } } })
  await wrapper.get('[data-open-inputs]').trigger('click')
  await wrapper.get('textarea').setValue('原补充内容')
  await wrapper.get('[data-send-inputs]').trigger('click')
  await flushPromises()
  expect(wrapper.get('textarea').attributes('disabled')).toBeUndefined()
  expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('原补充内容')
  expect(wrapper.emitted('changed')).toHaveLength(1)
  await wrapper.get('textarea').setValue('修正：商品材质为陶瓷')
  await wrapper.get('[data-send-inputs]').trigger('click')
  await flushPromises()
  expect(requests).toHaveLength(2)
  expect(JSON.parse(String(requests[1].body))).toEqual({ text: '修正：商品材质为陶瓷' })
  expect(new Headers(requests[1].headers).get('Idempotency-Key'))
    .not.toEqual(new Headers(requests[0].headers).get('Idempotency-Key'))
  wrapper.unmount()
})

it('rejects oversized video supplements before persisting or sending an intent', async () => {
  const fetcher = vi.fn()
  vi.stubGlobal('fetch',fetcher)
  const wrapper = mount(VideoTaskPanel,{props:{taskId:'too-long',media:{kind:'video',status:'awaiting_input'}}})
  await wrapper.get('[data-open-inputs]').trigger('click')
  await wrapper.get('textarea').setValue('字'.repeat(10001))
  await wrapper.get('[data-send-inputs]').trigger('click')
  await flushPromises()
  expect(fetcher).not.toHaveBeenCalled()
  expect(sessionStorage.getItem('video-command-v1:user-media:too-long')).toBeNull()
  expect(wrapper.get('textarea').attributes('maxlength')).toBe('10000')
  expect(wrapper.text()).toContain('10000')
  wrapper.unmount()
})

it('makes an old oversized intent editable because that payload cannot pass the API schema', async () => {
  const text = '字'.repeat(10001)
  const key = 'video-command-v1:user-media:old-too-long'
  sessionStorage.setItem(key,JSON.stringify({kind:'inputs',intent:{key:'original',body:JSON.stringify({text})}}))
  const wrapper = mount(VideoTaskPanel,{props:{taskId:'old-too-long',media:{kind:'video',status:'awaiting_input'}}})
  await wrapper.get('[data-open-inputs]').trigger('click')
  expect(wrapper.get('textarea').attributes('disabled')).toBeUndefined()
  expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe(text)
  expect(sessionStorage.getItem(key)).toBeNull()
  wrapper.unmount()
})

it('edits the viewed video shot and submits a version-bound revision without confirming generation', async () => {
  const requests: { url: string; options: RequestInit }[] = []
  vi.stubGlobal('fetch', async (url: string, options: RequestInit) => {
    requests.push({ url, options }); return new Response(JSON.stringify({ kind: 'video', status: 'awaiting_confirmation', head_plan_version: 4 }))
  })
  const wrapper = mount(VideoTaskPanel, { props: { taskId: 'edit-video', allowPlanRevision: true, media: {
    kind: 'video', status: 'awaiting_confirmation', head_plan_version: 3,
    plan: { plan_version: 3, document: { music_direction: '轻快', shots: [{ shot_id: 'shot-1', content: '原画面', action: '慢转', subtitle_text: '原字幕' }] } },
  } } })
  await wrapper.get('[data-edit-plan]').trigger('click')
  await wrapper.get('[data-shot-content="0"]').setValue('修改后的商品近景')
  await wrapper.get('[data-save-plan]').trigger('click')
  await flushPromises()
  expect(requests).toHaveLength(2)
  expect(requests[1].url).toBe('/api/v1/tasks/edit-video')
  expect(requests[0].url).toContain('/video/plan-revisions')
  expect(JSON.parse(String(requests[0].options.body))).toMatchObject({ plan_version: 3, patch: { shot_texts: [{ shot_id: 'shot-1', content: '修改后的商品近景' }] } })
  expect(wrapper.emitted('changed')).toHaveLength(1)
  wrapper.unmount()
})

it('persists an uncertain replan request and restores the original key after remount', async () => {
  const requests: RequestInit[] = []
  vi.stubGlobal('fetch', async (_: string, options: RequestInit) => { requests.push(options); throw new Error('lost receipt') })
  const props = { taskId: 'replan-video', allowPlanRevision: true, media: { kind: 'video' as const, status: 'awaiting_confirmation', head_plan_version: 2, plan: { plan_version: 2, document: {} } } }
  let wrapper = mount(VideoTaskPanel, { props })
  await wrapper.get('[data-replan]').trigger('click')
  await wrapper.get('[data-send-replan]').trigger('click')
  await flushPromises()
  expect(requests).toHaveLength(1)
  expect(JSON.parse(String(requests[0].body))).toMatchObject({ plan_version: 2, instruction: expect.any(String) })
  wrapper.unmount(); wrapper = mount(VideoTaskPanel, { props }); await flushPromises()
  expect(requests).toHaveLength(1)
  await wrapper.get('[data-retry-command]').trigger('click'); await flushPromises()
  expect(requests[1].body).toEqual(requests[0].body)
  expect(new Headers(requests[1].headers).get('Idempotency-Key')).toEqual(new Headers(requests[0].headers).get('Idempotency-Key'))
  wrapper.unmount()
})

it('keeps plan revision actions scoped to the explicitly enabled quick workflow', () => {
  const wrapper = mount(VideoTaskPanel, { props: { taskId: 'ordinary-video', media: {
    kind: 'video', status: 'awaiting_confirmation', head_plan_version: 1,
    plan: { plan_version: 1, document: {} },
  } } })
  expect(wrapper.find('[data-view-plan]').exists()).toBe(true)
  expect(wrapper.find('[data-edit-plan]').exists()).toBe(false)
  expect(wrapper.find('[data-replan]').exists()).toBe(false)
  wrapper.unmount()
})

it('saves edited quick plans before opening confirmation and confirms only the newly read version', async () => {
  const requests: { url: string; options: RequestInit }[] = []
  const updated = { kind: 'video', status: 'awaiting_confirmation', head_plan_version: 4, plan: { plan_version: 4, document: { shots: [{ shot_id: 'shot-1', content: '新画面' }] } } }
  vi.stubGlobal('fetch', async (url: string, options: RequestInit) => {
    requests.push({ url, options })
    return new Response(JSON.stringify(url.endsWith('/video/plan-revisions') ? updated : url.endsWith('/video/confirm') ? { kind: 'video', status: 'generating' } : { media: updated }))
  })
  const wrapper = mount(VideoTaskPanel, { props: { taskId: 'quick-edit-confirm', allowPlanRevision: true, media: {
    kind: 'video', status: 'awaiting_confirmation', head_plan_version: 3,
    plan: { plan_version: 3, document: { shots: [{ shot_id: 'shot-1', content: '原画面' }] } },
  } } })
  await wrapper.get('[data-view-plan]').trigger('click')
  await wrapper.get('[data-drawer-edit-plan]').trigger('click')
  await wrapper.get('[data-shot-content="0"]').setValue('新画面')
  await wrapper.get('[data-edit-confirm-plan]').trigger('click')
  await flushPromises()
  expect(requests.map(r => r.url)).toEqual(['/api/v1/tasks/quick-edit-confirm/video/plan-revisions', '/api/v1/tasks/quick-edit-confirm'])
  expect(wrapper.text()).toContain('将按方案版本 4')
  await wrapper.get('[aria-label="确认视频方案"] > button').trigger('click'); await flushPromises()
  expect((wrapper.get('[data-shot-content="0"]').element as HTMLTextAreaElement).value).toBe('新画面')
  await wrapper.get('[data-edit-confirm-plan]').trigger('click'); await flushPromises()
  expect(requests).toHaveLength(2)
  await wrapper.get('[data-send-confirmation]').trigger('click'); await flushPromises()
  expect(JSON.parse(String(requests.at(-1)!.options.body))).toEqual({ plan_version: 4 })
  expect(requests.filter(r => r.url.endsWith('/video/confirm'))).toHaveLength(1)
  wrapper.unmount()
})

it('keeps uncertain quick revisions on one request key and never confirms after a failed new-plan read', async () => {
  const requests: { url: string; options: RequestInit }[] = []
  let saveSucceeded = false
  vi.stubGlobal('fetch', async (url: string, options: RequestInit) => {
    requests.push({ url, options })
    if (url.endsWith('/video/plan-revisions') && saveSucceeded) return new Response(JSON.stringify({ kind: 'video', status: 'planning' }))
    throw new Error('lost response')
  })
  const wrapper = mount(VideoTaskPanel, { props: { taskId: 'quick-save-error', allowPlanRevision: true, media: { kind: 'video', status: 'awaiting_confirmation', head_plan_version: 1, plan: { plan_version: 1, document: { shots: [{ shot_id: 'one', content: '原画面' }] } } } } })
  await wrapper.get('[data-edit-plan]').trigger('click')
  await wrapper.get('[data-shot-content="0"]').setValue('修改')
  await wrapper.get('[data-edit-confirm-plan]').trigger('click'); await flushPromises()
  await wrapper.get('[data-edit-confirm-plan]').trigger('click'); await flushPromises()
  expect(requests).toHaveLength(1)
  saveSucceeded = true
  await wrapper.get('[data-retry-command]').trigger('click'); await flushPromises()
  expect(requests).toHaveLength(3)
  expect(new Headers(requests[0].options.headers).get('Idempotency-Key')).toBe(new Headers(requests[1].options.headers).get('Idempotency-Key'))
  expect(wrapper.text()).toContain('新方案暂时无法读取')
  expect(wrapper.find('[data-send-confirmation]').exists()).toBe(false)
  expect(requests.some(request => request.url.endsWith('/video/confirm'))).toBe(false)
  await wrapper.get('[aria-label="编辑视频方案"] > button').trigger('click')
  vi.stubGlobal('fetch', async () => new Response(JSON.stringify({ media: { kind: 'video', status: 'awaiting_confirmation', head_plan_version: 2, plan: { plan_version: 2, document: { shots: [{ shot_id: 'one', content: '修改' }] } } } })))
  await wrapper.get('[data-read-saved-plan]').trigger('click'); await flushPromises()
  await wrapper.get('[data-view-plan]').trigger('click')
  expect(wrapper.text()).toContain('方案版本 2')
  expect(wrapper.find('[data-send-confirmation]').exists()).toBe(false)
  wrapper.unmount()
})

it('does not reopen the old parent plan after a saved version has been read', async () => {
  const requests: { url: string; options: RequestInit }[] = []
  const updated = { kind: 'video', status: 'awaiting_confirmation', head_plan_version: 4, plan: { plan_version: 4, document: { shots: [{ shot_id: 'one', content: '已保存新画面' }] } } }
  vi.stubGlobal('fetch', async (url: string, options: RequestInit) => {
    requests.push({ url, options }); return new Response(JSON.stringify(url.endsWith('/video/plan-revisions') ? updated : url.endsWith('/video/confirm') ? { kind: 'video', status: 'generating' } : { media: updated }))
  })
  const wrapper = mount(VideoTaskPanel, { props: { taskId: 'quick-stale-parent', allowPlanRevision: true, media: { kind: 'video', status: 'awaiting_confirmation', head_plan_version: 3, plan: { plan_version: 3, document: { shots: [{ shot_id: 'one', content: '原画面' }] } } } } })
  await wrapper.get('[data-edit-plan]').trigger('click')
  await wrapper.get('[data-shot-content="0"]').setValue('已保存新画面')
  await wrapper.get('[data-save-plan]').trigger('click'); await flushPromises()
  await wrapper.get('[aria-label="编辑视频方案"] > button').trigger('click')
  await flushPromises(); await wrapper.get('[data-view-plan]').trigger('click')
  expect(wrapper.text()).toContain('方案版本 4')
  await wrapper.get('[data-confirm-plan]').trigger('click'); await wrapper.get('[data-send-confirmation]').trigger('click'); await flushPromises()
  expect(JSON.parse(String(requests.at(-1)!.options.body))).toEqual({ plan_version: 4 })
  wrapper.unmount()
})

it('does not confirm a stale revision response or discard the saved edit when the new version is still planning', async () => {
  const requests: string[] = []
  vi.stubGlobal('fetch', async (url: string) => { requests.push(url); return new Response(JSON.stringify(url.endsWith('/video/plan-revisions') ? { kind: 'video', status: 'planning' } : { media: { kind: 'video', status: 'planning', head_plan_version: 3 } })) })
  const wrapper = mount(VideoTaskPanel, { props: { taskId: 'quick-wait-new', allowPlanRevision: true, media: { kind: 'video', status: 'awaiting_confirmation', head_plan_version: 3, plan: { plan_version: 3, document: { shots: [{ shot_id: 'one', content: '原画面' }] } } } } })
  await wrapper.get('[data-edit-plan]').trigger('click')
  await wrapper.get('[data-shot-content="0"]').setValue('新画面')
  await wrapper.get('[data-edit-confirm-plan]').trigger('click'); await flushPromises()
  expect(requests.some(url => url.endsWith('/video/confirm'))).toBe(false)
  expect(wrapper.text()).toContain('正在读取已保存的新方案')
  await wrapper.setProps({ media: { kind: 'video', status: 'awaiting_confirmation', head_plan_version: 4, plan: { plan_version: 4, document: { shots: [{ shot_id: 'one', content: '新画面' }] } } } }); await flushPromises()
  expect(wrapper.text()).toContain('将按方案版本 4')
  wrapper.unmount()
})

it('submits selected video parameters in the confirmed immutable input and keeps a saved draft on capability errors', async () => {
  const route = reactive({ params: { conversationId: 'video-workspace-input' }, query: {}, path: '/workspace/video-workspace-input' })
  vi.doMock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }))
  vi.doMock('../../src/features/workspace/useTaskStream', () => ({ useTaskStream: () => ({
    tasks: ref([]), details: ref({}), fragments: ref({}), latestTaskId: ref(''), connectionState: ref('open'),
    reconnect: vi.fn(), refreshTask: vi.fn(),
  }) }))
  const draft = draftFor(route.params.conversationId)
  draft.agentId = 'video-agent'
  draft.agents['video-agent'] = { specId: '', instruction: '', parameters: { first_frame_file_id: 'frame', duration_seconds: 12, aspect_ratio: '16:9' } }
  draft.product = { product_id: 'product', version: 'pv', created_at: '', product: { name: '商品', category: '家居' } }
  draft.materials = [{ file_id: 'frame', version: 'fv' }]
  let capabilitiesAvailable = false
  let submitted: Record<string, unknown> | undefined
  vi.stubGlobal('fetch', async (url: string, options: RequestInit) => {
    if (url === '/api/v1/video-options') return capabilitiesAvailable
      ? new Response(JSON.stringify({ duration_tiers: [6, 12], default_duration: 6, aspect_ratios: ['9:16', '16:9'] }))
      : new Response(JSON.stringify({ error: { code: 'INTERNAL_ERROR', message: '视频参数暂不可用。' } }), { status: 503 })
    if (url === '/api/v1/agents') return new Response(JSON.stringify([{ agent_id: 'video-agent', kind: 'video', name: '视频', enabled: true, protocol_version: 'video-agent-v1', input_support: { product_required_fields: ['name'], min_materials: 1, max_materials: 8, instruction_required: false } }]))
    if (url === '/api/v1/quotes') return new Response(JSON.stringify({ credits: 8 }))
    if (url === '/api/v1/tasks') { submitted = JSON.parse(String(options.body)); throw new Error('unknown receipt') }
    throw new Error('Unexpected request ' + url)
  })
  const { default: WorkspaceView } = await import('../../src/features/workspace/WorkspaceView.vue')
  const wrapper = mount(WorkspaceView, { global: { stubs: { TaskCard: true, QuotePanel: true } } })
  await flushPromises()
  expect(wrapper.text()).toContain('视频参数暂不可用')
  expect(wrapper.get('.generate-button').attributes('disabled')).toBeDefined()
  expect(draft.agents['video-agent'].parameters).toMatchObject({ duration_seconds: 12, aspect_ratio: '16:9' })
  capabilitiesAvailable = true
  await wrapper.findAll('button').find(button => button.text() === '重试读取参数')!.trigger('click')
  await flushPromises()
  await wrapper.get('select[data-select-id$="-duration"]').setValue('6')
  await wrapper.get('.generate-button').trigger('click')
  await flushPromises()
  expect(wrapper.text()).toContain('后续确认方案不会再次收费')
  draft.agents['video-agent'].parameters.duration_seconds = 12
  await wrapper.findAll('button').find(button => button.text() === '确认并冻结积分')!.trigger('click')
  await flushPromises()
  expect(submitted).toMatchObject({ input: { parameters: { first_frame_file_id: 'frame', duration_seconds: 6, aspect_ratio: '16:9' } } })
  wrapper.unmount()
  vi.doUnmock('vue-router')
  vi.doUnmock('../../src/features/workspace/useTaskStream')
})
