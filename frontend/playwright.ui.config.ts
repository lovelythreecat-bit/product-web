import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests/e2e',
  testMatch: ['workspace-updates.spec.ts', 'workspace-recovery.spec.ts', 'agent-configs.spec.ts', 'video-agent-configs.spec.ts', 'media-integration.spec.ts', 'element-controls.spec.ts', 'user-surface-updates.spec.ts'],
  workers: 1, timeout: 45000, reporter: 'list',
  webServer: { command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 15174 --strictPort', url: 'http://127.0.0.1:15174', reuseExistingServer: true },
  use: { baseURL: 'http://127.0.0.1:15174', channel: 'msedge', headless: true },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
})
