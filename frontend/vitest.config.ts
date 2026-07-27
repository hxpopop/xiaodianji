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
    environment: 'jsdom',
    globals: true,
  },
})
