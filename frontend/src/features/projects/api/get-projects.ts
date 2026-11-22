import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import type { paths } from '@/types/api'

export type ProjectFilters = NonNullable<
  paths['/api/projects']['get']['parameters']['query']
>

/** Load projects using the backend's optional course, supervisor, and status filters. */
export function useProjects(filters: ProjectFilters = {}) {
  return useQuery({
    queryKey: ['projects', filters],
    queryFn: async ({ signal }) => {
      const { data, error } = await api.GET('/api/projects', {
        params: { query: filters },
        signal,
      })

      if (error) throw new Error('Could not load projects.', { cause: error })
      return data
    },
  })
}
