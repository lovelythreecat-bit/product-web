import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
const mocks = vi.hoisted(() => ({ authenticate:vi.fn(), replace:vi.fn(), push:vi.fn(), listWorks:vi.fn(), getWork:vi.fn(), deleteWork:vi.fn(), listLedger:vi.fn(), refreshAccount:vi.fn(), saveProfile:vi.fn(), getTask:vi.fn(), setSourceDraft:vi.fn(), uploadFile:vi.fn() }))
const identity = vi.hoisted(() => ({ profile:{value:{user_id:'owner',account:'merchant',nickname:'原昵称',bio:'原简介',role:'user',shop_name:'原店铺',category:'家居',email:null as string|null,phone:null as string|null,avatar:null,status:'active',created_at:'2026-10-09T00:00:00Z',last_login_at:null}},account:{value:{available:90,frozen:10,consumed:20,credited_total:120}},epoch:{value:1},busy:{value:false},error:{value:''} }))
vi.mock('vue-router',()=>({useRouter:()=>({replace:mocks.replace,push:mocks.push})}))
vi.mock('../../src/features/auth/session',()=>({session:{...identity,authenticate:mocks.authenticate,refreshAccount:mocks.refreshAccount,saveProfile:mocks.saveProfile}}))
vi.mock('../../src/api/works',()=>({listWorks:mocks.listWorks,getWork:mocks.getWork,deleteWork:mocks.deleteWork}))
vi.mock('../../src/api/account',()=>({listLedger:mocks.listLedger}))
vi.mock('../../src/api/tasks',()=>({getTask:mocks.getTask}))
vi.mock('../../src/api/files',()=>({uploadFile:mocks.uploadFile,fileContentUrl:(id:string)=>'/api/v1/files/'+id+'/content'}))
vi.mock('../../src/features/workspace/drafts',()=>({setSourceDraft:mocks.setSourceDraft}))
import AuthForm from '../../src/features/auth/AuthForm.vue'
import AccountView from '../../src/features/account/AccountView.vue'
import WorksView from '../../src/features/works/WorksView.vue'
const overlay=defineComponent({props:['open'],emits:['update:open'],template:'<section v-if="open"><slot/><button @click="$emit(\'update:open\',false)">关闭测试弹层</button><slot name="actions"/></section>'})
const global={stubs:{AppDrawer:overlay,AppDialog:overlay,RouterLink:{template:'<a><slot/></a>'}}}
const work={work_id:'work-1',task_id:'task-1',conversation_id:'conversation-1',kind:'copy',created_at:'2026-10-13T00:00:00Z',items:[],source:{policy_versions:{},input:{product:{name:'保温杯'},parameters:{ratio:'1:1'},instruction:'仅原始指令'},task:{state:'SUCCEEDED',settlement_state:'CONSUMED',quote:{credits:8}},materials:[],ledger_ids:['ledger-1'],credit_reservation_id:'reservation-1'}}
beforeEach(()=>{vi.clearAllMocks();identity.profile.value.nickname='原昵称';identity.profile.value.bio='原简介';mocks.authenticate.mockResolvedValue(true);mocks.listWorks.mockResolvedValue({items:[work],next_cursor:null,page:1,page_size:10,total:1});mocks.getWork.mockResolvedValue(work);mocks.listLedger.mockResolvedValue({items:[],next_cursor:null,page:1,page_size:20,total:0});mocks.refreshAccount.mockResolvedValue(identity.account.value);mocks.saveProfile.mockResolvedValue(undefined)})
it('confirmation mismatch blocks registration and matching retry reuses the registration intent',async()=>{
 const wrapper=mount(AuthForm,{props:{register:true},global})
 await wrapper.get('#auth-account').setValue('merchant');await wrapper.get('#auth-password').setValue('password-long');await wrapper.get('#auth-confirmation').setValue('different-password');await wrapper.get('form').trigger('submit')
 expect(mocks.authenticate).not.toHaveBeenCalled();expect(wrapper.text()).toContain('两次密码不一致')
 mocks.authenticate.mockRejectedValueOnce(Error('network'));await wrapper.get('#auth-confirmation').setValue('password-long');await wrapper.get('form').trigger('submit');await flushPromises();await wrapper.get('form').trigger('submit');await flushPromises()
 expect(mocks.authenticate.mock.calls[0][0]).toEqual(mocks.authenticate.mock.calls[1][0]);expect(mocks.authenticate.mock.calls[0][0]).not.toHaveProperty('confirmation');wrapper.unmount()
})
it('login has no confirmation field and retains the real password constraint',async()=>{
 const wrapper=mount(AuthForm,{global});expect(wrapper.find('#auth-confirmation').exists()).toBe(false)
 await wrapper.get('#auth-account').setValue('merchant');await wrapper.get('#auth-password').setValue('12345678');await wrapper.get('form').trigger('submit');expect(mocks.authenticate).not.toHaveBeenCalled();expect(wrapper.text()).toContain('密码需要 10–128');wrapper.unmount()
})
it('profile cancellation retains the server summary and reopening resets the draft',async()=>{
 const wrapper=mount(AccountView,{global});await flushPromises();const button=(text:string)=>wrapper.findAll('button').find(b=>b.text()===text)!
 await button('编辑资料').trigger('click');await wrapper.get('#profile-nickname').setValue('不应保存');await button('关闭测试弹层').trigger('click');expect(mocks.saveProfile).not.toHaveBeenCalled();expect(wrapper.get('[data-testid="profile-nickname"]').text()).toBe('原昵称');await button('编辑资料').trigger('click');expect((wrapper.get('#profile-nickname').element as HTMLInputElement).value).toBe('原昵称');wrapper.unmount()
})
it('account details show the account without displaying the internal user identifier',async()=>{
 const wrapper=mount(AccountView,{global});await flushPromises()
 await wrapper.findAll('button').find(b=>b.text()==='账号详情')!.trigger('click')
 expect(wrapper.text()).toContain('merchant');expect(wrapper.text()).not.toContain('用户编号')
 expect(wrapper.findAll('dd').some(field=>field.text()===identity.profile.value.user_id)).toBe(false)
 wrapper.unmount()
})
it('saves the full profile with trimmed optional contact fields only after explicit save',async()=>{
 const wrapper=mount(AccountView,{global});await flushPromises();await wrapper.findAll('button').find(b=>b.text()==='编辑资料')!.trigger('click')
 await wrapper.get('#profile-shop_name').setValue(' 新店铺 ');await wrapper.get('#profile-category').setValue(' 美妆 ');await wrapper.get('#profile-email').setValue(' merchant@example.com ');await wrapper.get('#profile-phone').setValue(' 13800000000 ')
 expect(mocks.saveProfile).not.toHaveBeenCalled();await wrapper.get('#profile-form').trigger('submit');await flushPromises()
 expect(mocks.saveProfile).toHaveBeenCalledWith({shop_name:'新店铺',category:'美妆',email:'merchant@example.com',phone:'13800000000'});wrapper.unmount()
})
it('preserves unchanged historical long profile values but rejects new oversized or blank nicknames',async()=>{
 identity.profile.value.nickname='  '+'旧'.repeat(60)+' ';identity.profile.value.bio='  '+'旧'.repeat(400)+' '
 const wrapper=mount(AccountView,{global});await flushPromises();const edit=()=>wrapper.findAll('button').find(b=>b.text()==='编辑资料')!.trigger('click');await edit()
 await wrapper.get('#profile-shop_name').setValue('兼容店铺');await wrapper.get('#profile-form').trigger('submit');await flushPromises()
 expect(mocks.saveProfile.mock.calls[0][0]).not.toHaveProperty('nickname');expect(mocks.saveProfile.mock.calls[0][0]).not.toHaveProperty('bio');await edit()
 await wrapper.get('#profile-nickname').setValue('新'.repeat(41));await wrapper.get('#profile-form').trigger('submit');expect(mocks.saveProfile).toHaveBeenCalledTimes(1)
 await wrapper.get('#profile-nickname').setValue(' ');await wrapper.get('#profile-form').trigger('submit');expect(mocks.saveProfile).toHaveBeenCalledTimes(1);wrapper.unmount()
})
it('cancels an uploaded avatar without binding it and ignores an upload that completes after closing',async()=>{
 const uploaded={file_id:'avatar-file',version:'avatar-v1'};mocks.uploadFile.mockResolvedValueOnce(uploaded)
 const wrapper=mount(AccountView,{global});await flushPromises();const button=(text:string)=>wrapper.findAll('button').find(b=>b.text()===text)!;await button('编辑资料').trigger('click')
 const file=new File(['image'],'avatar.png',{type:'image/png'});Object.defineProperty(wrapper.get('#profile-avatar').element,'files',{value:[file],configurable:true});await wrapper.get('#profile-avatar').trigger('change');await flushPromises()
 expect(mocks.saveProfile).not.toHaveBeenCalled();await button('关闭测试弹层').trigger('click');await button('编辑资料').trigger('click');await wrapper.get('#profile-shop_name').setValue('保存店铺');await wrapper.get('#profile-form').trigger('submit');await flushPromises();expect(mocks.saveProfile.mock.calls[0][0]).not.toHaveProperty('avatar')
 let resolveUpload!:(value:typeof uploaded)=>void;mocks.uploadFile.mockReturnValueOnce(new Promise(resolve=>{resolveUpload=resolve}));await button('编辑资料').trigger('click');Object.defineProperty(wrapper.get('#profile-avatar').element,'files',{value:[file],configurable:true});await wrapper.get('#profile-avatar').trigger('change');await button('关闭测试弹层').trigger('click');await button('编辑资料').trigger('click');resolveUpload(uploaded);await flushPromises();await wrapper.get('#profile-form').trigger('submit');await flushPromises();expect(mocks.saveProfile.mock.calls.at(-1)![0]).not.toHaveProperty('avatar');wrapper.unmount()
})
it('binds an uploaded avatar only when saving the current profile draft',async()=>{
 const avatar={file_id:'avatar-file',version:'avatar-v1'};mocks.uploadFile.mockResolvedValue(avatar)
 const wrapper=mount(AccountView,{global});await flushPromises();await wrapper.findAll('button').find(b=>b.text()==='编辑资料')!.trigger('click');Object.defineProperty(wrapper.get('#profile-avatar').element,'files',{value:[new File(['image'],'avatar.png',{type:'image/png'})],configurable:true});await wrapper.get('#profile-avatar').trigger('change');await flushPromises();expect(mocks.saveProfile).not.toHaveBeenCalled();await wrapper.get('#profile-form').trigger('submit');await flushPromises();expect(mocks.saveProfile.mock.calls[0][0]).toHaveProperty('avatar',avatar);wrapper.unmount()
})
it('rejects invalid optional email without discarding profile input',async()=>{
 const wrapper=mount(AccountView,{global});await flushPromises();await wrapper.findAll('button').find(b=>b.text()==='编辑资料')!.trigger('click');await wrapper.get('#profile-email').setValue('invalid-address');await wrapper.get('#profile-form').trigger('submit');await flushPromises();expect(mocks.saveProfile).not.toHaveBeenCalled();expect((wrapper.get('#profile-email').element as HTMLInputElement).value).toBe('invalid-address');wrapper.unmount()
})
it('renders real projected work and conversation names and keeps deletion available for video',async()=>{
 mocks.listWorks.mockResolvedValue({items:[{...work,kind:'video',name:'桌面收纳盒视频',conversation_title:'收纳盒新品'}],next_cursor:null,page:1,page_size:10,total:1})
 const wrapper=mount(WorksView,{global});await flushPromises();expect(wrapper.text()).toContain('桌面收纳盒视频');expect(wrapper.text()).toContain('收纳盒新品');expect(wrapper.findAll('button').some(b=>b.text()==='删除作品')).toBe(true);wrapper.unmount()
})
it('work filters preserve API kinds and source details avoid raw JSON; deletion remains policy-gated',async()=>{
 const wrapper=mount(WorksView,{global});await flushPromises();const button=(text:string)=>wrapper.findAll('button').find(b=>b.text()===text)!
 await button('图片').trigger('click');await flushPromises();expect(mocks.listWorks).toHaveBeenLastCalledWith({kind:'image',q:undefined,page:1,limit:10})
 await button('任务详情').trigger('click');await flushPromises();expect(wrapper.text()).toContain('保温杯');expect(wrapper.text()).toContain('8 积分');expect(wrapper.text()).not.toContain('"product"');expect(wrapper.text()).not.toContain('"credits"')
 await button('关闭测试弹层').trigger('click');await button('删除作品').trigger('click');await flushPromises();expect(button('确认删除').attributes('disabled')).toBeDefined();await button('确认删除').trigger('click');expect(mocks.deleteWork).not.toHaveBeenCalled();wrapper.unmount()
})

it('ledger source navigation reads the owned task before opening its conversation',async()=>{
 const entry={ledger_id:'ledger-1',kind:'freeze',amount:8,created_at:'2026-10-13T00:00:00Z',task_id:'task-1',reason:'任务冻结',balances_before:{available:10,frozen:0,consumed:0},balances_after:{available:2,frozen:8,consumed:0}}
 mocks.listLedger.mockResolvedValue({items:[entry],next_cursor:null,page:1,page_size:20,total:1});mocks.getTask.mockResolvedValue({conversation_id:'conversation-1',input:{instruction:'原始指令'},task:{task_id:'task-1',state:'RUNNING',settlement_state:'FROZEN',quote:{credits:8}}})
 const wrapper=mount(AccountView,{global});await flushPromises();await wrapper.get('[aria-label="查看流水 ledger-1"]').trigger('click');await wrapper.findAll('button').find(b=>b.text()==='查看来源会话')!.trigger('click');await flushPromises();expect(mocks.getTask).toHaveBeenCalledWith('task-1');expect(mocks.push).toHaveBeenCalledWith('/workspace/conversation-1');wrapper.unmount()
})
