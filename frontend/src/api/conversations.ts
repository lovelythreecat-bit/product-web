import type { Schema } from '../types/api'
import { request, jsonRequest, id, query } from './client'
export const listConversations = (cursor?:string) => request<Schema<'CursorPage_ConversationSummary_'>>('/api/v1/conversations'+query({cursor}))
export const createConversation = (body:Schema<'ConversationCreate'>) => jsonRequest<Schema<'ConversationSummary'>>('/api/v1/conversations','POST',body)
export const getConversation = (conversationId:string) => request<Schema<'ConversationView'>>('/api/v1/conversations/'+id(conversationId))
export const createProductVersion = (body:Schema<'ProductVersionCreate'>) => jsonRequest<Schema<'ProductVersionView'>>('/api/v1/products/versions','POST',body)
export const getProductVersion = (version:string) => request<Schema<'ProductVersionView'>>('/api/v1/products/versions/'+id(version))
