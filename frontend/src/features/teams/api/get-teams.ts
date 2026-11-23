import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import type { components } from '@/types/api'

export type Team = components['schemas']['TeamRead']

/** Every team, to show names and members next to their applications. */
export function useTeams() {
  return useQuery({
    queryKey: ['teams'],
    queryFn: async ({ signal }) => {
      const { data, error } = await api.GET('/api/teams', { signal })
      if (error) throw new Error('Could not load teams.', { cause: error })
      return data
    },
  })
}
