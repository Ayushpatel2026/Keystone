import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import MenuItem from '@mui/material/MenuItem'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { useState } from 'react'
import { Link } from 'react-router'
import { paths } from '@/config/paths'
import { useCourses } from '@/features/courses/api/get-courses'
import { useUsers } from '@/lib/auth'
import {
  useProjects,
  type ProjectFilters,
} from '@/features/projects/api/get-projects'

/** Every listed project with its status and capacity, for every role. */
export function ProjectCatalogPage() {
  const [filters, setFilters] = useState<ProjectFilters>({})
  const projects = useProjects(filters)
  const courses = useCourses()
  const users = useUsers()
  const supervisors =
    users.data?.filter((user) => user.role === 'supervisor') ?? []

  return (
    <Stack spacing={3}>
      <Typography variant="h4" component="h1">
        Projects
      </Typography>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
        <TextField
          select
          slotProps={{
            inputLabel: { shrink: true },
            select: { displayEmpty: true },
          }}
          label="Availability"
          value={filters.status ?? ''}
          onChange={(event) => {
            const status = event.target.value
            if (
              status === '' ||
              status === 'open' ||
              status === 'full' ||
              status === 'closed'
            ) {
              setFilters((current) => ({
                ...current,
                status: status || undefined,
              }))
            }
          }}
          sx={{ flex: 1, minWidth: { xs: 0, sm: 200 } }}
        >
          <MenuItem value="">All projects</MenuItem>
          <MenuItem value="open">Open</MenuItem>
          <MenuItem value="full">Full</MenuItem>
          <MenuItem value="closed">Closed</MenuItem>
        </TextField>
        <TextField
          select
          slotProps={{
            inputLabel: { shrink: true },
            select: { displayEmpty: true },
          }}
          label="Course"
          value={filters.course_id ?? ''}
          disabled={courses.isPending || courses.isError}
          onChange={(event) =>
            setFilters((current) => ({
              ...current,
              course_id: event.target.value || undefined,
            }))
          }
          sx={{ flex: 1, minWidth: { xs: 0, sm: 200 } }}
        >
          <MenuItem value="">All courses</MenuItem>
          {courses.data?.map((course) => (
            <MenuItem key={course.id} value={course.id}>
              {course.code} - {course.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          slotProps={{
            inputLabel: { shrink: true },
            select: { displayEmpty: true },
          }}
          label="Supervisor"
          value={filters.supervisor_id ?? ''}
          disabled={users.isPending || users.isError}
          onChange={(event) =>
            setFilters((current) => ({
              ...current,
              supervisor_id: event.target.value || undefined,
            }))
          }
          sx={{ flex: 1, minWidth: { xs: 0, sm: 200 } }}
        >
          <MenuItem value="">All supervisors</MenuItem>
          {supervisors.map((supervisor) => (
            <MenuItem key={supervisor.id} value={supervisor.id}>
              {supervisor.first_name} {supervisor.last_name}
            </MenuItem>
          ))}
        </TextField>
      </Stack>
      {(courses.isError || users.isError) && (
        <Alert severity="warning">
          Some filter options could not be loaded.
        </Alert>
      )}
      {projects.isPending && <CircularProgress aria-label="Loading projects" />}
      {projects.isError && (
        <Alert
          severity="error"
          action={
            <Button onClick={() => void projects.refetch()}>Retry</Button>
          }
        >
          Could not load projects. Please try again.
        </Alert>
      )}
      {projects.isSuccess && projects.data?.length === 0 && (
        <Typography>No projects match your filters.</Typography>
      )}
      {projects.isSuccess &&
        projects.data?.map((project) => {
          const course = courses.data?.find(
            (item) => item.id === project.course_id,
          )
          const supervisor = supervisors.find(
            (item) => item.id === project.supervisor_id,
          )
          return (
            <Card key={project.id} variant="outlined">
              <CardContent>
                <Stack spacing={2}>
                  <Stack
                    direction="row"
                    sx={{
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                    }}
                    spacing={2}
                  >
                    <Typography variant="h6" component="h2">
                      {project.title}
                    </Typography>
                    <Chip
                      size="small"
                      label={
                        project.status.charAt(0).toUpperCase() +
                        project.status.slice(1)
                      }
                      color={project.status === 'open' ? 'success' : 'default'}
                      sx={{ flexShrink: 0 }}
                    />
                  </Stack>
                  <Stack spacing={0.5}>
                    <Typography>
                      Supervisor:{' '}
                      {supervisor
                        ? `${supervisor.first_name} ${supervisor.last_name}`
                        : 'Unavailable'}
                    </Typography>
                    <Typography color="text.secondary">
                      Course:{' '}
                      {course
                        ? `${course.code} - ${course.name}`
                        : 'Unavailable'}
                    </Typography>
                    <Typography>
                      Capacity: {project.slots_reserved} of{' '}
                      {project.supervisor_capacity} slots reserved
                      {' | '}Available: {project.slots_available}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Updated {new Date(project.updated_at).toLocaleString()}
                    </Typography>
                  </Stack>
                  <Typography>{project.background}</Typography>
                  <Button
                    component={Link}
                    to={paths.projectDetail(project.id)}
                    variant="outlined"
                    sx={{ alignSelf: 'flex-start' }}
                  >
                    View details
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          )
        })}
    </Stack>
  )
}
