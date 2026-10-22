import type { Schema } from '../types/api'
import { request, jsonRequest } from './client'
import type { VideoOptions } from '../features/workspace/videoParameters'
export const listAgents = () => request<Schema<'AgentVersion'>[]>('/api/v1/agents')
export const getVideoOptions = () => request<VideoOptions>('/api/v1/video-options')
export const quote = (body:Schema<'QuoteRequest'>) => jsonRequest<Schema<'Quote'>>('/api/v1/quotes','POST',body)
