import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import type { paths } from '@/types/api'

export type ProjectFilters = NonNullable<
  paths['/api/projects']['get']['parameters']['query']
>

/**
 * Load projects using the backend's optional course, supervisor, and status filters.
 * Pass `enabled: false` to wait, e.g. until a filter's value is known.
 */
export function useProjects(
  filters: ProjectFilters = {},
  { enabled = true }: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: ['projects', filters],
    enabled,
    queryFn: async ({ signal }) => {
      const { data, error } = await api.GET('/api/projects', {
        params: { query: filters },
        signal,
      })

      if (error) throw new Error('Could not load projects.', { cause: error })
      return data
    },
    // no auto refresh for now, this allows us to see some stale data for demo purposes
    refetchOnWindowFocus: false,
  })
}
