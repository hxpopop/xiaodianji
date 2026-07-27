import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    ...devices['Desktop Chrome'],
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:8080',
    channel: 'chrome',
    viewport: { width: 390, height: 844 },
    trace: 'retain-on-failure',
  },
})
