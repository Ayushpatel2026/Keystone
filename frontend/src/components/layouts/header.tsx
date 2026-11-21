import NavigateNextRoundedIcon from '@mui/icons-material/NavigateNextRounded'
import Breadcrumbs, { breadcrumbsClasses } from '@mui/material/Breadcrumbs'
import Stack from '@mui/material/Stack'
import { styled } from '@mui/material/styles'
import Typography from '@mui/material/Typography'
import { matchPath, useLocation } from 'react-router'
import ColorModeIconDropdown from '@/lib/theme/ColorModeIconDropdown'
import { allNavItems } from '@/components/layouts/nav-items'

const StyledBreadcrumbs = styled(Breadcrumbs)(({ theme }) => ({
  margin: theme.spacing(1, 0),
  [`& .${breadcrumbsClasses.separator}`]: {
    color: (theme.vars ?? theme).palette.action.disabled,
    margin: 1,
  },
  [`& .${breadcrumbsClasses.ol}`]: {
    alignItems: 'center',
  },
}))

/** The menu section the current URL belongs to, e.g. "Projects". */
function useCurrentSection() {
  const { pathname } = useLocation()
  return allNavItems.find(
    (item) => matchPath({ path: item.to, end: false }, pathname) !== null,
  )?.label
}

/**
 * Row above each page on medium screens and up: breadcrumbs, then actions.
 * Adapted from the template's Header and NavbarBreadcrumbs; its search box,
 * date picker and notifications button are left out until we need them.
 */
export function Header() {
  const section = useCurrentSection()

  return (
    <Stack
      direction="row"
      spacing={2}
      sx={{
        display: { xs: 'none', md: 'flex' },
        width: '100%',
        alignItems: 'center',
        justifyContent: 'space-between',
        maxWidth: { sm: '100%', md: '1700px' },
        pt: 1.5,
      }}
    >
      <StyledBreadcrumbs
        aria-label="breadcrumb"
        separator={<NavigateNextRoundedIcon fontSize="small" />}
      >
        <Typography variant="body1">Keystone</Typography>
        {section && (
          <Typography
            variant="body1"
            sx={{ color: 'text.primary', fontWeight: 600 }}
          >
            {section}
          </Typography>
        )}
      </StyledBreadcrumbs>
      {/* size="medium" is 40px, the SRS's minimum for controls. */}
      <ColorModeIconDropdown size="medium" />
    </Stack>
  )
}
