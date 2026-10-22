import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
const api=vi.hoisted(()=>({listUsers:vi.fn(),usersSummary:vi.fn(),listAdminLedger:vi.fn(),ledgerSummary:vi.fn(),tasksSummary:vi.fn(),listTasks:vi.fn(),diagnostics:vi.fn(),investigation:vi.fn(),resolveInvestigation:vi.fn(),assignInvestigation:vi.fn(),userAccount:vi.fn(),userLedger:vi.fn(),setUserStatus:vi.fn(),getParameterConfig:vi.fn(),listAgents:vi.fn(),listSpecs:vi.fn(),listPrices:vi.fn(),listTextModels:vi.fn(),getTextDefaultModel:vi.fn(),statistics:vi.fn(),listAudit:vi.fn(),auditSummary:vi.fn()}))
vi.mock('../../src/api/admin',()=>api)
vi.mock('vue-router',()=>({useRoute:()=>({query:{}})}))
vi.mock('../../src/features/auth/session',()=>({session:{epoch:{value:0},profile:{value:{user_id:'admin'}}},onIdentityChange:()=>()=>{}}))
vi.mock('../../src/features/admin/creditIntent',()=>({restoreGrant:()=>null,rememberGrant:vi.fn(),forgetGrant:vi.fn()}))

import ParametersView from '../../src/features/admin/ParametersView.vue'
import AgentsView from '../../src/features/admin/AgentsView.vue'

import AuditView from '../../src/features/admin/AuditView.vue'

import TasksView from '../../src/features/admin/TasksView.vue'
const overlay=defineComponent({props:['open'],template:'<section v-if="open"><slot/><slot name="actions"/></section>'})
const global={stubs:{AppDrawer:overlay,AppDialog:overlay,ContentAccessPanel:true,TextServiceConnection:true,RouterLink:{template:'<a><slot/></a>'}}}
beforeEach(()=>{vi.clearAllMocks();api.getTextDefaultModel.mockResolvedValue({model_config_id:null,revision:0,connection_revision:0});api.listTextModels.mockResolvedValue({items:[],next_cursor:null});api.listUsers.mockResolvedValue({items:[{id:'u1',account_normalized:'商家账号',nickname:'店主',role:'user',status:'active',created_at:'2026-10-13T00:00:00Z',auth_version:0,shop_name:'真实店铺',category:'家居',email:null,phone:null,last_login_at:null,task_count:7,available:17,frozen:3,consumed:8}],next_cursor:null});api.listAgents.mockResolvedValue([{agent_id:'a1',version:'v1',name:'图片创作',kind:'image',mode:'mock',test_only:true,enabled:false,secret_configured:false}]);api.listSpecs.mockResolvedValue([{spec_id:'s1',agent_id:'a1',agent_version:'v1',version:'s-v1',name:'单张商品图',delivery_kind:'single',enabled:false,parameter_schema:{fields:{ratio:{default:'1:1'}},combinations:[]}}]);api.listPrices.mockResolvedValue([{spec_id:'s1',credits:8,version:'p-v1',enabled:false}])})
beforeEach(()=>{api.usersSummary.mockResolvedValue({total:987,active:980,disabled:7,admin_count:2,available:700,frozen:8,consumed:90,credited_total:798});api.listAdminLedger.mockResolvedValue({items:[{ledger_id:'ledger-1',user_id:'u1',account:'商家账号',operator:null,kind:'admin_grant',amount:17,task_id:null,reason:'试用',created_at:'2026-10-13T00:00:00Z',balances_before:{available:0,frozen:0,consumed:0},balances_after:{available:17,frozen:0,consumed:0}}],next_cursor:null});api.ledgerSummary.mockResolvedValue({available:700,frozen:8,consumed:90,credited_total:798,ledger_count:4321});api.auditSummary.mockResolvedValue({total:2468,action_counts:{admin_credit_grant:11}});api.tasksSummary.mockResolvedValue({total:876,investigating:3,save_recovery:2,frozen_credits:8});api.listTasks.mockResolvedValue({items:[],next_cursor:null,page:1,page_size:20,total:0})})
it('parameters replace specifications while agent route retains model configuration',async()=>{
 api.getParameterConfig.mockResolvedValue({version:null,text_price:null,image_price:null,video_price:null})
 const specs=mount(ParametersView,{global});await flushPromises()
 expect(specs.find('h1').exists()).toBe(false);expect(specs.text()).toContain('编辑参数');expect(specs.text()).not.toContain('编辑规格')
 specs.unmount()
 const agents=mount(AgentsView,{global:{...global,stubs:{...global.stubs,MediaAgentConfigs:{props:['kind'],template:'<section><h2>{{kind === "image" ? "图片" : "视频"}}服务配置</h2></section>'}}}});await flushPromises()
 expect(agents.text()).not.toContain('文本服务接入');expect(agents.text()).not.toContain('新增文本 Agent');expect(agents.find('#admin-agent').exists()).toBe(false);expect(agents.find('h1').exists()).toBe(false);expect(agents.text()).toContain('文本模型配置');expect(agents.text()).not.toContain('参数规格与当前价格')
 for(const label of ['图片','视频']) {
  await agents.findAll('button').find(b=>b.text()===label)!.trigger('click')
  expect(agents.text()).toContain(label+'服务配置')
  expect(agents.text()).not.toContain('配置模型');expect(agents.text()).not.toContain('新增文本 Agent');expect(agents.text()).not.toContain('图片创作')
 }
 agents.unmount()
})
it('audit filter displays Chinese but sends exact server action and preserves structured changes',async()=>{
 api.listAudit.mockResolvedValue({items:[{id:'l1',action:'admin_credit_grant',actor_id:'admin',object_id:'g1',reason:'试用',created_at:'2026-10-13T00:00:00Z',changes:{amount:17,user_id:'u1'}}],next_cursor:null,page:1,page_size:20,total:1})
 const wrapper=mount(AuditView,{global});await flushPromises();await wrapper.get('select').setValue('admin_credit_grant');await wrapper.get('form').trigger('submit');await flushPromises()
 expect(api.listAudit).toHaveBeenLastCalledWith(undefined,'admin_credit_grant',undefined,undefined,undefined,1)
 await wrapper.findAll('button').find(b=>b.text()==='查看详情')!.trigger('click')
 expect(wrapper.text()).toContain('积分数量');expect(wrapper.text()).toContain('17');expect(wrapper.find('pre').exists()).toBe(false);wrapper.unmount()
})
it('tasks search keeps keyword and actual agent id without a summary panel',async()=>{
 const wrapper=mount(TasksView,{global});await flushPromises();expect(wrapper.text()).not.toContain('平台任务汇总');await wrapper.get('#admin-task-keyword').setValue('商家账号');await wrapper.get('select[data-select-id="admin-task-agent"]').setValue('a1');await wrapper.get('.admin-filters').trigger('submit');await flushPromises();expect(api.listTasks).toHaveBeenLastCalledWith(undefined,undefined,undefined,'商家账号','a1',1);wrapper.unmount()
})
it('opens compatible task diagnostics that omit optional works and timeline without inventing records',async()=>{
 const diagnostic={id:'task-1',user_id:'u1',state:'RUNNING',settlement_state:'FROZEN',state_version:1,agent_id:'a1',agent_version:'v1',elapsed_seconds:3,diagnostic_code:null,investigation_status:null,investigation_owner:null,investigation_deadline:null,created_at:'2026-10-13T00:00:00Z'}
 api.listTasks.mockResolvedValue({items:[diagnostic],next_cursor:null,page:1,page_size:20,total:1});api.diagnostics.mockResolvedValue(diagnostic)
 const wrapper=mount(TasksView,{global});await flushPromises();await wrapper.findAll('button').find(b=>b.text()==='查看诊断')!.trigger('click');await flushPromises();expect(wrapper.text()).toContain('关联成果未提供');expect(wrapper.text()).toContain('尚未提供状态记录');wrapper.unmount()
})

it('keeps diagnosis read-only with no footer actions or investigation forms',async()=>{
 const task={id:'task1',user_id:'u1',agent_id:'a1',agent_version:'v1',state:'INVESTIGATING',state_version:1,settlement_state:'FROZEN',elapsed_seconds:0,created_at:'2026-10-15T00:00:00Z',work_ids:[]}
 api.listTasks.mockResolvedValue({items:[task],next_cursor:null,page:1,page_size:20,total:1});api.diagnostics.mockResolvedValue(task)
 const wrapper=mount(TasksView,{global});await flushPromises()
 await wrapper.findAll('button').find(b=>b.text()==='查看诊断')!.trigger('click');await flushPromises()
 expect(wrapper.text()).toContain('任务时间线')
 expect(wrapper.text()).not.toMatch(/刷新诊断|登记核查|调整负责人|处置原任务/)
 expect(wrapper.find('#task-action').exists()).toBe(false)
 expect(api.investigation).not.toHaveBeenCalled()
 wrapper.unmount()
})
