import FactCheckRoundedIcon from '@mui/icons-material/FactCheckRounded'
import GroupsRoundedIcon from '@mui/icons-material/GroupsRounded'
import WorkHistoryRoundedIcon from '@mui/icons-material/WorkHistoryRounded'
import WorkRoundedIcon from '@mui/icons-material/WorkRounded'
import type { Role } from '@/lib/authorization'
import { paths } from '@/config/paths'

export interface NavItem {
  label: string
  to: string
  icon: React.ReactNode
}

const projects: NavItem = {
  label: 'Projects',
  to: paths.projects,
  icon: <WorkRoundedIcon />,
}

/**
 * Each role's menu, top to bottom. The first item is that role's home page,
 * where `/` sends them. Add an entry when adding a page a role should reach
 * from the menu. The breadcrumb uses the same labels.
 */
export const navItemsByRole: Record<Role, NavItem[]> = {
  student: [
    projects,
    { label: 'My team', to: paths.myTeam, icon: <GroupsRoundedIcon /> },
  ],
  supervisor: [
    {
      label: 'My projects',
      to: paths.myProjects,
      icon: <WorkHistoryRoundedIcon />,
    },
    projects,
  ],
  instructor: [
    { label: 'Teams', to: paths.teams, icon: <FactCheckRoundedIcon /> },
    projects,
  ],
  ta: [
    { label: 'Teams', to: paths.teams, icon: <FactCheckRoundedIcon /> },
    projects,
  ],
}

/** Every item in any menu, for looking up a page's label. */
export const allNavItems: NavItem[] = [
  ...new Set(Object.values(navItemsByRole).flat()),
]

/** Where `/` sends a role. */
export function homePath(role: Role): string {
  return navItemsByRole[role][0].to
}
