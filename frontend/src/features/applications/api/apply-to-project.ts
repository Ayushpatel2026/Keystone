import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

interface ApplyToProjectInput {
  studentId: string
  teamId: string
  projectId: string
}

/** Apply on behalf of the student's team and refresh its applications. */
export function useApplyToProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      studentId,
      teamId,
      projectId,
    }: ApplyToProjectInput) => {
      const { data, error, response } = await api.POST('/api/applications', {
        params: { query: { student_id: studentId } },
        body: { team_id: teamId, project_id: projectId },
      })
      if (!response.ok) {
        // Business errors contain a readable detail; validation errors use a list.
        const detail = error && 'detail' in error ? error.detail : undefined
        throw new Error(
          typeof detail === 'string' ? detail : 'Could not apply to project.',
        )
      }
      return data
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['applications'] })
    },
  })
}
