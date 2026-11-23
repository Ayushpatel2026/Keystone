import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { apiErrorMessage } from '@/lib/api-error'

export type SupervisorDecision = 'accept' | 'decline'

interface DecisionVariables {
  applicationId: string
  decision: SupervisorDecision
}

/**
 * The project's supervisor accepts or declines a team's application. A
 * refusal by the backend (project full, already decided, ...) throws an
 * Error carrying the backend's own message.
 */
export function useDecideApplication() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ applicationId, decision }: DecisionVariables) => {
      const options = { params: { path: { application_id: applicationId } } }
      const { data, error } =
        decision === 'accept'
          ? await api.POST('/api/applications/{application_id}/accept', options)
          : await api.POST(
              '/api/applications/{application_id}/decline',
              options,
            )
      if (error !== undefined || !data) {
        throw new Error(
          apiErrorMessage(
            error,
            `Could not ${decision} this application. Please try again.`,
          ),
          { cause: error },
        )
      }
      return data
    },
    // Refresh either way: after a 409 the list is stale. Accepting reserves a
    // slot (and can fill the project), so project availability changes too.
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['applications'] }),
        queryClient.invalidateQueries({ queryKey: ['projects'] }),
        queryClient.invalidateQueries({ queryKey: ['project'] }),
      ]),
  })
}
