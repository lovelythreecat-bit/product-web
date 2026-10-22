import { expect, it } from 'vitest'
import { draftFor, setSourceDraft } from '../../src/features/workspace/drafts'
import { computed, effectScope, nextTick, watch } from 'vue'
import { mount } from '@vue/test-utils'
import AgentSelector from '../../src/components/AgentSelector.vue'
import type { Schema } from '../../src/types/api'

it('restoring a conversation keeps its creation type selected without an agent dropdown', async () => {
  const agents = [
    { agent_id: 'copy-agent', name: 'Copy', kind: 'copy', enabled: true },
    { agent_id: 'video-agent', name: 'Video', kind: 'video', enabled: true },
  ] as Schema<'AgentVersion'>[]
  const wrapper = mount(AgentSelector, { props: { agents, modelValue: 'copy-agent' } })
  await wrapper.findAll('button')[0].trigger('click')
  await wrapper.setProps({ modelValue: 'video-agent' })
  expect(wrapper.find('select').exists()).toBe(false)
  expect(wrapper.findAll('button')[2].attributes('aria-pressed')).toBe('true')
  wrapper.unmount()
})

it('the first draft remains reactive so choosing an Agent triggers its real form load', async () => {
  const scope = effectScope()
  const selected: string[] = []
  const id = 'first-reactive-' + crypto.randomUUID()
  const draft = scope.run(() => {
    const value = computed(() => draftFor(id))
    watch(() => value.value.agentId, id => selected.push(id))
    return value
  })!
  draft.value.agentId = 'copy'
  await nextTick()
  expect(selected).toEqual(['copy'])
  scope.stop()
})

it('isolates product/input drafts between conversations and parameters between manually selected Agents', () => {
  const first = draftFor('first'), second = draftFor('second')
  first.agentId = 'copy'; first.agents.copy = { instruction: 'original copy', specId: 'copy-spec', parameters: { tone: '专业' } }
  first.agents.video = { instruction: 'original video', specId: 'video-spec', parameters: { aspect_ratio: '16:9', subtitles: false } }
  first.agentId = 'video'; first.agents.video.instruction = 'edited video'
  expect(first.agents.copy).toEqual({ instruction: 'original copy', specId: 'copy-spec', parameters: { tone: '专业' } })
  expect(second.agents).toEqual({})
  expect(second.materials).toEqual([])
  expect(first.agents.video.parameters).toEqual({ aspect_ratio: '16:9', subtitles: false })
})


it('new creation from an old work retains product and instruction but removes retired spec options', () => {
 const product={product_id:'p',version:'pv1',created_at:'2026-10-15T00:00:00Z',product:{name:'商品'}} as Schema<'ProductVersionView'>
 setSourceDraft('old-work-regeneration', {work_id:'w',source:{agent_id:'a',input:{instruction:'原要求',parameters:{ratio:'1:1'}},materials:[],task:{quote:{spec_id:'retired'}}}} as unknown as Schema<'WorkDetail'>,product)
 expect(draftFor('old-work-regeneration').agents.a).toEqual({specId:'',instruction:'原要求',parameters:{}})
 expect(draftFor('old-work-regeneration').product).toEqual(product)
})

it('regenerating a text work restores its typed scene requirements including numeric maximum', () => {
 const product={product_id:'p',version:'pv1',created_at:'2026-10-15T00:00:00Z',product:{name:'商品'}} as Schema<'ProductVersionView'>
 const parameters={copy_type:'商品标题',platform:'京东',audience:'学生',tone:'简洁',max_chars:50,extra_instructions:'突出材质'}
 setSourceDraft('text-scene-regeneration',{work_id:'w',source:{agent_id:'a',input:{instruction:'原要求',parameters},materials:[]}} as unknown as Schema<'WorkDetail'>,product)
 expect(draftFor('text-scene-regeneration').agents.a.parameters).toEqual(parameters)
})

it.each(['copy', 'image', 'video'] as const)('retains the source task for %s work regeneration without granting a video allowance', kind => {
 const product = { product_id: 'p', version: 'pv', created_at: '', product: { name: '杯子' } } as Schema<'ProductVersionView'>
 setSourceDraft('source-' + kind, { kind, work_id: 'work', task_id: 'source-task', source: { agent_id: 'agent', input: { instruction: '原要求', parameters: {} }, materials: [] } } as unknown as Schema<'WorkDetail'>, product)
 expect(draftFor('source-' + kind).sourceTaskId).toBe('source-task')
 expect(draftFor('source-' + kind).regenerationSourceId).toBe(kind === 'video' ? undefined : 'source-task')
})
