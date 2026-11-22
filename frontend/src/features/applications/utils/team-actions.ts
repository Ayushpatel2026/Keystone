import type {
  ApplicationStatus,
  TeamAction,
  TeamActionName,
} from '@/features/applications/types/application'

const AGREE: TeamAction = { action: 'agree', label: 'Agree' }
const SUBMIT: TeamAction = { action: 'submit', label: 'Submit for review' }
const WITHDRAW: TeamAction = { action: 'withdraw', label: 'Withdraw' }
// The API's /decline is the supervisor's. A team that turns down a supervisor's
// acceptance uses /withdraw, so "Decline" is only a different label for it.
const DECLINE: TeamAction = { action: 'withdraw', label: 'Decline' }

/**
 * What a student's team may do, per status. This table is the only place the UI
 * encodes the state machine. The server still validates every action, so if it
 * disagrees with this table the user sees the server's error rather than
 * corrupt state.
 */
export const actionsByStatus: Record<ApplicationStatus, TeamAction[]> = {
  applied: [WITHDRAW],
  supervisor_accepts: [AGREE, DECLINE],
  agreed: [SUBMIT, WITHDRAW],
  team_project_submitted: [WITHDRAW],
  team_project_under_review: [WITHDRAW],
  // Outside the PoC scope (no change requests, no post-approval changes).
  team_project_changes_requested: [],
  approved: [],
  approved_change_under_review: [],
  // Closed: nothing left to do.
  team_project_rejected: [],
  declined_or_withdrawn: [],
}

/**
 * Shown in the confirmation dialog. They spell out the side effects
 */
export const actionDescription: Record<TeamActionName, string> = {
  agree:
    "Your team agrees to work on this project. Your team's other applications will be withdrawn and any slots reserved for your team on other projects will be released.",
  submit: "Submit your team's project to the course staff for approval.",
  withdraw:
    "Your team's application will be closed and any slot reserved for your team on this project will be released. This can't be undone.",
}
