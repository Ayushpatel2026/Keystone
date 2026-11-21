import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import { Outlet } from 'react-router'
import { Header } from './Header'
import { MobileNavbar } from './MobileNavbar'
import { SideMenu } from './SideMenu'

/**
 * The frame around every page: side menu (or top bar on phones), breadcrumb
 * header, then the page. Adapted from the template's Dashboard component.
 */
export function AppLayout() {
  return (
    <Box sx={{ display: 'flex' }}>
      <SideMenu />
      <MobileNavbar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          minWidth: 0,
          minHeight: '100vh',
          backgroundColor: 'background.default',
        }}
      >
        <Stack
          spacing={2}
          sx={{
            mx: { xs: 2, sm: 3 },
            pb: 5,
            // Leave room for the fixed mobile top bar.
            mt: { xs: 9, md: 0 },
          }}
        >
          <Header />
          <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
            <Outlet />
          </Box>
        </Stack>
      </Box>
    </Box>
  )
}
