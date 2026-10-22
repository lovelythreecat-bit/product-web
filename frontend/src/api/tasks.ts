import type { Schema } from '../types/api'
import type { Intent } from './client'
import type { MediaTaskState } from '../types/media'
import type { VideoPlanRevision } from '../types/media'
import { request, id, query, sendIntent, createIntent, jsonRequest } from './client'
export type RegenerationQuote = Schema<'RegenerationQuote'>
export const getRegenerationQuote = (taskId: string, body: Schema<'RegenerationQuoteRequest'>) => jsonRequest<RegenerationQuote>('/api/v1/tasks/' + id(taskId) + '/regeneration-quote', 'POST', body)
export const getTaskHistory = (taskId: string) => request<Schema<'TaskDetail'>[]>('/api/v1/tasks/' + id(taskId) + '/history')
export const getTask = (taskId:string,signal?:AbortSignal) => request<Schema<'TaskDetail'>>('/api/v1/tasks/'+id(taskId),{signal})
export const deleteTask = (taskId: string) => request<void>('/api/v1/tasks/' + id(taskId), { method: 'DELETE' })
export const listTasks = (conversationId?:string,cursor?:string,signal?:AbortSignal,taskType?:'ordinary') => request<Schema<'CursorPage_TaskView_'>>('/api/v1/tasks'+query({conversation_id:conversationId,cursor,task_type:taskType}),{signal})
export const getInvestigation = (taskId:string) => request<Schema<'OwnerView'>>('/api/v1/tasks/'+id(taskId)+'/investigation')
/** The caller must retain the confirmed immutable body with this key. No automatic retry. */
export const submitTask = (key:string,body:Schema<'SubmitTaskRequest'>) => sendIntent<Schema<'SubmitTaskRequest'>,Schema<'AdmissionResult'>>('/api/v1/tasks',createIntent(body,key))
export const submitTaskIntent = (intent:Intent<Schema<'SubmitTaskRequest'>>) => sendIntent<Schema<'SubmitTaskRequest'>,Schema<'AdmissionResult'>>('/api/v1/tasks',intent)
export const confirmVideoPlan = (taskId: string, intent: Intent<{ plan_version: number }>) => sendIntent<{ plan_version: number }, MediaTaskState>('/api/v1/tasks/' + id(taskId) + '/video/confirm', intent)
export const supplementVideoInputs = (taskId: string, intent: Intent<{ text: string }>) => sendIntent<{ text: string }, MediaTaskState>('/api/v1/tasks/' + id(taskId) + '/video/inputs', intent)
export const reviseVideoPlan = (taskId: string, intent: Intent<VideoPlanRevision>) => sendIntent<VideoPlanRevision, MediaTaskState>('/api/v1/tasks/' + id(taskId) + '/video/plan-revisions', intent)
export const retryFailedTask = (taskId: string, intent: Intent<Record<string, never>>) => sendIntent<Record<string, never>, Schema<'AdmissionResult'>>('/api/v1/tasks/' + id(taskId) + '/retry', intent)
export const releaseFailedTask = (taskId: string, intent: Intent<Record<string, never>>) => sendIntent<Record<string, never>, Schema<'TaskView'>>('/api/v1/tasks/' + id(taskId) + '/release', intent)
