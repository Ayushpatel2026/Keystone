import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Stack from '@mui/material/Stack'
import { matchPath, NavLink, useLocation } from 'react-router'
import { mainNavItems, type NavItem, secondaryNavItems } from './navItems'

interface NavMenuProps {
  /** Called after a link is clicked, e.g. to close the mobile drawer. */
  onNavigate?: () => void
}

/** The list of page links. Adapted from the template's MenuContent. */
export function NavMenu({ onNavigate }: NavMenuProps) {
  const { pathname } = useLocation()

  const renderItems = (items: NavItem[]) => (
    <List>
      {items.map((item) => {
        // Highlight the item for its page and anything under it, so
        // /projects/123 still highlights "Projects".
        const selected =
          matchPath({ path: item.to, end: false }, pathname) !== null
        return (
          <ListItem key={item.to} disablePadding sx={{ display: 'block' }}>
            <ListItemButton
              component={NavLink}
              to={item.to}
              selected={selected}
              onClick={onNavigate}
              // 40px tall: the SRS's minimum size for controls.
              sx={{ minHeight: 40 }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        )
      })}
    </List>
  )

  return (
    <Stack
      component="nav"
      aria-label="Main"
      sx={{ flexGrow: 1, p: 1, justifyContent: 'space-between' }}
    >
      {renderItems(mainNavItems)}
      {renderItems(secondaryNavItems)}
    </Stack>
  )
}
