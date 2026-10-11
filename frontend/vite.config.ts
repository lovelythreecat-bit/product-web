import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 15173,
    strictPort: true,
    proxy: { '/api': process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:18000' },
  },
})
