/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

// Where the FastAPI dev server runs. Override with KEYSTONE_API_URL if needed.
const apiTarget = process.env.KEYSTONE_API_URL ?? 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    // Imports: "@/lib/auth" is "src/lib/auth". Matches tsconfig.app.json.
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    // Forward API calls to the backend so the browser sees one origin (no CORS).
    proxy: {
      '/api': apiTarget,
      '/auth': apiTarget,
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/testing/setup-tests.ts'],
    coverage: {
      provider: 'v8',
      // lcov is the report SonarQube imports.
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/main.tsx',
        'src/testing/**',
        'src/types/**',
        'src/**/*.test.{ts,tsx}',
      ],
    },
  },
})
