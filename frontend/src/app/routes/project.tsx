import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { Link, useParams } from 'react-router'
import { paths } from '@/config/paths'
import { useProject } from '@/features/projects/api/get-project'
import { useCourses } from '@/features/courses/api/get-courses'
import { useApplyToProject } from '@/features/projects/api/apply-to-project'
import { useMyTeam } from '@/features/teams/api/get-my-team'
import { useActingAs, useUsers } from '@/lib/auth'

/** Full details and availability for the project selected from the catalog. */
export function ProjectDetailPage() {
  const actingAs = useActingAs()
  const { projectId } = useParams()
  const projectQuery = useProject(projectId ?? '')
  const project = projectQuery.data
  const courses = useCourses()
  const users = useUsers()
  const course = courses.data?.find((item) => item.id === project?.course_id)
  const supervisor = users.data?.find(
    (item) => item.id === project?.supervisor_id,
  )

  return (
    <Stack spacing={3}>
      <Button
        component={Link}
        to={paths.projects}
        variant="outlined"
        sx={{ alignSelf: 'flex-start' }}
      >
        Back to projects
      </Button>
      {!projectId && <Alert severity="error">No project was selected.</Alert>}
      {projectId && projectQuery.isPending && (
        <CircularProgress aria-label="Loading project" />
      )}
      {projectQuery.isError && (
        <Alert severity="error">{projectQuery.error.message}</Alert>
      )}
      {project && (
        <>
          <Typography variant="h4" component="h1">
            {project.title}
          </Typography>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Chip
                  label={
                    project.status.charAt(0).toUpperCase() +
                    project.status.slice(1)
                  }
                  color={project.status === 'open' ? 'success' : 'default'}
                  sx={{ alignSelf: 'flex-start' }}
                />
                <Typography>
                  Course:{' '}
                  {course
                    ? `${course.code} - ${course.name}`
                    : courses.isPending
                      ? 'Loading...'
                      : 'Unavailable'}
                </Typography>
                <Typography>
                  Supervisor:{' '}
                  {supervisor
                    ? `${supervisor.first_name} ${supervisor.last_name}`
                    : users.isPending
                      ? 'Loading...'
                      : 'Unavailable'}
                </Typography>
                <Typography variant="h6" component="h2">
                  Background
                </Typography>
                <Typography sx={{ whiteSpace: 'pre-wrap' }}>
                  {project.background}
                </Typography>
                <Typography variant="h6" component="h2">
                  Availability
                </Typography>
                <Typography>
                  Capacity: {project.supervisor_capacity} teams
                </Typography>
                <Typography>
                  Reserved slots: {project.slots_reserved}
                </Typography>
                <Typography>
                  Available slots: {project.slots_available}
                </Typography>
                <Typography color="text.secondary">
                  Last updated: {new Date(project.updated_at).toLocaleString()}
                </Typography>
                {actingAs?.role === 'student' &&
                  (project.status !== 'open' ? (
                    <Alert severity="info">
                      This project is not open for applications.
                    </Alert>
                  ) : actingAs.course_id !== project.course_id ? (
                    <Alert severity="info">
                      You can only apply to projects in your course.
                    </Alert>
                  ) : (
                    <ApplyToProject
                      key={`${actingAs.id}:${project.id}`}
                      studentId={actingAs.id}
                      courseId={actingAs.course_id}
                      projectId={project.id}
                    />
                  ))}
              </Stack>
            </CardContent>
          </Card>
        </>
      )}
    </Stack>
  )
}

/** Resolve the student's team before allowing an application. */
function ApplyToProject({
  studentId,
  courseId,
  projectId,
}: {
  studentId: string
  courseId: string
  projectId: string
}) {
  const team = useMyTeam(studentId, courseId)
  const application = useApplyToProject()

  if (team.isPending) return <CircularProgress aria-label="Loading your team" />
  if (team.isError) return <Alert severity="error">{team.error.message}</Alert>
  if (!team.data)
    return (
      <Alert severity="info">You must belong to a team before applying.</Alert>
    )
  const teamId = team.data.id

  return (
    <Stack spacing={2}>
      <Button
        variant="contained"
        sx={{ alignSelf: 'flex-start' }}
        disabled={application.isPending || application.isSuccess}
        onClick={() => application.mutate({ studentId, teamId, projectId })}
      >
        {application.isPending ? 'Applying…' : 'Apply'}
      </Button>
      {application.isError && (
        <Alert severity="error">{application.error.message}</Alert>
      )}
      {application.isSuccess && (
        <Alert severity="success">Your team has applied to this project.</Alert>
      )}
    </Stack>
  )
}
