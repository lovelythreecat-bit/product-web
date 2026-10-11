import type { Schema } from '../types/api'
import { request, query } from './client'
export const getAccount = () => request<Schema<'AccountView'>>('/api/v1/account')
export const listLedger = (cursor?:string) => request<Schema<'CursorPage_LedgerEntryView_'>>('/api/v1/account/ledger'+query({cursor}))
