import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { ApiError } from '../../src/api/client'
const api = vi.hoisted(()=>({getAdminSiteContent:vi.fn(),getAdminCases:vi.fn(),updateSiteContent:vi.fn(),getPublicSite:vi.fn(),getPublicCases:vi.fn(),withdrawCase:vi.fn()}))
const identity=vi.hoisted(()=>({epoch:{value:0},profile:{value:{user_id:'admin'}}}))
vi.mock('../../src/api/site',()=>api)
vi.mock('../../src/features/auth/session',()=>({session:identity}))
import SiteView from '../../src/features/admin/SiteView.vue'
import HomeView from '../../src/features/site/HomeView.vue'
const overlay=defineComponent({props:['open'],emits:['update:open'],template:'<section v-if="open"><slot/><button @click="$emit(\'update:open\',false)">取消</button><slot name="actions"/></section>'})
const global={stubs:{AppDrawer:overlay,AppDialog:overlay,RouterLink:{template:'<a><slot/></a>'}}}
const content={product_intro:'original',agent_descriptions:{text:'text',image:'image',video:'video'},process_steps:['one']}
const row={version:1,content,status:'draft',policy_version:'D11_draft',policy_versions:{},content_ref:'sha256:test'}
beforeEach(()=>{vi.clearAllMocks();identity.epoch.value=0;api.getAdminSiteContent.mockResolvedValue(row);api.getAdminCases.mockResolvedValue([])})
afterEach(()=>{vi.unstubAllEnvs()})
it('cleanup retry keeps the recorded withdrawal version instead of the publication version',async()=>{
 const pending={id:'original-case',work_id:'original-work',owner_id:'original-owner',authorization_ref:'approval',policy_version:'D11_publish_v1',withdrawal_policy_version:'D11_withdraw_v2',state:'cleanup_pending'}
 api.getAdminCases.mockResolvedValue([pending]);api.withdrawCase.mockResolvedValue({...pending,state:'withdrawn'})
 const wrapper=mount(SiteView,{global});await flushPromises()
 const button=(label:string)=>wrapper.findAll('button').find(b=>b.text()===label)!
 await button('重试清理').trigger('click')
 expect((wrapper.get('input').element as HTMLInputElement).value).toBe('D11_withdraw_v2')
 await button('撤回并清理').trigger('click');await flushPromises()
 expect(api.withdrawCase).toHaveBeenCalledExactlyOnceWith('original-case','D11_withdraw_v2')
 wrapper.unmount()
})
it('409 retains edits and reopening loads the current content without version adoption',async()=>{
 api.updateSiteContent.mockRejectedValue(new ApiError('conflict',409))
 const wrapper=mount(SiteView,{global});await flushPromises()
 const button=(label:string)=>wrapper.findAll('button').find(b=>b.text()===label)!
 await button('编辑介绍').trigger('click')
 await flushPromises()
 const form=wrapper.get('#site-editor');await form.findAll('textarea')[0].setValue('my retained draft')
 await form.trigger('submit');await flushPromises()
 expect(form.text()).toContain('草稿已保留')
 expect((form.findAll('textarea')[0].element as HTMLTextAreaElement).value).toBe('my retained draft')
 api.getAdminSiteContent.mockResolvedValue({...row,version:2,content:{...content,product_intro:'another editor'}})
 expect(wrapper.findAll('button').some(b=>/核对最新|采用.*基线/.test(b.text()))).toBe(false)
 await button('取消').trigger('click')
 await button('编辑介绍').trigger('click');await flushPromises()
 const reopened=wrapper.get('#site-editor')
 expect((reopened.findAll('textarea')[0].element as HTMLTextAreaElement).value).toBe('another editor')
 await reopened.findAll('textarea')[0].setValue('revised draft')
 api.updateSiteContent.mockResolvedValue({...row,version:3})
 await reopened.trigger('submit');await flushPromises()
 expect(api.updateSiteContent).toHaveBeenLastCalledWith(expect.objectContaining({expected_version:2,content:{...content,product_intro:'revised draft'}}))
 expect(wrapper.find('#site-editor').exists()).toBe(false)
 wrapper.unmount()
})
it('late content cannot become visible across an identity epoch',async()=>{
 let resolve!:(v:typeof row)=>void
 api.getAdminSiteContent.mockReturnValue(new Promise(r=>{resolve=r}))
 const wrapper=mount(SiteView,{global});identity.epoch.value++;resolve(row);await flushPromises()
 expect(wrapper.text()).not.toContain('original')
 expect(wrapper.findAll('button').find(b=>b.text()==='编辑介绍')!.attributes('disabled')).toBeDefined()
 wrapper.unmount()
})
it('unapproved public content renders empty state and login/register entry points',async()=>{
 api.getPublicSite.mockResolvedValue({content:null});api.getPublicCases.mockResolvedValue([])
 const wrapper=mount(HomeView,{global});await flushPromises()
 expect(wrapper.text()).toContain('产品介绍正在准备中')
 expect(wrapper.text()).toContain('暂无已获公开展示授权的真实案例')
 expect(wrapper.text()).toContain('注册体验');expect(wrapper.text()).toContain('登录')
 expect(wrapper.text()).not.toContain('original');wrapper.unmount()
})
it('production uses the complete layout with approved API copy without exposing design samples',async()=>{
 vi.stubEnv('DEV',false)
 api.getPublicSite.mockResolvedValue({content:{...row,status:'approved'}});api.getPublicCases.mockResolvedValue([])
 const wrapper=mount(HomeView,{global});await flushPromises()
 expect(wrapper.find('.home-hero').exists()).toBe(true)
 expect(wrapper.find('.home-mechanism-diagram').exists()).toBe(true)
 expect(wrapper.find('.home-final-cta').exists()).toBe(true)
 expect(wrapper.text()).toContain('original')
 expect(wrapper.find('.home-process').text()).toContain('one')
 expect(wrapper.text()).not.toContain('亮眼登场')
 expect(wrapper.text()).not.toContain('创作示例')
 expect(wrapper.findAll('img[src*="/homepage/"]')).toHaveLength(0)
 wrapper.unmount()
})
it('local development displays all V3 sections and labels illustrative visuals',async()=>{
 vi.stubEnv('DEV',true);vi.stubEnv('MODE','development')
 api.getPublicSite.mockResolvedValue({content:null});api.getPublicCases.mockResolvedValue([])
 const wrapper=mount(HomeView,{global});await flushPromises()
 expect(wrapper.get('h1').text()).toBe('让好商品，亮眼登场。')
 expect(wrapper.findAll('.home-creation')).toHaveLength(3)
 expect(wrapper.findAll('.home-scenario')).toHaveLength(3)
 expect(wrapper.findAll('.home-process li')).toHaveLength(4)
 expect(wrapper.text()).toContain('商品与创作内容仅作示例展示。')
 expect(wrapper.find('.home-public-cases').exists()).toBe(false)
 expect(wrapper.findAll('video')).toHaveLength(0)
 expect(wrapper.findAll('a[href="#capabilities"]').length).toBeGreaterThan(0)
 wrapper.unmount()
})
it('approved case imagery comes only from the public case response',async()=>{
 vi.stubEnv('DEV',false)
 api.getPublicSite.mockResolvedValue({content:{...row,status:'approved'}})
 api.getPublicCases.mockResolvedValue([{id:'authorized-case',items:[{id:'image',media_type:'image/png',url:'/public/authorized.png'}]}])
 const wrapper=mount(HomeView,{global});await flushPromises()
 expect(wrapper.get('.home-authorized-art').attributes('src')).toBe('/public/authorized.png')
 expect(wrapper.get('.home-public-cases img').attributes('src')).toBe('/public/authorized.png')
 expect(wrapper.findAll('img[src*="/homepage/"]')).toHaveLength(0)
 wrapper.unmount()
})
