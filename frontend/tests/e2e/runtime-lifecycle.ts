import https from 'node:https'
import type { ChildProcess } from 'node:child_process'

export type OwnedRuntime = {
  child: ChildProcess
  control?: {url:string; token:string}
  vite?: {close:()=>Promise<void>; httpServer?: {listening?:boolean; closeAllConnections?:()=>void}|null}
  graceMs?: number
  requestTimeoutMs?: number
  forceExitMs?: number
}

function within<T>(promise:Promise<T>, deadline:number, message:string):Promise<T> {
  let timer:ReturnType<typeof setTimeout>
  return Promise.race([promise,new Promise<never>((_resolve,reject)=>{
    timer=setTimeout(()=>reject(new Error(message)),Math.max(0,deadline-Date.now()))
  })]).finally(()=>clearTimeout(timer))
}
const hasExited=(child:ChildProcess)=>child.exitCode !== null || child.signalCode !== null

export async function waitForHealth(url:string, deadline:number, requestTimeoutMs=1000) {
  while (Date.now()<deadline) {
    const ready=await new Promise<boolean>(resolve=>{
      const controller=new AbortController()
      const timer=setTimeout(()=>controller.abort(),Math.min(requestTimeoutMs,Math.max(1,deadline-Date.now())))
      const request=https.get(url,{rejectUnauthorized:false,signal:controller.signal},response=>{
        const healthy=response.statusCode===200
        response.destroy()
        resolve(healthy)
      })
      request.once('error',()=>resolve(false))
      request.once('close',()=>clearTimeout(timer))
    })
    if (ready) return
    await new Promise(resolve=>setTimeout(resolve,Math.min(100,Math.max(0,deadline-Date.now()))))
  }
  throw new Error('Real API health check deadline exceeded')
}

export async function stopOwnedRuntime({child,control,vite,graceMs=5000,requestTimeoutMs=1000,forceExitMs=5000}:OwnedRuntime) {
  // Establish both deadlines before any network or Vite await. Only this spawn handle is signalled.
  const graceDeadline=Date.now()+graceMs
  const finalDeadline=graceDeadline+forceExitMs
  let exitListener:()=>void
  const exited=new Promise<void>(resolve=>{
    exitListener=resolve
    if (hasExited(child)) resolve()
    else child.once('exit',exitListener)
  })
  const stopChild=async()=>{
    try {
      if (control && !hasExited(child)) {
        const controller=new AbortController()
        const timer=setTimeout(()=>controller.abort(),Math.min(requestTimeoutMs,Math.max(0,graceDeadline-Date.now())))
        try {
          const response=await fetch(control.url+'/shutdown',{method:'POST',headers:{Authorization:control.token,'Content-Type':'application/json'},body:'{}',signal:controller.signal})
          await response.body?.cancel()
        } catch { /* Forced termination below remains available if control does not respond. */ }
        finally {clearTimeout(timer)}
      }
      if (!hasExited(child)) await within(exited,graceDeadline,'Runtime graceful exit deadline exceeded').catch(()=>{})
    } finally {
      if (!hasExited(child) && child.pid !== undefined) {
        if (!child.kill('SIGKILL') && !hasExited(child)) throw new Error('Unable to terminate owned runtime')
        await within(exited,finalDeadline,'Owned runtime exit not observed after forced termination')
      }
    }
  }
  const stopVite=async()=>{
    if (!vite) return
    const closed=vite.close()
    try {await within(closed,graceDeadline,'Vite close deadline exceeded')}
    catch {
      // Vite owns these sockets; never close another server or a shared API connection.
      vite.httpServer?.closeAllConnections?.()
      await within(closed,finalDeadline,'Vite close not observed')
    }
  }
  try {
    const outcomes=await Promise.allSettled([stopVite(),stopChild()])
    const failures=outcomes.filter((outcome):outcome is PromiseRejectedResult=>outcome.status==='rejected')
    if (failures.length) throw new AggregateError(failures.map(outcome=>outcome.reason),'Owned runtime cleanup failed')
    return {exitObserved:hasExited(child),exitCode:child.exitCode,signal:child.signalCode}
  } finally {child.removeListener('exit',exitListener!)}
}
