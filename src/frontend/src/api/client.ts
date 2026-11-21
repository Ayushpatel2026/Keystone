import createClient from 'openapi-fetch'
import type { paths } from './schema'

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
 * No baseUrl: requests go to the same origin, and the Vite dev server (or
 * nginx in production) forwards /api and /auth to the backend.
 */
export const api = createClient<paths>()
