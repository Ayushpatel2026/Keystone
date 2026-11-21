import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'
import MuiDrawer, { drawerClasses } from '@mui/material/Drawer'
import { styled } from '@mui/material/styles'
import { BrandMark } from './BrandMark'
import { NavMenu } from './NavMenu'
import { UserSwitcher } from './UserSwitcher'

export const drawerWidth = 240

const Drawer = styled(MuiDrawer)({
  width: drawerWidth,
  flexShrink: 0,
  boxSizing: 'border-box',
  [`& .${drawerClasses.paper}`]: {
    width: drawerWidth,
    boxSizing: 'border-box',
  },
})

/**
 * The permanent menu on the left, on medium screens and up. Phones get
 * MobileNavbar instead. Adapted from the template's SideMenu.
 */
export function SideMenu() {
  return (
    <Drawer
      variant="permanent"
      sx={{
        display: { xs: 'none', md: 'block' },
        [`& .${drawerClasses.paper}`]: {
          backgroundColor: 'background.paper',
        },
      }}
    >
      <Box sx={{ display: 'flex', p: 2 }}>
        <BrandMark />
      </Box>
      <Divider />
      <Box
        sx={{
          overflow: 'auto',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <NavMenu />
      </Box>
      <UserSwitcher />
    </Drawer>
  )
}
