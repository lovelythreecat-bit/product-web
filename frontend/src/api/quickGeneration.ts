import type { Schema } from '../types/api'
import { id, jsonRequest, request } from './client'

export type QuickView = Schema<'QuickView'>
export type QuickDraft = Required<Schema<'QuickDraft'>>
export type QuickKind = Schema<'QuickPrepare'>['kind']
export type ImageOutput = NonNullable<Schema<'QuickPrepare'>['outputs']>[number]
const base = '/api/v1/quick-generation'
export const listQuickRuns = () => request<Schema<'QuickSummary'>[]>(base)
export const createQuickRun = (runId: string) => jsonRequest<QuickView>(base, 'POST', { run_id: runId })
export const getQuickRun = (runId: string) => request<QuickView>(base + '/' + id(runId))
export const saveQuickRun = (runId: string, version: number, draft: QuickDraft) => jsonRequest<QuickView>(base + '/' + id(runId), 'PATCH', { version, draft })
export const prepareQuickRun = (runId: string, version: number, kind: QuickKind, outputs?: ImageOutput[], itemIndex?: number) => jsonRequest<QuickView>(base + '/' + id(runId) + '/prepare', 'POST', { version, kind, ...(outputs ? { outputs } : {}), ...(itemIndex !== undefined ? { item_index: itemIndex } : {}) })
export const submitQuickBatch = (runId: string, batchId: string) => jsonRequest<QuickView>(base + '/' + id(runId) + '/batches/' + id(batchId) + '/submit', 'POST', {})
export const cancelQuickBatch = (runId: string, batchId: string) => jsonRequest<QuickView>(base + '/' + id(runId) + '/batches/' + id(batchId) + '/cancel', 'POST', {})
export const advanceQuickRun = (runId: string, version: number, action: Schema<'QuickAdvance'>['action']) => jsonRequest<QuickView>(base + '/' + id(runId) + '/advance', 'POST', { version, action })
