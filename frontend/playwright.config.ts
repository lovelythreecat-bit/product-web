import { defineConfig } from '@playwright/test'
import { resolve } from 'node:path'
import { randomUUID } from 'node:crypto'
process.env.BROWSER_RUNTIME_DIR ??= resolve('.cache/browser/TEST_ONLY-'+randomUUID())
export default defineConfig({
 testDir:'./tests/e2e', fullyParallel:false, workers:1, forbidOnly:!!process.env.CI,
 retries:0, reporter:'list', timeout:60000, globalSetup:'./tests/e2e/setup.ts',
 use:{baseURL:'https://127.0.0.1:15173',ignoreHTTPSErrors:true,trace:'retain-on-failure',channel:process.env.PLAYWRIGHT_CHANNEL},
 projects:[{name:'desktop',use:{viewport:{width:1440,height:1000}}},{name:'mobile',use:{viewport:{width:390,height:844},isMobile:true,hasTouch:true}}]
})
