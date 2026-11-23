import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { apiErrorMessage } from '@/lib/api-error'

export type ReviewDecision = 'approve' | 'reject'

interface ReviewVariables {
  applicationId: string
  decision: ReviewDecision
}

/**
 * Approve or reject a team project that is under review. A rejection by the
 * backend (wrong course, already decided, ...) throws an Error carrying the
 * backend's own message, so the page can show it as is.
 */
export function useReviewApplication() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ applicationId, decision }: ReviewVariables) => {
      const options = { params: { path: { application_id: applicationId } } }
      const { data, error } =
        decision === 'approve'
          ? await api.POST(
              '/api/applications/{application_id}/approve',
              options,
            )
          : await api.POST('/api/applications/{application_id}/reject', options)
      if (error !== undefined || !data) {
        throw new Error(
          apiErrorMessage(
            error,
            `Could not ${decision} this submission. Please try again.`,
          ),
          { cause: error },
        )
      }
      return data
    },
    // Refresh either way: after a 409 the list is stale and should catch up.
    // Rejecting releases the project's slot, so project availability changes too.
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['applications'] }),
        queryClient.invalidateQueries({ queryKey: ['projects'] }),
      ]),
  })
}
