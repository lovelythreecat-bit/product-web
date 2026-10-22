import type { Schema } from '../types/api'
import { id, jsonRequest, query, request } from './client'
export type ManagedUser = Schema<'ManagedUserView'>
export interface UserEdit { expected_auth_version:number; expected_profile_version:string; account:string; nickname:string|null; shop_name:string|null; category:string|null; email:string|null; phone:string|null; role:'admin'|'user'; status:'active'|'disabled'; reason:string }
export interface PasswordReset { expected_auth_version:number; new_password:string; reason:string }
export interface UserDelete { expected_auth_version:number; reason:string }
export interface Adjustment { business_key:string; delta:number; reason:string }
export interface AdjustmentIntent { user_id:string; body:Adjustment }
export interface AdjustmentReceipt extends Adjustment { ledger_id:string; user_id:string; actor_id:string }
const root='/api/v1/admin/managed-users'
export const listUsers = (cursor?:string,status?:string,q?:string,page?:number) => request<Schema<'NumberedPage_ManagedUserView_'>>(root+query({cursor,status,q,page}))
export const getUser = (user:string) => request<ManagedUser>(root+'/'+id(user))
export const updateUser = (user:string,body:UserEdit) => jsonRequest<ManagedUser>(root+'/'+id(user),'PATCH',body)
export const resetPassword = (user:string,body:PasswordReset) => jsonRequest<ManagedUser>(root+'/'+id(user)+'/password-reset','POST',body)
export const deleteUser = (user:string,body:UserDelete) => jsonRequest<void>(root+'/'+id(user),'DELETE',body)
export const adjustCredits = (intent:AdjustmentIntent) => request<AdjustmentReceipt>(root+'/'+id(intent.user_id)+'/credit-adjustments',{method:'POST',body:JSON.stringify(intent.body),key:intent.body.business_key})
const prefix='admin-adjustment-intent:v1:'
export function restoreAdjustment(actor:string):AdjustmentIntent|null {
 const raw=localStorage.getItem(prefix+actor);if(!raw)return null
 const intent=JSON.parse(raw) as AdjustmentIntent
 if(!intent.user_id || !intent.body?.business_key || !Number.isSafeInteger(intent.body.delta) || !intent.body.delta || !intent.body.reason?.trim())throw Error('待确认积分调整记录无法读取，请保留记录并联系维护人员。')
 return intent
}
export function rememberAdjustment(actor:string,user_id:string,delta:number,reason:string):AdjustmentIntent {
 if(restoreAdjustment(actor))throw Error('有一笔积分调整待确认，请先重试原请求。')
 const intent={user_id,body:{business_key:crypto.randomUUID(),delta,reason}}
 localStorage.setItem(prefix+actor,JSON.stringify(intent));return intent
}
export function forgetAdjustment(actor:string,businessKey:string) {
 if(restoreAdjustment(actor)?.body.business_key===businessKey)localStorage.removeItem(prefix+actor)
}
// Financial intents survive logout, 401 and account switches. Each actor reads
// only their own persisted key; erase it only after a verified receipt/rejection.
