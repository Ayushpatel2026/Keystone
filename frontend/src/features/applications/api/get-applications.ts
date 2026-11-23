import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import type { components } from '@/types/api'

export type Application = components['schemas']['ApplicationRead']
export type ApplicationStatus = Application['status']

/**
 * Every application the signed-in user may see. The backend scopes it by
 * role: a supervisor gets applications to their own projects, an instructor
 * or TA those in their course(s), a student their teams' applications.
 */
export function useApplications() {
  return useQuery({
    queryKey: ['applications'],
    queryFn: async ({ signal }) => {
      const { data, error } = await api.GET('/api/applications', { signal })
      if (error) {
        throw new Error('Could not load applications.', { cause: error })
      }
      return data
    },
  })
}
