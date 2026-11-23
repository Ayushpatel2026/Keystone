import { useMutation, useQueryClient } from '@tanstack/react-query'
import { errorMessage } from '@/features/applications/utils/error-message'
import { api } from '@/lib/api-client'

/** Matches the endpoint names: /accept and /decline. */
export type SupervisorDecision = 'accept' | 'decline'

interface DecisionVariables {
  applicationId: string
  decision: SupervisorDecision
}

/**
 * The project's supervisor accepts or declines a team's application. When the
 * backend refuses (project full, already decided, ...) this throws its
 * message, so callers can show it as `mutation.error.message`.
 */
export function useDecideApplication() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ applicationId, decision }: DecisionVariables) => {
      const { response, error } = await api.POST(
        `/api/applications/{application_id}/${decision}`,
        { params: { path: { application_id: applicationId } } },
      )
      if (!response.ok) throw new Error(errorMessage(error))
    },
    // Refresh only on success, like the team actions, so a refused action
    // leaves the stale view in place for the demo. Accepting reserves a slot
    // (and can fill the project), so projects are refreshed too.
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['applications'] }),
        queryClient.invalidateQueries({ queryKey: ['projects'] }),
        queryClient.invalidateQueries({ queryKey: ['project'] }),
      ])
    },
  })
}
