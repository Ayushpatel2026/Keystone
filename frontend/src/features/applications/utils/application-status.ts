import type {
  Application,
  ApplicationStatus,
} from '@/features/applications/types/application'

// `closed` drives the colour scheme and the sort order. Record<ApplicationStatus,
// ...> makes the compiler flag any status added to the API but missing here.
export const statusInfo: Record<
  ApplicationStatus,
  { label: string; closed: boolean }
> = {
  applied: { label: 'Applied', closed: false },
  supervisor_accepts: { label: 'Supervisor accepted', closed: false },
  agreed: { label: 'Agreed', closed: false },
  team_project_submitted: { label: 'Submitted', closed: false },
  team_project_under_review: { label: 'Under review', closed: false },
  team_project_changes_requested: { label: 'Changes requested', closed: false },
  approved: { label: 'Approved', closed: false },
  approved_change_under_review: {
    label: 'Approved (change under review)',
    closed: false,
  },
  team_project_rejected: { label: 'Rejected', closed: true },
  declined_or_withdrawn: { label: 'Declined or withdrawn', closed: true },
}

/** Chip colour: grey when closed, green once approved, blue otherwise. */
export function statusChipColor(
  status: ApplicationStatus,
): 'default' | 'success' | 'primary' {
  if (statusInfo[status].closed) return 'default'
  return status === 'approved' ? 'success' : 'primary'
}

/**
 * Open applications first, closed ones last. Array.sort is stable, so the
 * server's order is otherwise kept.
 */
export function sortOpenFirst(applications: Application[]): Application[] {
  // Copy first: query data must not be mutated.
  return [...applications].sort(
    (a, b) =>
      Number(statusInfo[a.status].closed) - Number(statusInfo[b.status].closed),
  )
}
