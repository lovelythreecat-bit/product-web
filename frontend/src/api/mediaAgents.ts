import { createIntent, id, query, request, sendIntent, type Intent } from './client'

export type MediaKind = 'image' | 'video'
export type MediaResource = 'services' | 'model-configs' | 'agent-configs' | 'adapter-types' | 'model-profiles' | 'adapter-bindings' | 'settings'
export type MediaRole = 'planner' | 'video' | 'voice' | 'music' | 'visual'
export type Json = string | number | boolean | null | Json[] | { [key: string]: Json }
export interface MediaRecord {
  [key: string]: Json | undefined
  id?: string; profile_id?: string; name?: string; model?: string | null; base_url?: string | null
  version?: number; configuration_revision?: number; enabled?: boolean; has_api_key?: boolean
  role?: MediaRole; adapter?: string; protocol?: string; service_id?: string; description?: string | null
  parameters?: Record<string, Json>; image_models?: Record<string, string>; stages?: Record<string, string>
  secret_presence?: Record<string, boolean>; roles?: MediaRole[]; required_fields?: string[]; secret_fields?: string[]
}
export interface MediaConnection {
  id: string | null; kind: MediaKind; base_url: string | null; revision: number
  has_service_key: boolean; has_management_key: boolean; default_config_id: string | null; image_model: string | null
}
export interface MediaConnectionUpdate {
  expected_revision: number; base_url: string; service_key?: string; management_key?: string
  default_config_id?: string | null; image_model?: string | null
}
export interface MediaPage { items: MediaRecord[]; limit: number; offset: number; total: number }
export type MediaList = MediaRecord[] | MediaPage | MediaRecord
export const recordId = (row: MediaRecord) => row.id ?? row.profile_id ?? ''
const root = (kind: MediaKind) => '/api/v1/admin/media-agents/' + kind
const resourcePath = (kind: MediaKind, resource: MediaResource, configId?: string) => root(kind) + '/resources/' + resource + (configId ? '/' + id(configId) : '')
export const getMediaConnection = (kind: MediaKind) => request<MediaConnection>(root(kind) + '/connection')
export const saveMediaConnection = (kind: MediaKind, body: MediaConnectionUpdate) => request<MediaConnection>(root(kind) + '/connection', { method: 'PATCH', body: JSON.stringify(body) })
export interface ImageModelSetting {
  base_url: string; model: string; protocol: 'chat_completions' | 'openai_images' | 'openrouter_images'
  has_api_key: boolean; enabled: boolean
}
export interface ImageModels {
  revision: number; versions: Record<string, number>
  text_model: ImageModelSetting | null; image_model: ImageModelSetting | null
}
export type ImageModelWrite = Omit<ImageModelSetting, 'has_api_key' | 'enabled'> & { api_key?: string }
export interface ImageModelsUpdate {
  expected_revision: number; expected_versions: Record<string, number>
  text_model: ImageModelWrite; image_model: ImageModelWrite
}
export const getImageModels = () => request<ImageModels>(root('image') + '/models')
export const saveImageModels = (body: ImageModelsUpdate) => request<ImageModels>(root('image') + '/models', {method:'PATCH',body:JSON.stringify(body)})
export type VideoModelRole = 'planner' | 'video' | 'visual'
export type VideoAdapter = 'openai_chat' | 'seedance' | 'wan' | 'openai_vision'
export interface VideoModel {
  profile_id: string; version: number; adapter: VideoAdapter; base_url: string | null; model: string | null
  enabled: boolean; has_api_key: boolean; max_segment_seconds: number | string | null
}
export interface VideoModels {
  revision: number; configuration_revision: number; models: Record<VideoModelRole, VideoModel | null>
  bindings: Record<MediaRole, {adapter: string | null; profile_id: string | null}> & {configuration_revision:number}
}
export interface VideoModelWrite {
  expected_revision: number; expected_configuration_revision: number
  expected_profile_id: string | null; expected_profile_version: number | null
  enabled: boolean; adapter: VideoAdapter; base_url?: string; model?: string; api_key?: string
  max_segment_seconds?: number
}
export const getVideoModels = () => request<VideoModels>(root('video')+'/models')
export const saveVideoModel = (role:VideoModelRole,body:VideoModelWrite) => request<VideoModels>(root('video')+'/models/'+role,{method:'PATCH',body:JSON.stringify(body)})
export interface VideoAudio {revision:number;enabled:boolean}
export const getVideoAudio = () => request<VideoAudio>(root('video')+'/audio')
export const saveVideoAudio = (body:{expected_revision:number;expected_configuration_revision:number;enabled:boolean}) => request<VideoAudio>(root('video')+'/audio',{method:'PATCH',body:JSON.stringify(body)})
export const saveVideoSettings = (config:Record<string,Json>,connectionRevision:number) => request<MediaRecord>(root('video')+'/resources/settings',{
  method:'PATCH',body:JSON.stringify({config,expected_connection_revision:connectionRevision})})
export const listMediaResources = (kind: MediaKind, resource: MediaResource, offset = 0, limit = 20) => request<MediaList>(resourcePath(kind, resource) + query({ limit, offset }))
export const getMediaResource = (kind: MediaKind, resource: MediaResource, configId?: string) => request<MediaRecord>(resourcePath(kind, resource, configId))
export function saveMediaResource(kind: MediaKind, resource: MediaResource, configId: string | undefined, config: Record<string, Json>, creating = false, intent?: Intent<{config: Record<string,Json>}>) {
  const path = resourcePath(kind, resource, configId), body = { config }
  return creating ? sendIntent<typeof body, MediaRecord>(path, intent ?? createIntent(body)) : request<MediaRecord>(path, { method: 'PATCH', body: JSON.stringify(body) })
}
/** Dependency selectors include all pages; a repeated page is a protocol error. */
export async function loadMediaOptions(kind: MediaKind, resource: MediaResource): Promise<MediaRecord[]> {
  const all: MediaRecord[] = [], seen = new Set<string>()
  let offset = 0
  while (true) {
    const result = await listMediaResources(kind, resource, offset, 100)
    const page = Array.isArray(result) ? result : 'items' in result && Array.isArray(result.items) ? result.items as MediaRecord[] : []
    if (page.some(row => seen.has(recordId(row)))) throw new Error('配置列表分页异常，请刷新后重试。')
    page.forEach(row => seen.add(recordId(row)))
    all.push(...page); offset += page.length
    const total = !Array.isArray(result) && typeof result.total === 'number' ? result.total : null
    if (!page.length || (total !== null ? offset >= total : page.length < 100)) return all
  }
}
