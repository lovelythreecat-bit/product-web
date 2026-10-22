/** Owned UI projection: media phases evolve independently of task state_version. */
export interface VideoShot {
  shot_id?: string; content?: string; action?: string; shot_size?: string; camera?: string
  start_frame?: number; end_frame?: number; subtitle_text?: string; voiceover_text?: string
}
export interface VideoPlanDocument {
  creative?: string; audience?: string; selling_points?: string[]
  shared_visual?: Record<string, string | null>; shots?: VideoShot[]
  duration_seconds?: number; aspect_ratio?: string; subtitles?: boolean
  voiceover?: boolean; music?: boolean; music_direction?: string
  language?: string; voice_preference?: string
}
export interface VideoPlanView { plan_version: number; document: VideoPlanDocument }
export interface VideoPlanRevision {
  plan_version: number
  instruction?: string
  patch?: { music_direction?: string; shot_texts?: Array<Pick<VideoShot, 'content' | 'action' | 'shot_size' | 'camera' | 'subtitle_text' | 'voiceover_text'> & { shot_id: string }> }
}
export interface MediaTaskState {
  revision?: number
  kind: 'image' | 'video'; status?: string; core_status?: string | null
  questions?: string[]; head_plan_version?: number; plan?: VideoPlanView | null
  generation_id?: string | null; confirmed_plan_version?: number | null; artifact_id?: string | null
}
export function taskMedia(detail: unknown): MediaTaskState | null {
  const value = detail && typeof detail === 'object' ? (detail as { media?: unknown }).media : null
  if (!value || typeof value !== 'object' || !['image', 'video'].includes(String((value as MediaTaskState).kind))) return null
  return value as MediaTaskState
}
export function mediaStageLabel(media: MediaTaskState | null): string {
  if (!media) return ''
  if (media.kind === 'image' && media.status === 'completed' && media.core_status === 'needs_input') return '等待补充资料'
  const labels: Record<string, string> = {
    pending: '准备中', queued: '排队中', planning: '正在规划视频', awaiting_input: '等待补充资料',
    awaiting_confirmation: '等待确认方案', generating: '正在生成视频', running: '正在处理',
    completed: '正在核验完整成果', failed: '执行异常，等待核查', interrupted: '执行中断，等待核查',
    generation_uncertain: '生成状态待核查', needs_input: '等待补充资料',
  }
  return labels[media.status || ''] || '正在核对任务状态'
}
