import createClient from 'openapi-fetch'
import type { paths } from './schema'

/**
 * A typed client for the Keystone API. Use `api` from ./client instead; this
 * is for the few places that need a client without the auth middleware.
 *
 * Requests go to the page's own origin, and the Vite dev server (or nginx in
 * production) forwards /api and /auth to the backend.
 */
export function createApiClient() {
  return createClient<paths>({
    baseUrl: window.location.origin,
    // Look fetch up on each call, so test mocks (MSW) installed later apply.
    fetch: (request) => globalThis.fetch(request),
  })
}
