import createClient from 'openapi-fetch'
import type { paths } from '@/types/api'

/**
 * Typed client for the Keystone API.
 *
 * Paths, parameters and response bodies are all checked against the backend's
 * OpenAPI schema. Run `npm run gen:api` after changing backend endpoints.
 *
 * Example:
 *   const { data, error } = await api.GET('/api/projects/{project_id}', {
 *     params: { path: { project_id: id } },
 *   })
 *
 * Requests go to the page's own origin, and the Vite dev server (or nginx in
 * production) forwards /api and /auth to the backend. They carry the token of
 * the user picked in the switcher: `@/lib/auth` adds that to this client.
 */
export const api = createClient<paths>({
  baseUrl: window.location.origin,
  // Look fetch up on each call, so test mocks (MSW) installed later apply.
  fetch: (request) => globalThis.fetch(request),
})
