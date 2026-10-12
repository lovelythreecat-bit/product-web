import { reactive, watch } from 'vue'
import type { Schema } from '../../types/api'
import { onIdentityChange, session } from '../auth/session'
import type { Intent } from '../../api/client'

export interface AgentDraft { specId: string; instruction: string; parameters: Record<string, string | number | boolean> }
export interface Draft {
  agentId: string
  agents: Record<string, AgentDraft>
  product: Schema<'ProductVersionView'> | null
  materials: Schema<'FileVersionRef'>[]
  missingMaterials: number
  sourceWorkId?: string
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
export function setSourceDraft(id: string, work: Schema<'WorkDetail'>, product: Schema<'ProductVersionView'>) {
  const source = work.source
  drafts[id] = {
    agentId: source.agent_id, sourceWorkId: work.work_id, product,
    materials: source.materials.filter(x => x.available).map(x => x.file),
    missingMaterials: source.materials.filter(x => !x.available).length,
    agents: { [source.agent_id]: { specId: source.task.quote.spec_id, instruction: source.input.instruction, parameters: { ...source.input.parameters } as AgentDraft['parameters'] } },
  }
}
