/**
 * The message to show for a failed API request.
 *
 * FastAPI puts it in `detail`: a string for errors the endpoint raises
 * (403, 404, 409 ...), or a list of `{ msg }` for request validation (422).
 * Anything else, or no body at all, falls back to `fallback`.
 */
export function apiErrorMessage(error: unknown, fallback: string): string {
  if (typeof error !== 'object' || error === null || !('detail' in error)) {
    return fallback
  }
  const { detail } = error
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item: unknown) =>
        typeof item === 'object' && item !== null && 'msg' in item
          ? String(item.msg)
          : null,
      )
      .filter((msg): msg is string => Boolean(msg))
    if (messages.length > 0) return messages.join(' ')
  }
  return fallback
}
