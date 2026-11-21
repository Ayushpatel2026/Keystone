import MenuRoundedIcon from '@mui/icons-material/MenuRounded'
import AppBar from '@mui/material/AppBar'
import Divider from '@mui/material/Divider'
import Drawer, { drawerClasses } from '@mui/material/Drawer'
import IconButton from '@mui/material/IconButton'
import Stack from '@mui/material/Stack'
import Toolbar from '@mui/material/Toolbar'
import { useState } from 'react'
import ColorModeIconDropdown from '../../theme/ColorModeIconDropdown'
import { BrandMark } from './BrandMark'
import { NavMenu } from './NavMenu'
import { UserSwitcher } from './UserSwitcher'

/**
 * Top bar with a slide-out menu, below the medium breakpoint (phones and
 * small tablets). Adapted from the template's AppNavbar and SideMenuMobile.
 */
export function MobileNavbar() {
  const [open, setOpen] = useState(false)

  return (
    <AppBar
      position="fixed"
      sx={{
        display: { xs: 'block', md: 'none' },
        boxShadow: 0,
        bgcolor: 'background.paper',
        backgroundImage: 'none',
        borderBottom: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Toolbar sx={{ gap: 1 }}>
        <Stack direction="row" sx={{ mr: 'auto' }}>
          <BrandMark />
        </Stack>
        {/* size="medium" is 40px, the SRS's minimum for controls. */}
        <ColorModeIconDropdown size="medium" />
        <IconButton
          size="medium"
          aria-label="Open menu"
          aria-expanded={open}
          onClick={() => {
            setOpen(true)
          }}
        >
          <MenuRoundedIcon />
        </IconButton>
      </Toolbar>
      <Drawer
        anchor="right"
        open={open}
        onClose={() => {
          setOpen(false)
        }}
        sx={{
          [`& .${drawerClasses.paper}`]: {
            backgroundImage: 'none',
            backgroundColor: 'background.paper',
          },
        }}
      >
        <Stack sx={{ width: 'min(280px, 80dvw)', height: '100%' }}>
          <UserSwitcher />
          <Divider />
          <NavMenu
            onNavigate={() => {
              setOpen(false)
            }}
          />
        </Stack>
      </Drawer>
    </AppBar>
  )
}
