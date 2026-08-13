/// <reference types="vitest/config" />

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    // The first case in a file pays for transforming the whole app graph, and
    // v8 instrumentation makes that slower still; the 5s default was close
    // enough to the real cost that `npm test -- --coverage` failed at random.
    testTimeout: 20000,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/test/**', 'src/**/*.d.ts', 'src/main.tsx', 'src/vite-env.d.ts'],
      // A ratchet, not an aspiration: set just under what the suite covers
      // today, so a change that drops coverage fails here rather than quietly
      // eroding it. Raise these as coverage grows.
      thresholds: {
        statements: 87,
        branches: 75,
        functions: 83,
        lines: 88,
      },
    },
  },
  server: {
    port: 3001,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
