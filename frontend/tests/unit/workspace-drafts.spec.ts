import { expect, it } from 'vitest'
import { draftFor } from '../../src/features/workspace/drafts'
import { computed, effectScope, nextTick, watch } from 'vue'
import { mount } from '@vue/test-utils'
import AgentSelector from '../../src/components/AgentSelector.vue'
import type { Schema } from '../../src/types/api'

it('restoring a conversation keeps its manually selected Agent visible across kind filters', async () => {
  const agents = [
    { agent_id: 'copy-agent', name: 'Copy', kind: 'copy', enabled: true },
    { agent_id: 'video-agent', name: 'Video', kind: 'video', enabled: true },
  ] as Schema<'AgentVersion'>[]
  const wrapper = mount(AgentSelector, { props: { agents, modelValue: 'copy-agent' } })
  await wrapper.findAll('button')[0].trigger('click')
  await wrapper.setProps({ modelValue: 'video-agent' })
  expect((wrapper.get('select').element as HTMLSelectElement).value).toBe('video-agent')
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
