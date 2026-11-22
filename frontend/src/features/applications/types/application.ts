import type { components } from '@/types/api'

export type Application = components['schemas']['ApplicationRead']
export type ApplicationStatus = components['schemas']['ApplicationStatus']

/** The application endpoints a team member can call. */
export type TeamActionName = 'agree' | 'submit' | 'withdraw'

/** A button the team can press: which endpoint it calls and what it says. */
export interface TeamAction {
  action: TeamActionName
  label: string
}

/** An action the user has clicked but not yet confirmed in the dialog. */
export interface PendingAction {
  application: Application
  projectTitle: string
  button: TeamAction
}
