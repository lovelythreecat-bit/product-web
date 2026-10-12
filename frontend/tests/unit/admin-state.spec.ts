import { beforeEach, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
const identity=vi.hoisted(()=>({epoch:{value:0},listeners:[] as ((v:{userId:string|null;reason:string})=>void)[]}))
vi.mock('../../src/features/auth/session',()=>({session:{epoch:identity.epoch},onIdentityChange:(fn:(v:{userId:string|null;reason:string})=>void)=>identity.listeners.push(fn)}))
import { rememberGrant, restoreGrant, forgetGrant } from '../../src/features/admin/creditIntent'
import { useAdminRequest } from '../../src/features/admin/shared'
beforeEach(()=>{localStorage.clear();identity.epoch.value=0})
it('restores exact serialized grant body and key across remount and blocks replacement',()=>{
 const input={user_id:'target',amount:17,reason:'original'}
 const first=rememberGrant('admin',input)
 input.amount=99
 expect(restoreGrant('admin')).toEqual(first)
  forgetGrant('admin','older-intent-key')
  expect(restoreGrant('admin')).toEqual(first)
 expect(JSON.parse(restoreGrant('admin')!.body).amount).toBe(17)
 expect(()=>rememberGrant('admin',{...input,reason:'second'})).toThrow('等待核对')
 expect(restoreGrant('admin')).toEqual(first)
})
it('corrupt pending storage fails closed without generating a replacement',()=>{
 localStorage.setItem('admin-credit-intent:v1:admin','broken')
 expect(()=>rememberGrant('admin',{user_id:'target',amount:17,reason:'original'})).toThrow()
 expect(localStorage.getItem('admin-credit-intent:v1:admin')).toBe('broken')
})
it('same actor restoration preserves intent but logout and another identity clear private records',()=>{
 const first=rememberGrant('admin',{user_id:'target',amount:17,reason:'original'})
 identity.listeners.forEach(fn=>fn({userId:'admin',reason:'authenticated'}))
 expect(restoreGrant('admin')).toEqual(first)
 identity.listeners.forEach(fn=>fn({userId:'other',reason:'authenticated'}))
 expect(restoreGrant('admin')).toBeNull()
 rememberGrant('other',{user_id:'target',amount:17,reason:'original'})
 identity.listeners.forEach(fn=>fn({userId:null,reason:'unauthorized'}))
 expect(restoreGrant('other')).toBeNull()
})
it('late admin data cannot apply after epoch change or page unmount',async()=>{
 for(const boundary of ['epoch','unmount']) {
  let scope!:ReturnType<typeof useAdminRequest>
  const wrapper=mount(defineComponent({setup(){scope=useAdminRequest();return()=>null}}))
  let resolve!:(s:string)=>void
  const apply=vi.fn()
  const pending=scope.run(()=>new Promise<string>(r=>{resolve=r}),apply)
  if(boundary==='epoch')identity.epoch.value++;else wrapper.unmount()
  resolve('private data')
  expect(await pending).toBe(false)
  expect(apply).not.toHaveBeenCalled()
  if(boundary==='epoch')wrapper.unmount()
 }
})
