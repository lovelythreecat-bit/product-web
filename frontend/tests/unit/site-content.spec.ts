import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { ApiError } from '../../src/api/client'
const api = vi.hoisted(()=>({getAdminSiteContent:vi.fn(),getAdminCases:vi.fn(),updateSiteContent:vi.fn(),getPublicSite:vi.fn(),getPublicCases:vi.fn()}))
const identity=vi.hoisted(()=>({epoch:{value:0},profile:{value:{user_id:'admin'}}}))
vi.mock('../../src/api/site',()=>api)
vi.mock('../../src/features/auth/session',()=>({session:identity}))
import SiteView from '../../src/features/admin/SiteView.vue'
import HomeView from '../../src/features/site/HomeView.vue'
const overlay=defineComponent({props:['open'],template:'<section v-if="open"><slot/><slot name="actions"/></section>'})
const global={stubs:{AppDrawer:overlay,AppDialog:overlay,RouterLink:{template:'<a><slot/></a>'}}}
const content={product_intro:'original',agent_descriptions:{text:'text',image:'image',video:'video'},process_steps:['one']}
const row={version:1,content,status:'draft',policy_version:'D11_draft',policy_versions:{},content_ref:'sha256:test'}
beforeEach(()=>{vi.clearAllMocks();identity.epoch.value=0;api.getAdminSiteContent.mockResolvedValue(row);api.getAdminCases.mockResolvedValue([])})
it('409 retains all edits and keeps CAS baseline until explicit adoption',async()=>{
 api.updateSiteContent.mockRejectedValue(new ApiError('conflict',409))
 const wrapper=mount(SiteView,{global});await flushPromises()
 const button=(label:string)=>wrapper.findAll('button').find(b=>b.text()===label)!
 await button('编辑介绍').trigger('click')
 const form=wrapper.get('#site-editor');await form.findAll('textarea')[0].setValue('my retained draft')
 await form.trigger('submit');await flushPromises()
 expect(form.text()).toContain('草稿已保留')
 expect((form.findAll('textarea')[0].element as HTMLTextAreaElement).value).toBe('my retained draft')
 api.getAdminSiteContent.mockResolvedValue({...row,version:2,content:{...content,product_intro:'another editor'}})
 await button('核对最新版本（保留输入）').trigger('click');await flushPromises()
 expect(form.text()).toContain('保存基线：版本 1')
 expect((form.findAll('textarea')[0].element as HTMLTextAreaElement).value).toBe('my retained draft')
 await button('已核对，采用版本 2 为基线').trigger('click')
 api.updateSiteContent.mockResolvedValue({...row,version:3})
 await form.trigger('submit');await flushPromises()
 expect(api.updateSiteContent).toHaveBeenLastCalledWith(expect.objectContaining({expected_version:2,content:{...content,product_intro:'my retained draft'}}))
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
