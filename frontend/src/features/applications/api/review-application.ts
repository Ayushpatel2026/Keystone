import { useMutation, useQueryClient } from '@tanstack/react-query'
import { errorMessage } from '@/features/applications/utils/error-message'
import { api } from '@/lib/api-client'

/** Matches the endpoint names: /approve and /reject. */
export type ReviewDecision = 'approve' | 'reject'

interface ReviewVariables {
  applicationId: string
  decision: ReviewDecision
}

/**
 * An instructor or TA approves or rejects a team project under review. When
 * the backend refuses (wrong course, already decided, ...) this throws its
 * message, so callers can show it as `mutation.error.message`.
 */
export function useReviewApplication() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ applicationId, decision }: ReviewVariables) => {
      const { response, error } = await api.POST(
        `/api/applications/{application_id}/${decision}`,
        { params: { path: { application_id: applicationId } } },
      )
      if (!response.ok) throw new Error(errorMessage(error))
    },
    // Refresh only on success, like the team actions, so a refused action
    // leaves the stale view in place for the demo. Rejecting releases the
    // project's slot, so projects are refreshed too.
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['applications'] }),
        queryClient.invalidateQueries({ queryKey: ['projects'] }),
      ])
    },
  })
}
