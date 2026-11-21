import Button from '@mui/material/Button'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { Link } from 'react-router'
import { useActingAs } from '@/lib/auth'
import { audience, roleWithArticle, type Role } from '@/lib/authorization'
import { homePath } from '@/components/layouts/nav-items'

interface RequireRoleProps {
  /** Roles that can use the page. */
  roles: Role[]
  /** Page name, for the heading when the role doesn't match. */
  title: string
  children: React.ReactNode
}

/**
 * Shows the page only to the given roles. Anyone else sees who the page is
 * for and how to switch, rather than a 404, since the demo switches users
 * often.
 *
 * This only shapes the UI. The backend decides what each user may do.
 */
export function RequireRole({ roles, title, children }: RequireRoleProps) {
  const actingAs = useActingAs()
  if (actingAs && roles.includes(actingAs.role)) return children

  return (
    <Stack spacing={2} sx={{ alignItems: 'start' }}>
      <Typography variant="h4" component="h1">
        {title}
      </Typography>
      <Typography>
        This page is for {audience(roles)}.{' '}
        {actingAs
          ? `You're acting as ${actingAs.first_name} ${actingAs.last_name}, ${roleWithArticle[actingAs.role]}.`
          : "You haven't picked anyone to act as."}{' '}
        Pick someone else in <strong>Acting as</strong> to see it.
      </Typography>
      {actingAs && (
        <Button component={Link} to={homePath(actingAs.role)}>
          Go to your home page
        </Button>
      )}
    </Stack>
  )
}
