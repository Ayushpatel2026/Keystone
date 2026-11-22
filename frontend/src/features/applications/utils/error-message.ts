/**
 * A readable message from an API error body.
 *
 * The generated types only describe the 422 body, but the backend's rule
 * violations (full project, wrong state, ...) come back as
 * `{ detail: string }`. This reads that defensively and falls back to a
 * generic message.
 */
export function errorMessage(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'detail' in error) {
    const { detail } = error
    if (typeof detail === 'string') return detail
    // FastAPI validation errors: a list of { msg, loc, ... }.
    if (Array.isArray(detail)) {
      return detail.map((item: { msg?: string }) => item.msg ?? '').join('; ')
    }
  }
  return 'The server rejected this action.'
}
