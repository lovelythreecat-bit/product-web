export interface VideoOptions {
  duration_tiers: number[]
  default_duration: number
  aspect_ratios: string[]
}

/** Preserve only the protocol's editable parameters; absence keeps historical inputs exact. */
export function videoParameters(values: Record<string, unknown>): Record<string, string | number> {
  return Object.fromEntries(Object.entries(values).filter(([key, value]) =>
    key === 'duration_seconds' ? typeof value === 'number' :
      ['first_frame_file_id', 'aspect_ratio'].includes(key) && typeof value === 'string')) as Record<string, string | number>
}

export function validateVideoParameters(values: Record<string, unknown>, options: VideoOptions): string {
  if (!options.duration_tiers.includes(Number(values.duration_seconds)) || typeof values.duration_seconds !== 'number') return '请选择当前支持的视频时长。'
  if (!options.aspect_ratios.includes(String(values.aspect_ratio || ''))) return '请选择当前支持的画面比例。'
  return ''
}
