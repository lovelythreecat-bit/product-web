// @vitest-environment node
import { afterAll, expect, test } from 'vitest'
import { createServer as createNetServer, connect } from 'node:net'
import type { Socket, AddressInfo } from 'node:net'
import { createServer as createHttpServer } from 'node:http'
import { spawn } from 'node:child_process'
import type { ChildProcess } from 'node:child_process'
import { once } from 'node:events'
import { writeFileSync } from 'node:fs'
import { createServer as createViteServer } from 'vite'
import { stopOwnedRuntime, waitForHealth } from '../e2e/runtime-lifecycle'

const facts:unknown[]=[]
function record(value:string) {facts.push(JSON.parse(value))}
afterAll(()=>{if(process.env.TEST_LIFECYCLE_EVIDENCE)writeFileSync(process.env.TEST_LIFECYCLE_EVIDENCE,JSON.stringify(facts,null,2))})

async function ownChild() {
  const child = spawn(process.execPath, ['-e', "process.on('message',m=>{if(m==='stop')process.exit(0)});setInterval(()=>{},1000);console.log('ready')"], {windowsHide:true,stdio:['ignore','pipe','pipe','ipc']})
  await once(child.stdout!, 'data')
  return child
}
async function reap(child:ChildProcess) {
  if (child.exitCode !== null || child.signalCode !== null) return
  const exited=once(child,'exit');child.kill('SIGKILL');await exited
}
async function listen(server:ReturnType<typeof createNetServer>) {
  const sockets=new Set<Socket>()
  server.on('connection',socket=>{sockets.add(socket);socket.once('close',()=>sockets.delete(socket))})
  server.listen(0,'127.0.0.1');await once(server,'listening')
  return {port:(server.address() as AddressInfo).port,sockets,async close(){for(const socket of sockets)socket.destroy();await new Promise<void>((resolve,reject)=>server.close(error=>error?reject(error):resolve()))}}
}

test('health deadline aborts a connection stalled before TLS response', async()=>{
  const server=createNetServer()
  const owned=await listen(server)
  let accepted=0;server.on('connection',()=>accepted++)
  const watchdog=setTimeout(()=>{for(const socket of owned.sockets)socket.destroy()},700)
  const started=Date.now()
  try {
    await expect(waitForHealth(`https://127.0.0.1:${owned.port}/health`,Date.now()+120,40)).rejects.toThrow(/health/i)
    const elapsed=Date.now()-started
    record(JSON.stringify({case:'stalled-health',elapsed,accepted}))
    expect(accepted).toBeGreaterThan(0)
    expect(elapsed).toBeLessThan(450)
  } finally {clearTimeout(watchdog);await owned.close()}
})

test('stalled shutdown control cannot postpone the exit deadline', async()=>{
  let requests=0
  const server=createHttpServer((_req,_res)=>{requests++})
  const owned=await listen(server)
  const child=await ownChild()
  let observed=false;child.once('exit',()=>{observed=true})
  const watchdog=setTimeout(()=>{for(const socket of owned.sockets)socket.destroy()},700)
  const started=Date.now()
  try {
    const result=await stopOwnedRuntime({child,control:{url:`http://127.0.0.1:${owned.port}`,token:'TEST_ONLY'},graceMs:120,requestTimeoutMs:40,forceExitMs:1000})
    const elapsed=Date.now()-started
    record(JSON.stringify({case:'stalled-control',pid:child.pid,requests,elapsed,observed,...result}))
    expect(requests).toBe(1)
    expect(elapsed).toBeLessThan(450)
    expect(observed).toBe(true)
    expect(result.exitObserved).toBe(true)
  } finally {clearTimeout(watchdog);await reap(child);await owned.close()}
})

test('force termination returns only after actual child exit',async()=>{
  const child=await ownChild()
  let observed=false;child.once('exit',()=>{observed=true})
  try {
    const result=await stopOwnedRuntime({child,graceMs:30,forceExitMs:1000})
    record(JSON.stringify({case:'forced-exit',pid:child.pid,observed,...result}))
    expect(observed).toBe(true)
    expect(result.exitObserved).toBe(true)
    expect(child.exitCode !== null || child.signalCode !== null).toBe(true)
  } finally {await reap(child)}
})

test('Vite close error still reaps its own child before rejecting',async()=>{
  const child=await ownChild()
  const vite=await createViteServer({configFile:false,server:{host:'127.0.0.1',port:0},logLevel:'silent'})
  await vite.listen()
  let observed=false;child.once('exit',()=>{observed=true})
  try {
    await expect(stopOwnedRuntime({child,vite:{httpServer:vite.httpServer,close:async()=>{await vite.close();throw new Error('TEST_ONLY close failure')}},graceMs:50,forceExitMs:1000})).rejects.toThrow()
    record(JSON.stringify({case:'vite-close-error',pid:child.pid,observed,viteListening:vite.httpServer?.listening}))
    expect(vite.httpServer?.listening).toBe(false)
    expect(observed).toBe(true)
  } finally {await vite.close();await reap(child)}
})

test('cooperative control exits normally without forced termination',async()=>{
  const child=await ownChild()
  const server=createHttpServer((_req,res)=>{child.send!('stop');res.end('{}')})
  const owned=await listen(server)
  try {
    const result=await stopOwnedRuntime({child,control:{url:`http://127.0.0.1:${owned.port}`,token:'TEST_ONLY'},graceMs:1000,requestTimeoutMs:200,forceExitMs:1000})
    record(JSON.stringify({case:'cooperative-exit',pid:child.pid,...result}))
    expect(result).toMatchObject({exitObserved:true,exitCode:0,signal:null})
  } finally {await reap(child);await owned.close()}
})

test('occupied owned server is force-closed and awaited within the final deadline',async()=>{
  const server=createNetServer()
  const owned=await listen(server)
  const socket=connect(owned.port,'127.0.0.1')
  await once(socket,'connect')
  const child=await ownChild()
  let closed=false
  try {
    const result=await stopOwnedRuntime({child,vite:{close:()=>new Promise<void>((resolve,reject)=>server.close(error=>{closed=true;error?reject(error):resolve()})),httpServer:{closeAllConnections:()=>{for(const peer of owned.sockets)peer.destroy()}}},graceMs:40,forceExitMs:1000})
    record(JSON.stringify({case:'forced-server-close',pid:child.pid,closed,listening:server.listening,...result}))
    expect(closed).toBe(true)
    expect(server.listening).toBe(false)
    expect(result.exitObserved).toBe(true)
  } finally {socket.destroy();for(const peer of owned.sockets)peer.destroy();if(server.listening)await owned.close();await reap(child)}
})
