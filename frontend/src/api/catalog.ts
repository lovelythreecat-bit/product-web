import type { Schema } from '../types/api'
import { request, jsonRequest, id } from './client'
export const listAgents = () => request<Schema<'AgentVersion'>[]>('/api/v1/agents')
export const listSpecs = (agentId:string) => request<Schema<'SpecVersion'>[]>('/api/v1/agents/'+id(agentId)+'/specs')
export const quote = (body:Schema<'QuoteRequest'>) => jsonRequest<Schema<'Quote'>>('/api/v1/quotes','POST',body)
