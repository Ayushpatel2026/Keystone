import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

/** Load the project selected in the URL. */
export function useProject(projectId: string) {
  return useQuery({
    queryKey: ['project', projectId],
    enabled: projectId.length > 0,
    queryFn: async ({ signal }) => {
      const { data, error, response } = await api.GET(
        '/api/projects/{project_id}',
        {
          params: { path: { project_id: projectId } },
          signal,
        },
      )
      if (response.status === 404) throw new Error('Project not found.')
      if (error) throw new Error('Could not load project.', { cause: error })
      return data
    },
  })
}
