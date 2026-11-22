import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { useState } from 'react'
import { Link } from 'react-router'
import { paths } from '@/config/paths'
import { useActOnApplication } from '@/features/applications/api/act-on-application'
import { useTeamApplications } from '@/features/applications/api/get-team-applications'
import { ApplicationCard } from '@/features/applications/components/application-card'
import { ConfirmActionDialog } from '@/features/applications/components/confirm-action-dialog'
import type { PendingAction } from '@/features/applications/types/application'
import { sortOpenFirst } from '@/features/applications/utils/application-status'
import { useCourseProjects } from '@/features/projects/api/get-course-projects'
import { useUsers } from '@/lib/auth'
import { fullName } from '@/lib/utils/full-name'

interface TeamApplicationsProps {
  teamId: string
  courseId: string
}

/** A team's applications, with the actions the team can take on each. */
export function TeamApplications({ teamId, courseId }: TeamApplicationsProps) {
  // The action waiting for the user to confirm. null means the dialog is closed.
  const [pending, setPending] = useState<PendingAction | null>(null)

  const applications = useTeamApplications(teamId)
  // An application only has ids, so the project title, capacity and supervisor
  // come from the project list and the user list. The user list is the same
  // query the "Acting as" switcher uses, so it's usually already cached.
  const projects = useCourseProjects(courseId)
  const users = useUsers()
  const actOnApplication = useActOnApplication()

  function closeDialog() {
    // Clear the last error, or it would show again the next time a dialog opens.
    actOnApplication.reset()
    setPending(null)
  }

  function confirm() {
    if (!pending) return
    actOnApplication.mutate(
      {
        applicationId: pending.application.id,
        action: pending.button.action,
      },
      {
        // Runs after the hook's own onSuccess, which waits for the refetch, so
        // the dialog closes onto up-to-date data. It doesn't run on failure,
        // which leaves the dialog open to show the error.
        onSuccess: () => {
          setPending(null)
        },
      },
    )
  }

  if (applications.isPending || projects.isPending) {
    return <CircularProgress aria-label="Loading applications" />
  }
  if (applications.isError) {
    return <Alert severity="error">{applications.error.message}</Alert>
  }
  if (projects.isError) {
    return <Alert severity="error">{projects.error.message}</Alert>
  }

  const projectsById = new Map(projects.data.map((p) => [p.id, p]))
  const supervisorNames = new Map(
    (users.data ?? []).map((user) => [user.id, fullName(user)]),
  )
  const sorted = sortOpenFirst(applications.data)

  return (
    <Stack spacing={2}>
      <Typography variant="h5" component="h2">
        Applications
      </Typography>

      {sorted.length === 0 && (
        <Alert
          severity="info"
          action={
            <Button
              component={Link}
              to={paths.projects}
              color="inherit"
              size="small"
            >
              Browse projects
            </Button>
          }
        >
          Your team hasn't applied to any projects yet.
        </Alert>
      )}

      {sorted.map((application) => {
        const project = projectsById.get(application.project_id)
        return (
          <ApplicationCard
            key={application.id}
            application={application}
            projectTitle={project?.title ?? 'Unknown project'}
            supervisorName={
              (project && supervisorNames.get(project.supervisor_id)) ??
              'Unknown'
            }
            capacity={
              project
                ? `${project.slots_reserved} of ${project.supervisor_capacity} slots reserved (${project.status})`
                : 'Unknown'
            }
            onAction={(button) => {
              // Clear any error from a previous dialog before opening a new one.
              actOnApplication.reset()
              setPending({
                application,
                projectTitle: project?.title ?? 'this project',
                button,
              })
            }}
          />
        )
      })}

      <ConfirmActionDialog
        pending={pending}
        isWorking={actOnApplication.isPending}
        error={actOnApplication.isError ? actOnApplication.error.message : null}
        onConfirm={confirm}
        onClose={closeDialog}
      />
    </Stack>
  )
}
