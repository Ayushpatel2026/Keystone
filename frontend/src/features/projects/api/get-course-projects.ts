import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

/**
 * Every project in a course, for pages that join applications to their project
 * (title, capacity, supervisor).
 *
 * The key starts with 'projects' so that invalidating ['projects'] after an
 * action refreshes this list too.
 */
export function useCourseProjects(courseId: string) {
  return useQuery({
    queryKey: ['projects', { courseId }],
    queryFn: async ({ signal }) => {
      const { data, error } = await api.GET('/api/projects', {
        params: { query: { course_id: courseId } },
        signal,
      })
      if (error) throw new Error('Could not load projects.', { cause: error })
      return data
    },
    // no auto refresh for now, this allows us to see some stale data for demo purposes
    refetchOnWindowFocus: false,
  })
}
