import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

/**
 * The team a student belongs to, or null if they aren't on one.
 *
 * TODO - There's no "my team" endpoint, need to add one
 * so this lists the course's teams and picks the
 * one that contains the student.
 */
export function useMyTeam(studentId: string, courseId: string) {
  return useQuery({
    // studentId is in the key because what the API returns may depend on who is asking.
    queryKey: ['teams', 'mine', studentId, courseId],
    queryFn: async ({ signal }) => {
      const { data, error } = await api.GET('/api/teams', {
        params: { query: { course_id: courseId } },
        signal,
      })
      if (error) throw new Error('Could not load your team.', { cause: error })
      // null, not undefined: React Query doesn't allow undefined as query data,
      // and null lets the page tell "loaded, no team" apart from "still loading".
      return (
        data.find((team) =>
          team.members.some((member) => member.user.id === studentId),
        ) ?? null
      )
    },
    // The PoC deliberately has no auto-refresh: a stale view must still be able
    // to send an action and get it rejected (Dev Plan, PoC step 8).
    refetchOnWindowFocus: false,
  })
}
