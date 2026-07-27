import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          isCustomElement: tag => tag === 'navigator',
        },
      },
    }),
  ],
  test: {
    include: ['tests/**/*.test.ts'],
    environment: 'jsdom',
    globals: true,
  },
})
