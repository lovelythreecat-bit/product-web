import type { Schema } from '../types/api'
import type { Intent } from './client'
import { request, id, query, sendIntent, createIntent } from './client'
export const getTask = (taskId:string) => request<Schema<'TaskDetail'>>('/api/v1/tasks/'+id(taskId))
export const listTasks = (conversationId:string,cursor?:string) => request<Schema<'CursorPage_TaskView_'>>('/api/v1/tasks'+query({conversation_id:conversationId,cursor}))
export const getInvestigation = (taskId:string) => request<Schema<'OwnerView'>>('/api/v1/tasks/'+id(taskId)+'/investigation')
/** The caller must retain the confirmed immutable body with this key. No automatic retry. */
export const submitTask = (key:string,body:Schema<'SubmitTaskRequest'>) => sendIntent<Schema<'SubmitTaskRequest'>,Schema<'AdmissionResult'>>('/api/v1/tasks',createIntent(body,key))
export const submitTaskIntent = (intent:Intent<Schema<'SubmitTaskRequest'>>) => sendIntent<Schema<'SubmitTaskRequest'>,Schema<'AdmissionResult'>>('/api/v1/tasks',intent)
