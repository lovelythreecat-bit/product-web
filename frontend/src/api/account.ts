import type { Schema } from '../types/api'
import { request, query } from './client'

export type LedgerEntry = Schema<'LedgerEntryView'> & { task_name?: string | null }
export type LedgerConsumption = { copy: number; image: number; video: number; other: number }
export type LedgerPage = Omit<Schema<'AccountLedgerPage'>, 'items'> & {
  items: LedgerEntry[]
  consumption?: LedgerConsumption
}
export type LedgerFilters = { start_time?: string; end_time?: string }
export const getAccount = () => request<Schema<'AccountView'>>('/api/v1/account')
export const listLedger = (cursor?: string, filters: LedgerFilters = {}, page?: number) => request<LedgerPage>('/api/v1/account/ledger' + query({ cursor, ...filters, page }))
