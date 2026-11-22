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
import { useUsers } from '@/lib/auth'

/** Full details and availability for the project selected from the catalog. */
export function ProjectDetailPage() {
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
              </Stack>
            </CardContent>
          </Card>
        </>
      )}
    </Stack>
  )
}
