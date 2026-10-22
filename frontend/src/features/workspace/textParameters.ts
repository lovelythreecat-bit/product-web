export const textParameterKeys = [
  'copy_type', 'platform', 'audience', 'tone', 'max_chars', 'extra_instructions', 'language',
] as const

const labels: Record<string, string> = {
  copy_type: '文案类型', platform: '目标平台', audience: '目标人群', tone: '语气',
  extra_instructions: '额外协作要求', language: '输出语言',
}

/** Preserve numeric types for task, quote and assist inputs. Empty means upstream default. */
export function textParameters(source: Record<string, unknown>): Record<string, string | number | boolean> {
  const parameters: Record<string, string | number | boolean> = {}
  for (const key of textParameterKeys) {
    const value = source[key]
    if (value !== '' && (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean')) parameters[key] = value
  }
  return parameters
}

export function validateTextParameters(source: Record<string, unknown>): string {
  const maximum = source.max_chars
  if (maximum !== undefined && maximum !== null && maximum !== '' &&
      (typeof maximum !== 'number' || !Number.isSafeInteger(maximum) || maximum < 1)) {
    return '最大字符数请填写正整数，留空表示不限制。'
  }
  for (const key of textParameterKeys) {
    if (key !== 'max_chars' && source[key] !== undefined && typeof source[key] !== 'string') {
      return `${labels[key]}请填写文本。`
    }
  }
  return ''
}
