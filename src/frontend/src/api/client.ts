import { authMiddleware } from '../auth/session'
import { createApiClient } from './createApiClient'

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
 * Requests carry the token of the user picked in the switcher (see
 * src/auth/session.ts).
 */
export const api = createApiClient()

api.use(authMiddleware)
