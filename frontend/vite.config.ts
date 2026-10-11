import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { readFileSync } from 'node:fs'
const httpsRequested = !!process.env.TEST_HTTPS_CERT || !!process.env.TEST_HTTPS_KEY
if (httpsRequested && (process.env.APP_MODE !== 'mock' || process.env.APP_TEST_ONLY !== 'true')) throw new Error('Local test certificate is TEST_ONLY')
export default defineConfig({plugins:[vue()],server:{host:'127.0.0.1',port:15173,strictPort:true,
 https:httpsRequested ? {cert:readFileSync(process.env.TEST_HTTPS_CERT!),key:readFileSync(process.env.TEST_HTTPS_KEY!)} : undefined,
 proxy:{'/api':{target:process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:18000',changeOrigin:false}}
}})
