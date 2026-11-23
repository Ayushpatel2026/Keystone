import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import type { components } from '@/types/api'

export type Application = components['schemas']['ApplicationRead']
export type ApplicationStatus = Application['status']

/** Submissions waiting for an instructor or TA to approve or reject. */
export const awaitingReview: ApplicationStatus[] = ['team_project_under_review']

/** Submissions an instructor or TA has already decided on. */
export const reviewed: ApplicationStatus[] = [
  'approved',
  'approved_change_under_review',
  'team_project_rejected',
]

/**
 * Every application the signed-in user may see. For an instructor or TA the
 * backend returns only applications in the courses they teach or assist, so
 * no course filter is needed here.
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
