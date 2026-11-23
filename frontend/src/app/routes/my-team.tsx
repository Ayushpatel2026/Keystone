import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { useQueryClient } from '@tanstack/react-query'
import { TeamApplications } from '@/features/applications/components/team-applications'
import { useMyTeam } from '@/features/teams/api/get-my-team'
import { TeamDetails } from '@/features/teams/components/team-details'
import { useActingAs } from '@/lib/auth'
import { useProjects } from '@/features/projects/api/get-projects'

/**
 * Students: their team and its applications, each with its status (#237).
 * The team agrees to, declines, or withdraws from a project here (#239).
 */
export function MyTeamPage() {
  const actingAs = useActingAs()
  // RequireRole already limits this page to students. This check narrows the
  // type (to get `course_id`) and keeps the hooks in MyTeam out of a
  // conditional, which React doesn't allow.
  if (actingAs?.role !== 'student') return null
  return <MyTeam studentId={actingAs.id} courseId={actingAs.course_id} />
}

function MyTeam({
  studentId,
  courseId,
}: {
  studentId: string
  courseId: string
}) {
  const queryClient = useQueryClient()
  const team = useMyTeam(studentId, courseId)
  const projects = useProjects({ course_id: courseId })

  return (
    <Stack spacing={3}>
      <Stack
        direction="row"
        sx={{ justifyContent: 'space-between', alignItems: 'center' }}
      >
        <Typography variant="h4" component="h1">
          My team
        </Typography>
        {/* Manual refresh, since nothing refreshes by itself. Invalidating with
            no key refetches every active query on the page. */}
        <Button
          onClick={() => {
            void queryClient.invalidateQueries()
          }}
        >
          Refresh
        </Button>
      </Stack>

      {team.isPending && <CircularProgress aria-label="Loading your team" />}
      {team.isError && <Alert severity="error">{team.error.message}</Alert>}
      {team.data === null && (
        <Alert severity="info">
          You aren't on a team. Team formation isn't part of the PoC, so teams
          come from the seed data.
        </Alert>
      )}
      {team.data && (
        <>
          <TeamDetails team={team.data} studentId={studentId} />
          <TeamApplications teamId={team.data.id} projects={projects} />
        </>
      )}
    </Stack>
  )
}
