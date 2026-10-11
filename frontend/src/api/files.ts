import type { Schema } from '../types/api'
import { request, jsonRequest, id, query } from './client'
export const uploadFile = (file:File) => request<Schema<'FileVersionRef'>>('/api/v1/files'+query({display_name:file.name}),{method:'POST',body:file})
export const fileContentUrl = (fileId:string) => '/api/v1/files/'+id(fileId)+'/content'
export const deleteFile = (fileId:string, body:Schema<'DeleteRequest'>) => jsonRequest<Schema<'DeleteReceipt'>>('/api/v1/files/'+id(fileId),'DELETE',body)
