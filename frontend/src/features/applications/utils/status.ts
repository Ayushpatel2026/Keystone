import type { ApplicationStatus } from '@/features/applications/api/get-applications'

type ChipColor = 'default' | 'info' | 'warning' | 'success' | 'error'

/** How each team-project status is shown (SRS, status lifecycle). */
export const applicationStatusChip: Record<
  ApplicationStatus,
  { label: string; color: ChipColor }
> = {
  applied: { label: 'Applied', color: 'info' },
  supervisor_accepts: { label: 'Accepted, waiting for team', color: 'info' },
  agreed: { label: 'Agreed', color: 'success' },
  team_project_submitted: { label: 'Submitted', color: 'warning' },
  team_project_under_review: { label: 'Under review', color: 'warning' },
  team_project_changes_requested: {
    label: 'Changes requested',
    color: 'warning',
  },
  approved: { label: 'Approved', color: 'success' },
  approved_change_under_review: {
    label: 'Approved, change under review',
    color: 'success',
  },
  team_project_rejected: { label: 'Rejected', color: 'error' },
  declined_or_withdrawn: { label: 'Declined or withdrawn', color: 'default' },
}

/** Waiting for the project's supervisor to accept or decline. */
export const awaitingSupervisor: ApplicationStatus[] = ['applied']

/** Waiting for an instructor or TA to approve or reject. */
export const awaitingReview: ApplicationStatus[] = ['team_project_under_review']

/** Already decided by an instructor or TA. */
export const reviewed: ApplicationStatus[] = [
  'approved',
  'approved_change_under_review',
  'team_project_rejected',
]
