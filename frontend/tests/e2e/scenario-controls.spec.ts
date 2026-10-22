import { expect, test } from '@playwright/test'
import { readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { randomUUID } from 'node:crypto'

test('TEST_ONLY scoped controls recover originals and never turn uncertainty into release',async({page},info)=>{
 const root=process.env.BROWSER_RUNTIME_DIR!
 const meta=JSON.parse(await readFile(resolve(root,'metadata.json'),'utf8'))
 const control=JSON.parse(await readFile(resolve(root,'control.json'),'utf8'))
 const command=async(path:string,body:object)=>{const r=await fetch(control.url+path,{method:'POST',headers:{Authorization:control.token,'Content-Type':'application/json'},body:JSON.stringify(body)});expect(r.status,await r.clone().text()).toBe(200);return r.json()}
 await page.goto('/workspace')
 const ids:string[]=await page.evaluate(async meta=>{
  const a='/src/api/auth.ts',c='/src/api/conversations.ts',t='/src/api/tasks.ts',q='/src/api/catalog.ts'
  const auth=await import(a),conv=await import(c),tasks=await import(t),catalog=await import(q)
  await auth.register({account:meta.account_prefix+'sc_'+crypto.randomUUID().slice(0,8),password:'TEST_ONLY_browser_password',request_key:crypto.randomUUID()})
  const conversation=await conv.createConversation({title:'TEST_ONLY scoped scenarios'})
  const product=await conv.createProductVersion({product:{name:'TEST_ONLY cup'}})
  const input={product_version:product.version,product:product.product,instruction:'TEST_ONLY',parameters:{},material_versions:[]}
  const confirmed_quote=await catalog.quote({agent_id:meta.agents.copy,input})
  const ids=[]
  for(let i=0;i<5;i++) ids.push((await tasks.submitTask(crypto.randomUUID(),{conversation_id:conversation.conversation_id,agent_id:meta.agents.copy,input,confirmed_quote})).task.task_id)
  return ids
 },meta)
 const history:unknown[]=[]
 const run=async(index:number,scenario:string)=>{await command('/register',{task_id:ids[index],scenario,paused:true});const r=await command('/drive',{task_id:ids[index]});history.push(r);return r}
 const frozen=(r:any)=>{expect(r.work_ids).toHaveLength(0);expect(r.ledger.filter((x:any)=>x.task_id===r.task_id&&['consume','release'].includes(x.kind))).toHaveLength(0);expect(r.calls.submit).toBe(1)}
 let unknown=await run(0,'lost_response');frozen(unknown)
 await command('/scenario',{task_id:ids[0],scenario:'not_found'})
 unknown=await command('/drive',{task_id:ids[0]});history.push(unknown);frozen(unknown)
 await command('/scenario',{task_id:ids[0],scenario:'normal'})
 for(let i=0;i<3&&unknown.state!=='SUCCEEDED';i++) unknown=await command('/drive',{task_id:ids[0]})
 expect(unknown.state).toBe('SUCCEEDED');expect(unknown.calls.submit).toBe(1);history.push(unknown)
 let absent=await run(1,'not_found');absent=await command('/drive',{task_id:ids[1]});frozen(absent);history.push(absent)
 let saved=await run(2,'save_failure');saved=await command('/drive',{task_id:ids[2]});frozen(saved);expect(saved.state).toBe('SAVE_RECOVERY');history.push(saved)
 await command('/scenario',{task_id:ids[2],scenario:'normal'})
 saved=await command('/drive',{task_id:ids[2]});expect(saved.state).toBe('SUCCEEDED');expect(saved.calls.submit).toBe(1);history.push(saved)
 let failed=await run(3,'normal')
 const notification=await command('/notify',{task_id:ids[3],failure:true})
 expect(notification.receipts).toEqual(['ACCEPTED','DUPLICATE'])
 failed=await command('/drive',{task_id:ids[3]});expect(failed.state).toBe('FAILED');expect(failed.work_ids).toHaveLength(0)
 expect(failed.ledger.filter((r:any)=>r.task_id===ids[3]&&r.kind==='release')).toHaveLength(1);history.push(failed)
 let partial=await run(4,'partial');partial=await command('/drive',{task_id:ids[4]});frozen(partial);history.push(partial)
 const duplicate=await command('/notify',{task_id:ids[2],failure:false});expect(duplicate.receipts[1]).toBe('DUPLICATE')
 const final=await command('/inspect',{task_id:ids[2]});expect(final.calls.submit).toBe(1);expect(final.ledger.filter((r:any)=>r.task_id===ids[2]&&r.kind==='consume')).toHaveLength(1)
 await writeFile(info.outputPath('scenarios.json'),JSON.stringify({run_id:meta.run_id,ids,history,notification,duplicate,final},null,2))
})
