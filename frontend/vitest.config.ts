import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'
export default defineConfig({plugins:[vue()],test:{environment:'jsdom',setupFiles:['tests/unit/setup-ui.ts'],testTimeout:15000,maxWorkers:4,include:['tests/unit/**/*.test.ts','tests/unit/**/*.spec.ts']}})
