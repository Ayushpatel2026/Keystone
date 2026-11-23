import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Divider from '@mui/material/Divider'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { useState } from 'react'
import { Link } from 'react-router'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { paths } from '@/config/paths'
import {
  useDecideApplication,
  type SupervisorDecision,
} from '@/features/applications/api/decide-application'
import { useApplications } from '@/features/applications/api/get-applications'
import type { Application } from '@/features/applications/types/application'
import {
  statusChipColor,
  statusInfo,
} from '@/features/applications/utils/application-status'
import { useProjects } from '@/features/projects/api/get-projects'
import { useTeams } from '@/features/teams/api/get-teams'
import { useActingAs } from '@/lib/auth'
import { fullName } from '@/lib/utils/full-name'

/** Waiting for the project's supervisor to accept or decline. */
const isWaiting = (application: Application) => application.status === 'applied'

const decisionCopy = {
  accept: {
    title: 'Accept this team?',
    body: "This reserves one of the project's slots for the team. The team then confirms to agree.",
    button: 'Accept',
    color: 'success',
  },
  decline: {
    title: 'Decline this application?',
    body: "The team won't be able to work on this project. This can't be undone.",
    button: 'Decline',
    color: 'error',
  },
} as const

interface PendingDecision {
  application: Application
  decision: SupervisorDecision
}

/**
 * Supervisors: their own projects and the applications to each. Applications
 * waiting for a decision can be accepted or declined (#238).
 */
export function MyProjectsPage() {
  const me = useActingAs()
  // Without a supervisor_id the backend returns every project, so wait for it.
  const projects = useProjects({ supervisor_id: me?.id }, { enabled: !!me })
  const applications = useApplications()
  const teams = useTeams()
  const decide = useDecideApplication()
  // The last decision picked. Kept after closing so the dialog's wording
  // doesn't change while it animates out.
  const [pending, setPending] = useState<PendingDecision | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const teamOf = (application: Application) =>
    teams.data?.find((team) => team.id === application.team_id)
  const teamName = (application: Application) =>
    teamOf(application)?.name ?? 'Unknown team'
  const projectTitle = (application: Application) =>
    projects.data?.find((project) => project.id === application.project_id)
      ?.title ?? 'Unknown project'
  const dialogText = decisionCopy[pending?.decision ?? 'accept']

  function openDecision(
    application: Application,
    decision: SupervisorDecision,
  ) {
    decide.reset()
    setNotice(null)
    setPending({ application, decision })
    setDialogOpen(true)
  }

  function closeDecision() {
    if (decide.isPending) return
    setDialogOpen(false)
  }

  function confirmDecision() {
    if (!pending) return
    const { application, decision } = pending
    decide.mutate(
      { applicationId: application.id, decision },
      {
        onSuccess: () => {
          setNotice(
            `${teamName(application)} was ${decision === 'accept' ? 'accepted' : 'declined'} for ${projectTitle(application)}.`,
          )
          setDialogOpen(false)
        },
      },
    )
  }

  function renderApplication(application: Application) {
    const team = teamOf(application)
    return (
      <Stack key={application.id} spacing={1}>
        <Stack
          direction="row"
          spacing={2}
          sx={{ justifyContent: 'space-between', alignItems: 'flex-start' }}
        >
          <Typography variant="subtitle1" component="h3">
            {teamName(application)}
          </Typography>
          <Chip
            size="small"
            label={statusInfo[application.status].label}
            color={statusChipColor(application.status)}
            sx={{ flexShrink: 0 }}
          />
        </Stack>
        <Typography>
          Members:{' '}
          {team && team.members.length > 0
            ? team.members.map((member) => fullName(member.user)).join(', ')
            : 'Unavailable'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Updated {new Date(application.updated_at).toLocaleString()}
        </Typography>
        {isWaiting(application) && (
          <Stack direction="row" spacing={1}>
            <Button
              variant="contained"
              color="success"
              onClick={() => openDecision(application, 'accept')}
              aria-label={`Accept ${teamName(application)}`}
            >
              Accept
            </Button>
            <Button
              variant="outlined"
              color="error"
              onClick={() => openDecision(application, 'decline')}
              aria-label={`Decline ${teamName(application)}`}
            >
              Decline
            </Button>
          </Stack>
        )}
      </Stack>
    )
  }

  // Wait for team details too, so cards don't flash "Unknown team". If they
  // fail, the cards still show, with a warning above them.
  const loading =
    projects.isPending || applications.isPending || teams.isPending
  const failed = projects.isError || applications.isError

  return (
    <Stack spacing={3}>
      <Typography variant="h4" component="h1">
        My projects
      </Typography>
      {teams.isError && (
        <Alert severity="warning">Team details could not be loaded.</Alert>
      )}
      {notice && (
        <Alert severity="success" onClose={() => setNotice(null)}>
          {notice}
        </Alert>
      )}
      {loading && !failed && (
        <CircularProgress aria-label="Loading your projects" />
      )}
      {failed && (
        <Alert
          severity="error"
          action={
            <Button
              onClick={() => {
                void projects.refetch()
                void applications.refetch()
              }}
            >
              Retry
            </Button>
          }
        >
          Could not load your projects and applications. Please try again.
        </Alert>
      )}
      {projects.isSuccess && applications.isSuccess && !loading && (
        <>
          {projects.data.length === 0 && (
            <Typography>You don&apos;t have any projects yet.</Typography>
          )}
          {projects.data.map((project) => {
            const projectApps = applications.data.filter(
              (item) => item.project_id === project.id,
            )
            const waiting = projectApps.filter(isWaiting)
            // Waiting for a decision first, then the rest, each in the
            // order the server returned them.
            const sorted = [
              ...waiting,
              ...projectApps.filter((item) => !waiting.includes(item)),
            ]
            return (
              <Card
                key={project.id}
                variant="outlined"
                component="section"
                aria-labelledby={`project-${project.id}`}
              >
                <CardContent>
                  <Stack spacing={2}>
                    <Stack
                      direction="row"
                      spacing={2}
                      sx={{
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                      }}
                    >
                      <Typography
                        variant="h6"
                        component="h2"
                        id={`project-${project.id}`}
                      >
                        <Link to={paths.projectDetail(project.id)}>
                          {project.title}
                        </Link>
                      </Typography>
                      <Chip
                        size="small"
                        label={
                          project.status.charAt(0).toUpperCase() +
                          project.status.slice(1)
                        }
                        color={
                          project.status === 'open' ? 'success' : 'default'
                        }
                        sx={{ flexShrink: 0 }}
                      />
                    </Stack>
                    <Typography color="text.secondary">
                      {project.slots_reserved} of {project.supervisor_capacity}{' '}
                      slots reserved | {waiting.length} waiting for your
                      decision
                    </Typography>
                    <Divider />
                    {sorted.length === 0 ? (
                      <Typography color="text.secondary">
                        No applications yet.
                      </Typography>
                    ) : (
                      <Stack spacing={2} divider={<Divider flexItem />}>
                        {sorted.map(renderApplication)}
                      </Stack>
                    )}
                  </Stack>
                </CardContent>
              </Card>
            )
          })}
        </>
      )}
      <ConfirmDialog
        open={dialogOpen}
        title={dialogText.title}
        confirmLabel={dialogText.button}
        confirmColor={dialogText.color}
        pending={decide.isPending}
        error={decide.error?.message ?? null}
        onConfirm={confirmDecision}
        onClose={closeDecision}
      >
        {pending && (
          <>
            <strong>{teamName(pending.application)}</strong> on{' '}
            <strong>{projectTitle(pending.application)}</strong>.{' '}
          </>
        )}
        {dialogText.body}
      </ConfirmDialog>
    </Stack>
  )
}
