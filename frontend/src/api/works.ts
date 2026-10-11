import type { Schema } from '../types/api'
import { request, jsonRequest, id, query } from './client'
export const listWorks = (filters:{kind?:'copy'|'image'|'video';conversation_id?:string;task_id?:string;cursor?:string}={}) => request<Schema<'CursorPage_WorkView_'>>('/api/v1/works'+query(filters))
export const getWork = (workId:string) => request<Schema<'WorkDetail'>>('/api/v1/works/'+id(workId))
export const deleteWork = (workId:string,body:Schema<'DeleteRequest'>) => jsonRequest<Schema<'DeleteReceipt'>>('/api/v1/works/'+id(workId),'DELETE',body)
