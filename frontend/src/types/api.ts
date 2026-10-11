import type { components } from './contracts'
export type Schema<K extends keyof components['schemas']> = components['schemas'][K]
export type AdmissionResult = Schema<'AdmissionResult'>
export type SubmitTaskRequest = Schema<'SubmitTaskRequest'>
/** SSE cursors are opaque, scoped to the logged-in user, and never authentication. */
export interface TaskStreamConnection { close(): void }
export function connectTaskEvents(after?: string): EventSource {
  return new EventSource('/api/v1/events' + (after ? '?after=' + encodeURIComponent(after) : ''))
}
