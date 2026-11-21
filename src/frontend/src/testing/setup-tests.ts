// Runs before every test file.
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { resetSession } from '@/lib/auth'
import { server } from '@/testing/mocks/server'

// Answer API requests with the fake backend. A request with no handler fails
// the test, so a missing mock is obvious.
beforeAll(() => {
  server.listen({ onUnhandledFrame: 'error' })
})

afterEach(() => {
  // Unmount rendered components between tests so they don't leak into each other.
  cleanup()
  server.resetHandlers()
  resetSession()
  localStorage.clear()
})

afterAll(() => {
  server.close()
})
