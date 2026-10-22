import { defineConfig } from '@playwright/test'
export default defineConfig({testDir:'./tests/e2e',testMatch:['media-integration.spec.ts','agent-configs.spec.ts','image-model-settings.spec.ts'],workers:1,
  timeout:30000,reporter:'list',use:{baseURL:'http://127.0.0.1:15174',channel:'msedge',headless:true},
  projects:[{name:'desktop',use:{viewport:{width:1440,height:1000}}},
    {name:'mobile',use:{viewport:{width:390,height:844},isMobile:true,hasTouch:true}}]})
