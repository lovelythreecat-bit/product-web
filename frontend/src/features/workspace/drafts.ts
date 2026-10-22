import { reactive, watch } from 'vue'
import type { Schema } from '../../types/api'
import { onIdentityChange, session } from '../auth/session'
import type { Intent } from '../../api/client'
import { textParameters } from './textParameters'
import { videoParameters } from './videoParameters'

export interface AgentDraft { specId: string; instruction: string; parameters: Record<string, string | number | boolean> }
export interface Draft {
  agentId: string
  agents: Record<string, AgentDraft>
  product: Schema<'ProductVersionView'> | null
  materials: Schema<'FileVersionRef'>[]
  missingMaterials: number
  sourceWorkId?: string
  sourceTaskId?: string
  regenerationSourceId?: string
  confirmedFreeRegeneration?: boolean
  pending?: Intent<Schema<'SubmitTaskRequest'>> | null
  confirmed?: Schema<'SubmitTaskRequest'> | null
  uncertain?: boolean
}
const drafts = reactive<Record<string, Draft>>({})
const storagePrefix = 'creation-drafts-v1:'
let owner: string | null = null, restoring = false
function restore(userId: string | null) {
  restoring = true
  for (const key of Object.keys(drafts)) delete drafts[key]
  owner = userId
  try {
    // Tab-scoped drafts never survive logout or a different authenticated identity.
    for (const key of Object.keys(sessionStorage)) if (key.startsWith(storagePrefix) && key !== storagePrefix + userId) sessionStorage.removeItem(key)
    if (userId) {
      const saved = JSON.parse(sessionStorage.getItem(storagePrefix + userId) || '{}')
      for (const [id, value] of Object.entries(saved)) {
        const draft = value as Draft
        if (draft && typeof draft.agentId === 'string' && draft.agents && Array.isArray(draft.materials) && typeof draft.missingMaterials === 'number') {
          if (draft.pending) draft.uncertain = true
          drafts[id] = draft
        }
      }
    }
  } catch { /* Storage is optional; authenticated APIs remain authoritative. */ }
  restoring = false
}
onIdentityChange(change => restore(change.userId))
watch(drafts, () => { if (owner && !restoring) try { sessionStorage.setItem(storagePrefix + owner, JSON.stringify(drafts)) } catch { /* Retain the in-memory draft if storage is unavailable/full. */ } }, { deep: true, flush: 'sync' })
export function draftFor(id: string) {
  const userId = session.profile.value?.user_id ?? null
  if (userId !== owner) restore(userId)
  const key = id || 'new'
  if (!drafts[key]) drafts[key] = { agentId: '', agents: {}, product: null, materials: [], missingMaterials: 0 }
  return drafts[key]
}
export function moveDraft(from: string, to: string) { drafts[to] = drafts[from || 'new']; delete drafts[from || 'new'] }
/** A deliberate regeneration copies editable data, never a confirmed charge or pending intent. */
export function copyTaskDraft(source: Draft, to: string): Draft {
  const target = draftFor(to)
  Object.assign(target, JSON.parse(JSON.stringify({
    agentId: source.agentId, agents: source.agents, product: source.product,
    materials: source.materials, missingMaterials: source.missingMaterials,
    sourceTaskId: source.sourceTaskId, sourceWorkId: source.sourceWorkId, regenerationSourceId: source.regenerationSourceId,
  })))
  return target
}
export function taskDraftFor(conversationId: string, taskId: string) {
  return draftFor(conversationId + ':task:' + taskId)
}
/** Seed an editable copy, never attach mutable task snapshot objects to a draft. */
export function restoreTaskDraft(target: Draft, source: Schema<'TaskDetail'>, product: Schema<'ProductVersionView'>) {
  const input = JSON.parse(JSON.stringify(source.input)) as Schema<'InputSnapshot'>
  Object.assign(target, {
    sourceTaskId: source.task.task_id, agentId: source.agent_id,
    product: { ...product, version: input.product_version, product: input.product },
    materials: input.material_versions, missingMaterials: 0,
    agents: { [source.agent_id]: { specId: '', instruction: input.instruction,
      parameters: { ...textParameters(input.parameters || {}), ...videoParameters(input.parameters || {}), ...Object.fromEntries(Object.entries(input.parameters || {}).filter(([key, value]) =>
        typeof value === 'string' && ['platform', 'output_type', 'first_frame_file_id'].includes(key))) } } },
  })
}
export function setSourceDraft(id: string, work: Schema<'WorkDetail'>, product: Schema<'ProductVersionView'>) {
  draftFor(id) // Restore the current owner before writing a source draft for that owner.
  const source = work.source
  drafts[id] = {
    agentId: source.agent_id, sourceWorkId: work.work_id, sourceTaskId: work.task_id,
    regenerationSourceId: ['copy', 'image'].includes(work.kind) ? work.task_id : undefined, product,
    materials: source.materials.filter(x => x.available).map(x => x.file),
    missingMaterials: source.materials.filter(x => !x.available).length,
    agents: { [source.agent_id]: { specId: '', instruction: source.input.instruction,
      parameters: { ...textParameters(source.input.parameters || {}), ...videoParameters(Object.fromEntries(Object.entries(source.input.parameters || {}).filter(([key, value]) => key !== 'first_frame_file_id' || source.materials.some(m => m.available && m.file.file_id === value)))), ...Object.fromEntries(Object.entries(source.input.parameters || {}).filter(([key, value]) =>
        typeof value === 'string' && ['platform', 'output_type', 'first_frame_file_id'].includes(key) &&
        (key !== 'first_frame_file_id' || source.materials.some(m => m.available && m.file.file_id === value))).map(([key, value]) => [key, String(value)])) } } },
  }
}
