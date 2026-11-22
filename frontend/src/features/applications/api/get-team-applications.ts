import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

/**
 * A team's applications.
 *
 * Asks for `team_id` explicitly rather than relying on the backend to scope the
 * list by the caller's token.
 */
export function useTeamApplications(teamId: string) {
  return useQuery({
    queryKey: ['applications', { teamId }],
    queryFn: async ({ signal }) => {
      const { data, error } = await api.GET('/api/applications', {
        params: { query: { team_id: teamId } },
        signal,
      })
      if (error)
        throw new Error('Could not load applications.', { cause: error })
      return data
    },
    // No auto-refresh in the PoC (see use-my-team).
    refetchOnWindowFocus: false,
  })
}
