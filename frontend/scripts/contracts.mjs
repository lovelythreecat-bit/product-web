import { readFile, writeFile, mkdir } from 'node:fs/promises'
import openapiTS, { astToString } from 'openapi-typescript'

const source = new URL('../../contracts/openapi.json', import.meta.url)
const destination = new URL('../src/types/contracts.ts', import.meta.url)
const schema = JSON.parse(await readFile(source, 'utf8'))
const output = '// Generated from contracts/openapi.json. Do not edit.\n' + astToString(await openapiTS(schema))
if (process.argv.includes('--check')) {
  let actual
  try { actual = await readFile(destination, 'utf8') } catch { actual = null }
  if (actual !== output) {
    console.error('TypeScript contracts are stale; run contracts:generate.')
    process.exitCode = 1
  }
} else {
  await mkdir(new URL('../src/types/', import.meta.url), { recursive: true })
  await writeFile(destination, output, 'utf8')
}
