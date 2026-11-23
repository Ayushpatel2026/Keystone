import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { useState } from 'react'
import { Link } from 'react-router'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { paths } from '@/config/paths'
import {
  useApplications,
  type Application,
} from '@/features/applications/api/get-applications'
import {
  applicationStatusChip,
  awaitingReview,
  reviewed,
} from '@/features/applications/utils/status'
import { useCourses } from '@/features/courses/api/get-courses'
import { useProjects } from '@/features/projects/api/get-projects'
import { useTeams } from '@/features/teams/api/get-teams'
import {
  useReviewApplication,
  type ReviewDecision,
} from '@/features/teams/api/review-application'

const reviewCopy = {
  approve: {
    title: 'Approve this team project?',
    body: 'The team will be approved for this project.',
    button: 'Approve',
    color: 'success',
  },
  reject: {
    title: 'Reject this team project?',
    body: "The team's slot on the project will be released. This can't be undone.",
    button: 'Reject',
    color: 'error',
  },
} as const

interface PendingReview {
  application: Application
  decision: ReviewDecision
}

/**
 * Course staff: team project submissions in their course(s). Submissions
 * under review can be approved or rejected; decided ones are listed below
 * without actions (#240).
 */
export function TeamsPage() {
  const applications = useApplications()
  const teams = useTeams()
  const projects = useProjects()
  const courses = useCourses()
  const review = useReviewApplication()
  // The last review picked. Kept after closing so the dialog's wording doesn't
  // change while it animates out.
  const [pendingReview, setPendingReview] = useState<PendingReview | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const teamOf = (application: Application) =>
    teams.data?.find((team) => team.id === application.team_id)
  const projectOf = (application: Application) =>
    projects.data?.find((project) => project.id === application.project_id)
  const teamName = (application: Application) =>
    teamOf(application)?.name ?? 'Unknown team'
  const projectTitle = (application: Application) =>
    projectOf(application)?.title ?? 'Unknown project'

  const toReview =
    applications.data?.filter((item) => awaitingReview.includes(item.status)) ??
    []
  const decided =
    applications.data?.filter((item) => reviewed.includes(item.status)) ?? []
  const dialogText = reviewCopy[pendingReview?.decision ?? 'approve']

  function openReview(application: Application, decision: ReviewDecision) {
    review.reset()
    setNotice(null)
    setPendingReview({ application, decision })
    setDialogOpen(true)
  }

  function closeReview() {
    if (review.isPending) return
    setDialogOpen(false)
  }

  function confirmReview() {
    if (!pendingReview) return
    const { application, decision } = pendingReview
    review.mutate(
      { applicationId: application.id, decision },
      {
        onSuccess: () => {
          setNotice(
            `${teamName(application)} was ${decision === 'approve' ? 'approved' : 'rejected'} for ${projectTitle(application)}.`,
          )
          setDialogOpen(false)
        },
      },
    )
  }

  function renderCard(application: Application, withActions: boolean) {
    const team = teamOf(application)
    const project = projectOf(application)
    const course = courses.data?.find((item) => item.id === project?.course_id)
    const chip = applicationStatusChip[application.status]
    return (
      <Card key={application.id} variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <Stack
              direction="row"
              spacing={2}
              sx={{ justifyContent: 'space-between', alignItems: 'flex-start' }}
            >
              <Typography variant="h6" component="h3">
                {teamName(application)}
              </Typography>
              <Chip
                size="small"
                label={chip.label}
                color={chip.color}
                sx={{ flexShrink: 0 }}
              />
            </Stack>
            <Stack spacing={0.5}>
              <Typography>
                Project:{' '}
                {project ? (
                  <Link to={paths.projectDetail(project.id)}>
                    {project.title}
                  </Link>
                ) : (
                  'Unknown project'
                )}
              </Typography>
              {course && (
                <Typography color="text.secondary">
                  Course: {course.code} - {course.name}
                </Typography>
              )}
              <Typography>
                Members:{' '}
                {team && team.members.length > 0
                  ? team.members
                      .map(
                        (member) =>
                          `${member.user.first_name} ${member.user.last_name}`,
                      )
                      .join(', ')
                  : 'Unavailable'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Updated {new Date(application.updated_at).toLocaleString()}
              </Typography>
            </Stack>
            {withActions && (
              <Stack direction="row" spacing={1}>
                <Button
                  variant="contained"
                  color="success"
                  onClick={() => openReview(application, 'approve')}
                  aria-label={`Approve ${teamName(application)}`}
                >
                  Approve
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  onClick={() => openReview(application, 'reject')}
                  aria-label={`Reject ${teamName(application)}`}
                >
                  Reject
                </Button>
              </Stack>
            )}
          </Stack>
        </CardContent>
      </Card>
    )
  }

  return (
    <Stack spacing={3}>
      <Typography variant="h4" component="h1">
        Teams
      </Typography>
      {(teams.isError || projects.isError) && (
        <Alert severity="warning">
          Some team or project details could not be loaded.
        </Alert>
      )}
      {notice && (
        <Alert severity="success" onClose={() => setNotice(null)}>
          {notice}
        </Alert>
      )}
      {applications.isPending && (
        <CircularProgress aria-label="Loading applications" />
      )}
      {applications.isError && (
        <Alert
          severity="error"
          action={
            <Button onClick={() => void applications.refetch()}>Retry</Button>
          }
        >
          Could not load team submissions. Please try again.
        </Alert>
      )}
      {applications.isSuccess && (
        <>
          <Stack spacing={2} component="section" aria-labelledby="to-review">
            <Typography variant="h5" component="h2" id="to-review">
              Awaiting review ({toReview.length})
            </Typography>
            {toReview.length === 0 ? (
              <Typography color="text.secondary">
                No team projects are waiting for review.
              </Typography>
            ) : (
              toReview.map((item) => renderCard(item, true))
            )}
          </Stack>
          <Stack spacing={2} component="section" aria-labelledby="reviewed">
            <Typography variant="h5" component="h2" id="reviewed">
              Reviewed ({decided.length})
            </Typography>
            {decided.length === 0 ? (
              <Typography color="text.secondary">
                No team projects have been approved or rejected yet.
              </Typography>
            ) : (
              decided.map((item) => renderCard(item, false))
            )}
          </Stack>
        </>
      )}
      <ConfirmDialog
        open={dialogOpen}
        title={dialogText.title}
        confirmLabel={dialogText.button}
        confirmColor={dialogText.color}
        pending={review.isPending}
        error={review.error?.message ?? null}
        onConfirm={confirmReview}
        onClose={closeReview}
      >
        {pendingReview && (
          <>
            <strong>{teamName(pendingReview.application)}</strong> on{' '}
            <strong>{projectTitle(pendingReview.application)}</strong>.{' '}
          </>
        )}
        {dialogText.body}
      </ConfirmDialog>
    </Stack>
  )
}
