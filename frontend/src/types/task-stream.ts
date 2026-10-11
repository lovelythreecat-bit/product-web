import type { Ref } from 'vue'
import type { Schema } from './api'
/** T18c implements the consumer. Persistent events carry state, never final works. */
export type TaskEventPayload = Schema<'TaskEventPayload'>
export type ResetEvent = Schema<'ResetEvent'>
export type TransientFragment = Schema<'TransientFragment'>
export interface TaskStreamState {
  tasks: Ref<Schema<'TaskView'>[]>
  connectionState: Ref<'connecting'|'open'|'recovering'|'closed'>
  reconnect(): Promise<void>
}
