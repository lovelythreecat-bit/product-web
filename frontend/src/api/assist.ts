import type { Schema } from '../types/api'
import type { Intent } from './client'
import { sendIntent } from './client'
export const preparePrompt = (intent:Intent<Schema<'AssistRequest'>>) => sendIntent<Schema<'AssistRequest'>,Schema<'AssistProposal'>>('/api/v1/assist/prompts',intent)
