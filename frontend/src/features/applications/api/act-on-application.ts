import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { TeamActionName } from '@/features/applications/types/application'
import { errorMessage } from '@/features/applications/utils/error-message'
import { api } from '@/lib/api-client'

interface ActOnApplicationInput {
  applicationId: string
  action: TeamActionName
}

// One call per action. openapi-fetch checks the path literal against the
// generated types, so a dynamic path string wouldn't type-check. A switch
// keeps it fully typed.
function callAction(action: TeamActionName, application_id: string) {
  const init = { params: { path: { application_id } } }
  switch (action) {
    case 'agree':
      return api.POST('/api/applications/{application_id}/agree', init)
    case 'submit':
      return api.POST('/api/applications/{application_id}/submit', init)
    case 'withdraw':
      return api.POST('/api/applications/{application_id}/withdraw', init)
  }
}

/**
 * Agree to, submit, or withdraw an application, as the student's team.
 *
 * Throws the server's message when the action is rejected, so callers can show
 * it as `mutation.error.message`.
 */
export function useActOnApplication() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ applicationId, action }: ActOnApplicationInput) => {
      const { response, error } = await callAction(action, applicationId)
      if (!response.ok) throw new Error(errorMessage(error))
    },
    // Returning the promise keeps the mutation "pending" until the refetch has
    // finished, so callers' own onSuccess runs against up-to-date data. Both
    // lists are refreshed because one action touches both: agreeing withdraws
    // other applications, and withdrawing frees a slot (so the project's
    // capacity changes). Refresh happens only on success. After a rejection the
    // view is left as it was, so the stale-view demo still works.
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['applications'] }),
        queryClient.invalidateQueries({ queryKey: ['projects'] }),
      ])
    },
  })
}
