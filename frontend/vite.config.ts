import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { readFileSync } from 'node:fs'
const httpsRequested = !!process.env.TEST_HTTPS_CERT || !!process.env.TEST_HTTPS_KEY
if (httpsRequested && (process.env.APP_MODE !== 'mock' || process.env.APP_TEST_ONLY !== 'true')) throw new Error('Local test certificate is TEST_ONLY')
// Current public assets are unpublished homepage design examples, available only in dev.
// Approved production visuals are served by the permission-controlled site API.
export default defineConfig({plugins:[vue()],build:{copyPublicDir:false,rollupOptions:{output:{manualChunks(id){
 if(id.includes('/element-plus/es/components/table/')) return 'element-table'
 if(id.includes('/vue/') || id.includes('/@vue/') || id.includes('/vue-router/')) return 'vue'
}}}},server:{host:'127.0.0.1',port:15173,strictPort:true,
 https:httpsRequested ? {cert:readFileSync(process.env.TEST_HTTPS_CERT!),key:readFileSync(process.env.TEST_HTTPS_KEY!)} : undefined,
 proxy:{'/api':{target:process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:18000',changeOrigin:false,xfwd:httpsRequested}}
}})
