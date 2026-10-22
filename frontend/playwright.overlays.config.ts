import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests/e2e', testMatch: ['foundation.spec.ts', 'overlay-form.spec.ts'],
  grep: /dialog keyboard|parent form/, workers: 1, timeout: 90000, reporter: 'list',
  webServer: { command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 15174 --strictPort', url: 'http://127.0.0.1:15174', reuseExistingServer: true },
  use: { baseURL: 'http://127.0.0.1:15174', channel: 'msedge', headless: true, reducedMotion: 'reduce' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
})
