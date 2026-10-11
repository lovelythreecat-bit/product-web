import { expect, test } from '@playwright/test'
import { readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { randomUUID } from 'node:crypto'

test('TEST_ONLY real HTTPS registration CSRF admission Worker publication MySQL and disk',async({page,context},info)=>{
 const root=process.env.BROWSER_RUNTIME_DIR!
 const metadata=JSON.parse(await readFile(resolve(root,'metadata.json'),'utf8'))
 const control=JSON.parse(await readFile(resolve(root,'control.json'),'utf8'))
 const command=async(path:string,body:object)=>{
   const response=await fetch(control.url+path,{method:'POST',headers:{Authorization:control.token,'Content-Type':'application/json'},body:JSON.stringify(body)})
   expect(response.status).toBe(200);return response.json()
 }
 const pendingHeaders:Promise<void>[]=[]
 const requests:{url:string;method:string;origin:string|undefined;csrf:boolean;requestedWith:string|undefined}[]=[]
 page.on('request',req=>{if(req.url().includes('/api/v1/')) pendingHeaders.push(req.allHeaders().then(h=>{requests.push({url:req.url(),method:req.method(),origin:h.origin,csrf:!!h['x-csrf-token'],requestedWith:h['x-requested-with']})}))})
 await page.goto('/workspace')
 const result=await page.evaluate(async data=>{
   const authPath='/src/api/auth.ts', accountPath='/src/api/account.ts', convPath='/src/api/conversations.ts', catalogPath='/src/api/catalog.ts', taskPath='/src/api/tasks.ts', clientPath='/src/api/client.ts', filePath='/src/api/files.ts'
   const auth=await import(authPath), account=await import(accountPath), conversations=await import(convPath), catalog=await import(catalogPath), tasks=await import(taskPath), client=await import(clientPath), files=await import(filePath)
   const registered=await auth.register({account:data.account,password:'TEST_ONLY_browser_password',request_key:data.key})
   const me=await auth.getProfile()
   const before=await account.getAccount()
   const denied=await fetch('/api/v1/me',{method:'PATCH',headers:{'Content-Type':'application/json','X-Requested-With':'platform'},body:JSON.stringify({nickname:'must not persist'})})
   const updated=await auth.updateProfile({nickname:'TEST_ONLY browser'})
   const conversation=await conversations.createConversation({title:'TEST_ONLY browser smoke'})
   const product=await conversations.createProductVersion({product:{name:'TEST_ONLY cup'}})
   const png='iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAACXBIWXMAAAABAAAAAQBPJcTWAAAAPElEQVR4nO3RQQ0AMAgEwSOpu2qpPuxVwvLhtyPgSJbqd7PprK7HAwP+AJkImQiZCJkImQiZCJkImSjkA2iaAe2JlpYoAAAAAElFTkSuQmCC'
   const bytes=Uint8Array.from(atob(png),c=>c.charCodeAt(0))
   const file=await files.uploadFile(new File([bytes],'TEST_ONLY.png',{type:'image/png'}))
   const input={product_version:product.version,product:product.product,instruction:'TEST_ONLY complete result',parameters:{},material_versions:[file]}
   const quote=await catalog.quote({spec_id:data.specId,input})
   const body={conversation_id:conversation.conversation_id,agent_id:data.agentId,input,confirmed_quote:quote}
   const intent=client.createIntent(body)
   const first=await tasks.submitTaskIntent(intent)
   const replay=await tasks.submitTaskIntent(intent)
   const frozen=await account.getAccount()
   return {registered,me,before,denied:denied.status,updated,first,replay,frozen,file,body}
 },{account:metadata.account_prefix+info.project.name+'_'+randomUUID().slice(0,8),key:randomUUID(),specId:metadata.specs.copy,agentId:metadata.agents.copy})
 expect(result.me.user_id).toBe(result.registered.profile.user_id)
 expect(result.updated.nickname).toBe('TEST_ONLY browser')
 expect(result.denied).toBe(403)
 expect(result.before).toMatchObject({available:1000,frozen:0,consumed:0})
 expect(result.frozen).toMatchObject({available:992,frozen:8,consumed:0})
 const taskId=result.first.task.task_id
 expect(result.replay.task.task_id).toBe(taskId)
 const cookies=await context.cookies()
 const session=cookies.find(c=>c.name==='session')!
 expect(session).toMatchObject({secure:true,httpOnly:true,sameSite:'Lax'})
 expect(await page.evaluate(()=>document.cookie.includes('session='))).toBe(false)
 await command('/register',{task_id:taskId})
 await expect.poll(async()=>{
  const detail=await page.evaluate(async id=>{const p='/src/api/tasks.ts';return (await import(p)).getTask(id)},taskId)
  return detail.task.state
 },{timeout:45000,intervals:[100,200,500]}).toBe('SUCCEEDED')
 const persisted=await command('/inspect',{task_id:taskId})
 expect(persisted.calls.submit).toBe(1)
 expect(persisted.calls.generation_intents).toBe(1)
 expect(persisted.work_ids).toHaveLength(1)
 expect(persisted.ledger.filter((r:{kind:string})=>r.kind==='freeze')).toHaveLength(1)
 expect(persisted.ledger.filter((r:{kind:string})=>r.kind==='consume')).toHaveLength(1)
 expect(persisted.balances).toEqual({available:992,frozen:0,consumed:8})
 expect(persisted.disk.length).toBe(2)
 expect(persisted.disk.every((f:{matches:boolean})=>f.matches)).toBe(true)
 const delivered=await page.evaluate(async workId=>{
  const wp='/src/api/works.ts',ap='/src/api/account.ts'
  const works=await import(wp),account=await import(ap)
  const work=await works.getWork(workId)
  const download=await fetch(work.items[0].content_url)
  return {work,text:await download.text(),status:download.status,account:await account.getAccount(),ledger:await account.listLedger()}
 },persisted.work_ids[0])
 expect(delivered.work.task_id).toBe(taskId)
 expect(delivered.work.source.input).toEqual(result.body.input)
 expect(delivered.status).toBe(200)
 expect(delivered.text).toContain('TEST_ONLY copy original fixture')
 expect(delivered.work.source.ledger_ids.every((id:string)=>persisted.ledger.some((r:{id:string})=>r.id===id))).toBe(true)
 await Promise.all(pendingHeaders)
 expect(requests.filter(r=>r.method==='POST'||r.method==='PATCH').every(r=>r.origin==='https://127.0.0.1:15173')).toBe(true)
 const outside=await fetch(control.url+'/register',{method:'POST',headers:{Authorization:control.token,'Content-Type':'application/json'},body:JSON.stringify({task_id:randomUUID()})})
 expect(outside.status).toBe(400)
 const evidence={run_id:metadata.run_id,stream:metadata.stream,group:metadata.group,cookie:{secure:session.secure,httpOnly:session.httpOnly,sameSite:session.sameSite},requests,result,persisted,delivered}
 await writeFile(info.outputPath('real-api-evidence.json'),JSON.stringify(evidence,null,2))
 await test.info().attach('real-api-mysql-disk',{body:JSON.stringify(evidence,null,2),contentType:'application/json'})
})
