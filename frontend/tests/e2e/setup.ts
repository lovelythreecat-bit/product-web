import { spawn } from 'node:child_process'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { createServer } from 'vite'
import { stopOwnedRuntime, waitForHealth } from './runtime-lifecycle'
import type { FullConfig } from '@playwright/test'

export default async function setup(_config: FullConfig) {
  if (process.env.APP_MODE !== 'mock' || process.env.APP_TEST_ONLY !== 'true') throw new Error('Browser tests require explicit APP_MODE=mock APP_TEST_ONLY=true')
  const root = process.env.BROWSER_RUNTIME_DIR!
  await mkdir(root,{recursive:true})
  const env: NodeJS.ProcessEnv = {...process.env, PYTHONUTF8:'1', PYTHONDONTWRITEBYTECODE:'1'}; delete env.NO_COLOR
  const child = spawn(resolve('../backend/.venv/Scripts/python.exe'), ['-m','tests.browser_support.runtime','--root',root], {cwd:resolve('../backend'),env,windowsHide:true,stdio:['ignore','pipe','pipe']})
  let output = ''
  let spawnError:Error|undefined
  child.on('error',error=>{spawnError=error;output+='\n'+error.message})
  child.stdout.on('data', data => {output += data.toString()})
  child.stderr.on('data', data => {output += data.toString()})
  let vite: Awaited<ReturnType<typeof createServer>> | undefined
  let control: {url:string;token:string} | undefined
  let shutdownPromise:Promise<void>|undefined
  const shutdown = () => shutdownPromise ??= (async () => {
    let cleanupError:unknown
    try {await stopOwnedRuntime({child,control,vite})}
    catch(error) {cleanupError=error}
    finally {
      const exitObserved=child.exitCode !== null || child.signalCode !== null
      await writeFile(resolve(root,'processes.json'),JSON.stringify({pid:child.pid,exitCode:child.exitCode,signal:child.signalCode,exitObserved,cleanupError:cleanupError instanceof Error ? cleanupError.message : null,closedAt:new Date().toISOString()},null,2))
      await writeFile(resolve(root,'runtime.log'),output)
    }
    if (cleanupError) throw cleanupError
  })()
  try {
    const deadline = Date.now()+45000
    while (true) {
      if (spawnError || child.exitCode !== null || child.signalCode !== null) throw new Error('TEST_ONLY runtime startup failed: '+output)
      try {control = JSON.parse(await readFile(resolve(root,'control.json'),'utf8')); break} catch {}
      if (Date.now()>deadline) throw new Error('TEST_ONLY runtime readiness timeout: '+output)
      await new Promise(r=>setTimeout(r,100))
    }
    process.env.TEST_HTTPS_CERT=resolve(root,'cert.pem')
    process.env.TEST_HTTPS_KEY=resolve(root,'key.pem')
    process.env.API_PROXY_TARGET='http://127.0.0.1:18018'
    vite = await createServer({configFile:resolve('vite.config.ts')})
    await vite.listen()
    await waitForHealth('https://127.0.0.1:15173/api/v1/health/ready',deadline)
    await writeFile(resolve(root,'startup.json'),JSON.stringify({pid:child.pid,healthyAt:new Date().toISOString(),origin:'https://127.0.0.1:15173'},null,2))
    return shutdown
  } catch(error) {
    try {await shutdown()} catch(cleanupError) {throw new AggregateError([error,cleanupError],'Runtime startup and cleanup failed')}
    throw error
  }
}
