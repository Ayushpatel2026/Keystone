import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

/** Fetch courses for labels and filters. */
export function useCourses() {
  return useQuery({
    queryKey: ['courses'],
    queryFn: async ({ signal }) => {
      const { data, error } = await api.GET('/api/courses', { signal })
      if (error) throw new Error('Could not load courses.', { cause: error })
      return data
    },
  })
}
