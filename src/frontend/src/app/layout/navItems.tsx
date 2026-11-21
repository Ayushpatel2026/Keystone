import AssignmentRoundedIcon from '@mui/icons-material/AssignmentRounded'
import FactCheckRoundedIcon from '@mui/icons-material/FactCheckRounded'
import ScienceRoundedIcon from '@mui/icons-material/ScienceRounded'
import SupervisorAccountRoundedIcon from '@mui/icons-material/SupervisorAccountRounded'
import WorkRoundedIcon from '@mui/icons-material/WorkRounded'
import { paths } from '../paths'

export interface NavItem {
  label: string
  to: string
  icon: React.ReactNode
}

/**
 * The side menu's links, top to bottom. Add an entry here when adding a page
 * that should appear in the menu. The breadcrumb uses the same labels.
 */
export const mainNavItems: NavItem[] = [
  { label: 'Projects', to: paths.projects, icon: <WorkRoundedIcon /> },
  {
    label: 'My applications',
    to: paths.applications,
    icon: <AssignmentRoundedIcon />,
  },
  {
    label: 'Supervisor',
    to: paths.supervisorApplications,
    icon: <SupervisorAccountRoundedIcon />,
  },
  {
    label: 'Instructor review',
    to: paths.instructorReview,
    icon: <FactCheckRoundedIcon />,
  },
]

/** Shown at the bottom of the menu, apart from the main pages. */
export const secondaryNavItems: NavItem[] = [
  { label: 'Demo', to: paths.demo, icon: <ScienceRoundedIcon /> },
]
